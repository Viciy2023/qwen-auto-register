"""测试 Qwen token 是否可用于 API 调用。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import requests
except ImportError:
    print("请先安装: pip install requests")
    sys.exit(1)

from auto_register.writer.auth_profiles_writer import get_default_auth_profiles_path


def get_token_from_profiles() -> str | None:
    """从 auth-profiles.json 读取 qwen-portal access token。"""
    p = get_default_auth_profiles_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        profiles = data.get("profiles", {})
        for key, prof in profiles.items():
            if "qwen" in key.lower() and prof.get("type") == "oauth":
                acc = prof.get("access")
                if acc:
                    return acc
    except Exception:
        pass
    return None


def main():
    token = get_token_from_profiles()
    if not token:
        print("未找到 auth-profiles.json 中的 qwen-portal token。")
        print("请先运行自动注册流程，或手动传入 token：")
        print("  python scripts/test_qwen_token.py <your_access_token>")
        if len(sys.argv) > 1:
            token = sys.argv[1]
        else:
            sys.exit(1)
    else:
        print(f"从 auth-profiles 读取 token: {token[:50]}...")

    headers = {"Authorization": f"Bearer {token}"}

    # 1. portal.qwen.ai（OpenClaw 默认端点）
    print("\n--- 1. portal.qwen.ai/v1/models ---")
    url1 = "https://portal.qwen.ai/v1/models"
    r1 = requests.get(url1, headers=headers, timeout=15)
    print(f"GET /v1/models 状态码: {r1.status_code}")
    if r1.text:
        print(f"响应: {r1.text[:400]}")
    ok1 = r1.status_code == 200

    # 1b. 尝试 chat completions（401=认证失败，200/400=认证可能通过）
    print("\n--- 1b. portal.qwen.ai/v1/chat/completions ---")
    url1b = "https://portal.qwen.ai/v1/chat/completions"
    r1b = requests.post(url1b, headers={**headers, "Content-Type": "application/json"}, json={"model": "qwen-turbo", "messages": [{"role": "user", "content": "hi"}]}, timeout=15)
    print(f"POST /v1/chat/completions 状态码: {r1b.status_code}")
    if r1b.text:
        print(f"响应: {r1b.text[:300]}")
    if r1b.status_code == 401:
        ok1 = False

    # 2. chat.qwen.ai 后端 API（若存在）
    print("\n--- 2. chat.qwen.ai 相关 API ---")
    url2 = "https://chat.qwen.ai/api/conversations"
    r2 = requests.get(url2, headers=headers, timeout=15)
    print(f"GET {url2} 状态码: {r2.status_code}")
    ok2 = r2.status_code == 200

    # 400 + invalid_parameter 表示认证通过，只是模型名错误
    portal_ok = ok1 or (r1b.status_code == 400 and "invalid" in (r1b.text or "").lower())

    print("\n" + "=" * 50)
    if portal_ok:
        print("[OK] portal.qwen.ai: Token 有效，认证通过。")
        print("     若 OpenClaw 仍 401，请检查：")
        print("       1. openclaw gateway restart")
        print("       2. openclaw plugins enable qwen-portal-auth")
        print("       3. auth-profiles 路径是否与 OpenClaw 使用的一致")
    elif r1.status_code == 401 or r1b.status_code == 401:
        print("[X] portal.qwen.ai: Token 无效 (401)。")
        print("    建议：openclaw models auth login --provider qwen-portal --set-default")
    else:
        print("[?] portal.qwen.ai: 状态 %d/%d，无法确定。" % (r1.status_code, r1b.status_code))
    if ok2:
        print("\n[OK] chat.qwen.ai: Token 对 chat API 有效。")


if __name__ == "__main__":
    main()
