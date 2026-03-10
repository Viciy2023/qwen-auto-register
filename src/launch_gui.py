"""PyInstaller entry point - run as module to resolve relative imports."""
import os
import sys

if __name__ == "__main__":
    # 加载 .env（exe 同目录或项目根目录）
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        if getattr(sys, "frozen", False):
            load_dotenv(Path(sys.executable).parent / ".env")
        else:
            load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
    except Exception:
        pass

    # PyInstaller 打包后，Playwright 会在临时目录中查找浏览器，导致失败
    # 强制使用系统默认路径 %LOCALAPPDATA%\ms-playwright
    if getattr(sys, "frozen", False):
        from pathlib import Path
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        pw_path = local / "ms-playwright"
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(pw_path)
    try:
        from auto_register.gui.app import run_gui
        sys.exit(run_gui())
    except KeyboardInterrupt:
        sys.exit(0)
