"""Qwen registration + login + token extraction runner."""

import os
import string
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from playwright.sync_api import Page, sync_playwright

from ..providers.one_sec_mail_provider import get_email_provider
from ..providers.username_provider import UsernameProvider
from ..utils.gateway import restart_openclaw_gateway
from ..utils.token_utils import is_valid_jwt, validate_tokens
from ..writer.auth_profiles_writer import AuthProfilesWriter
from .qwen_oauth_client import run_device_code_flow


@dataclass
class QwenCredentials:
    """Credentials for a single Qwen registration."""

    username: str
    email: str
    password: str


def _generate_password(length: int = 14) -> str:
    """生成符合 Qwen 要求的密码：大小写字母+数字，≥8位。使用14位避免过长导致表单异常。"""
    import random
    # 强制包含至少各一个，满足 Qwen 要求
    pwd = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
    ]
    pwd += list(random.choices(string.ascii_letters + string.digits, k=length - 3))
    random.shuffle(pwd)
    return "".join(pwd)


class QwenPortalRunner:
    """Run full Qwen flow: register -> activate -> login -> extract token -> write."""

    REGISTER_URL = "https://chat.qwen.ai/auth?mode=register"
    LOGIN_URL = "https://chat.qwen.ai/auth"

    def __init__(
        self,
        headless: bool = False,
        auth_profiles_path: Optional[Path] = None,
        on_step: Optional[Callable[[str], None]] = None,
    ):
        self._headless = headless
        self._writer = AuthProfilesWriter(path=auth_profiles_path)
        self._on_step = on_step or (lambda _: None)

    def _log(self, msg: str) -> None:
        self._on_step(msg)

    def run(self) -> bool:
        """Execute full flow. Returns True on success."""
        mail_provider = get_email_provider(poll_interval=5.0, timeout=120.0)
        creds = QwenCredentials(
            username=UsernameProvider().get(),
            email=mail_provider.generate_email(),
            password=_generate_password(),
        )
        self._log(f"1. 临时邮箱: {creds.email}")
        self._log(f"2. 随机密码已生成")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self._headless)
            context = browser.new_context()
            page = context.new_page()

            try:
                self._do_register(page, creds)
                self._log("4. 已提交注册，等待激活邮件...")
                activation_url = mail_provider.wait_for_activation_link(creds.email)
                self._log("5. 收到激活邮件")
                page.goto(activation_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                self._log("6. 已打开激活链接")

                # 激活后可能已自动登录并跳转到 chat.qwen.ai，若无需登录则跳过
                needs_login = self._needs_login(page)
                if needs_login:
                    self._do_login(page, creds)
                    self._log("8. 已提交登录")
                else:
                    self._log("7. 激活后已自动登录，跳过登录步骤")

                page.wait_for_timeout(5000)

                # 确保在 chat 页（用户已登录），用于后续 OAuth 授权
                try:
                    if "chat.qwen.ai" not in (page.url or ""):
                        page.goto("https://chat.qwen.ai", wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(3000)

                # 9. 通过 OAuth 设备码流程获取 API token（与 openclaw onboard 一致，非网页 JWT）
                self._log("9. 启动 OAuth 设备码流程，获取 API token...")
                tokens = self._get_oauth_api_token(page)
                if not tokens:
                    self._log("9. OAuth 获取失败，请确保在授权页点击「同意」")
                    return False

                access, refresh, expires = tokens["access"], tokens["refresh"], tokens["expires"]
                self._log_token_debug(access, refresh, source="OAuth 设备码", fmt="API token")
                try:
                    validate_tokens(access, refresh, allow_same=(access == refresh), allow_api_token=True)
                except ValueError as e:
                    self._log(f"错误: {e}")
                    return False

                self._log("10. 正在写入 auth-profiles.json...")
                self._writer.write_qwen_profile(access=access, refresh=refresh, expires=expires)
                self._log("11. 已写入 auth-profiles.json")

                if restart_openclaw_gateway(on_log=self._log):
                    self._log("12. 全部完成，新账号已就绪")
                else:
                    self._log("12. Token 已写入，但 Gateway 重启失败，请手动执行: openclaw gateway restart")
                # 供 qwen-rate-limit-monitor 检测成功
                try:
                    (Path(os.environ.get("TEMP", "")) / "qwen-register-success").touch()
                except Exception:
                    pass
                return True
            except Exception as e:
                self._log(f"错误: {e}")
                raise
            finally:
                browser.close()

    def _do_register(self, page: Page, creds: QwenCredentials) -> None:
        """Fill and submit registration form."""
        self._log("3. 打开注册页并填写表单")
        page.goto(self.REGISTER_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # 用户名（第一个文本输入框，或 placeholder 含「用户」）
        try:
            username_input = page.locator(
                'input[placeholder*="用户"], input[placeholder*="username"], input[name="username"], input[type="text"]'
            ).first
            username_input.wait_for(state="visible", timeout=5000)
            username_input.fill(creds.username)
        except Exception:
            pass

        # 邮箱
        email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="邮箱"]').first
        email_input.wait_for(state="visible", timeout=10000)
        email_input.fill(creds.email)

        # 密码与确认密码
        pw_inputs = page.locator('input[type="password"]')
        count = pw_inputs.count()
        if count >= 1:
            pw_inputs.nth(0).fill(creds.password)
        if count >= 2:
            pw_inputs.nth(1).fill(creds.password)

        # 勾选「我同意用户条款和隐私协议」
        try:
            # 优先：通过 label 文字定位
            label = page.locator('label').filter(has_text="我同意").first
            if label.count() > 0:
                label.click()
            else:
                # 备选：直接勾选表单中唯一的 checkbox
                cb = page.locator('input[type="checkbox"]').first
                if cb.count() > 0:
                    cb.check()
        except Exception:
            pass

        page.wait_for_timeout(800)

        # 等待提交按钮可用（填完表单并勾选协议后会解除 disabled / .disabled 类）
        submit = page.locator('button[type="submit"], button:has-text("注册"), button:has-text("Register")').first
        submit.wait_for(state="visible", timeout=5000)
        page.wait_for_function(
            """() => {
                const btn = document.querySelector('button[type=submit]');
                if (!btn) return false;
                if (btn.disabled) return false;
                if (btn.classList.contains('disabled')) return false;
                return true;
            }""",
            timeout=10000,
        )
        submit.click()
        page.wait_for_timeout(3000)

    def _needs_login(self, page: Page) -> bool:
        """检查当前页是否显示登录表单（若已在 chat 页则不需要登录）。"""
        url = page.url or ""
        if "/auth" not in url and "chat.qwen.ai" in url:
            return False
        try:
            email_input = page.locator('input[type="email"], input[name="email"]').first
            return email_input.is_visible()
        except Exception:
            return False

    def _do_login(self, page: Page, creds: QwenCredentials) -> None:
        """Fill and submit login form."""
        self._log("7. 填写登录表单")
        if "auth" not in page.url.lower() or "register" in page.url:
            page.goto(self.LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

        email_input = page.locator('input[type="email"], input[name="email"]').first
        email_input.wait_for(state="visible", timeout=10000)
        email_input.fill(creds.email)

        pw_input = page.locator('input[type="password"]').first
        pw_input.fill(creds.password)

        submit = page.locator('button[type="submit"], button:has-text("登录"), button:has-text("Login")').first
        submit.click()
        page.wait_for_timeout(5000)

    def _get_oauth_api_token(self, page: Page) -> Optional[dict[str, str | int]]:
        """通过 OAuth 设备码流程获取 API token（在浏览器上下文中请求以通过 WAF）。"""
        def open_url(url: str, user_code: str) -> None:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if self._headless:
                self._log("[OAuth] 无头模式：自动填写设备码并点击「同意」...")
                self._auto_click_oauth_approve(page, user_code)
            else:
                self._log(f"请在打开的页面输入码 {user_code} 并点击「同意」")

        def on_wait() -> None:
            self._log("[OAuth] 等待用户授权...")

        return run_device_code_flow(
            open_verification_url=open_url,
            on_wait=on_wait,
            poll_interval=2.0,
            timeout_seconds=300.0,
            page_for_requests=page,
        )

    def _auto_click_oauth_approve(self, page: Page, user_code: str = "") -> None:
        """无头模式下自动填写设备码（若需要）并点击 OAuth 授权页的「同意」按钮。"""
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(4000)

        if user_code:
            try:
                for sel in [
                    'input[placeholder*="码"]',
                    'input[placeholder*="code"]',
                    'input[name*="code"]',
                    'input[placeholder*="Code"]',
                ]:
                    inp = page.locator(sel).first
                    if inp.count() > 0:
                        inp.wait_for(state="visible", timeout=2000)
                        inp.fill(user_code)
                        page.wait_for_timeout(1500)
                        break
            except Exception:
                pass

        selectors = [
            'button:has-text("同意")',
            'button:has-text("授权")',
            'button:has-text("允许")',
            'button:has-text("确认")',
            'button:has-text("Approve")',
            'button:has-text("Authorize")',
            'button:has-text("Allow")',
            'button:has-text("Continue")',
            'a:has-text("同意")',
            'a:has-text("授权")',
            'a:has-text("允许")',
            '[role="button"]:has-text("同意")',
            '[role="button"]:has-text("授权")',
            '[data-testid="approve"]',
            'button[type="submit"]',
            'input[type="submit"]',
            'div[class*="primary"]:has-text("同意")',
            'div[class*="submit"]:has-text("同意")',
        ]
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state="visible", timeout=3000)
                btn.click()
                self._log("[OAuth] 已自动点击同意")
                page.wait_for_timeout(2000)
                return
            except Exception:
                continue

        clicked = page.evaluate("""() => {
            const texts = ['同意', '授权', '允许', 'Approve', 'Authorize', 'Allow', '确认'];
            const nodes = document.querySelectorAll('button, a, [role="button"], input[type="submit"]');
            for (const el of nodes) {
                const t = (el.textContent || '').trim();
                if (texts.some(x => t.includes(x))) {
                    el.click();
                    return true;
                }
            }
            return false;
        }""")
        if clicked:
            self._log("[OAuth] 已自动点击同意（JS 查找）")
            page.wait_for_timeout(2000)
            return

        try:
            path = Path(tempfile.gettempdir()) / "qwen_oauth_approve_fail.png"
            page.screenshot(path=path)
            self._log(f"[OAuth] 未找到同意按钮，截图已保存: {path}")
        except Exception:
            self._log("[OAuth] 未找到同意按钮，请检查授权页结构")

    def _log_token_debug(self, access: str, refresh: str, source: str, fmt: str) -> None:
        """打印 token 来源与格式调试信息。"""
        jwt_flag = "JWT" if is_valid_jwt(access) else "非 JWT"
        self._log(f"[调试] Token 来源: {source}")
        self._log(f"[调试] Token 格式: {fmt} ({jwt_flag})")
        self._log(f"[调试] access(len={len(access)}) refresh(len={len(refresh)})")
