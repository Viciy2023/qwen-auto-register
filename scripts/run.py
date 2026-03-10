#!/usr/bin/env python3
"""Convenience script to run AutoRegister."""

import sys
from pathlib import Path

# Add project src to path
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "src"))

# 加载 .env（支持 OPENCLAW_NODE_PATH 等）
try:
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
except Exception:
    pass
from auto_register.main import run_cli

if __name__ == "__main__":
    try:
        sys.exit(run_cli())
    except KeyboardInterrupt:
        print("\n[已中断] 用户终止 (Ctrl+C)")
        sys.exit(0)
