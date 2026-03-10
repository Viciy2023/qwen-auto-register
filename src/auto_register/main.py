"""Entry point for Qwen token auto-acquisition."""

import argparse
import sys
from pathlib import Path

from .integrations.qwen_portal import QwenPortalRunner


def run_cli() -> int:
    """Run from command line."""
    parser = argparse.ArgumentParser(description="Qwen Token 自动获取 - 注册/激活/登录/写入 auth-profiles.json")
    parser.add_argument("--headless", action="store_true", help="无头模式运行浏览器")
    parser.add_argument("--no-gui", action="store_true", help="仅 CLI，不启动 GUI（默认自动检测）")
    parser.add_argument("--gui", action="store_true", help="强制启动 GUI")
    parser.add_argument(
        "--auth-path",
        type=Path,
        default=None,
        help="auth-profiles.json 路径覆盖",
    )
    args = parser.parse_args()

    # If --gui or no --no-gui and no args, launch GUI
    if args.gui or (not args.no_gui and len(sys.argv) == 1):
        from .gui.app import run_gui
        return run_gui()

    def on_step(msg: str) -> None:
        print(f"[Step] {msg}")

    runner = QwenPortalRunner(
        headless=args.headless,
        auth_profiles_path=args.auth_path,
        on_step=on_step,
    )
    try:
        ok = runner.run()
        return 0 if ok else 1
    except KeyboardInterrupt:
        print("\n[已中断] 用户终止 (Ctrl+C)", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(run_cli())
    except KeyboardInterrupt:
        print("\n[已中断] 用户终止 (Ctrl+C)", file=sys.stderr)
        sys.exit(0)
