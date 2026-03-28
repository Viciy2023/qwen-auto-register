"""Write Qwen credentials to output directory in multiple formats."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_default_output_path() -> Path:
    """Get default output directory path."""
    return Path(__file__).parent.parent.parent.parent / "output"


class OutputWriter:
    """Write Qwen credentials to output directory."""

    def __init__(self, output_dir: Path | str | None = None):
        """Initialize with optional custom output directory."""
        self._output_dir = Path(output_dir) if output_dir else get_default_output_path()
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def save_account_txt(self, email: str, password: str) -> Path:
        """Save account credentials to timestamped txt file.

        Format: email,password
        File: qwen-{timestamp_ms}.txt
        """
        timestamp_ms = int(time.time() * 1000)
        txt_file = self._output_dir / f"qwen-{timestamp_ms}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(f"{email},{password}\n")
        return txt_file

    def save_qwen_json(
        self,
        email: str,
        access_token: str,
        refresh_token: str,
        expires_ms: int,
    ) -> Path:
        """Save individual Qwen profile JSON file.

        Args:
            email: Full email address (e.g., naakd8r9ta8o@sharebot.net)
            access_token: OAuth access token.
            refresh_token: OAuth refresh token.
            expires_ms: Expiration as milliseconds Unix timestamp.

        Returns:
            Path to the saved JSON file.
        """
        timestamp_ms = int(time.time() * 1000)

        # Extract username from email (part before @)
        username = email.split("@")[0] if "@" in email else email

        # Convert milliseconds timestamp to ISO format
        expires_dt = datetime.fromtimestamp(expires_ms / 1000, tz=timezone.utc)
        expired_str = expires_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        # Last refresh is now
        now_dt = datetime.now(tz=timezone.utc)
        last_refresh_str = now_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        profile: dict[str, Any] = {
            "access_token": access_token,
            "email": username,
            "expired": expired_str,
            "last_refresh": last_refresh_str,
            "refresh_token": refresh_token,
            "resource_url": "portal.qwen.ai",
            "type": "qwen",
        }

        # Save as qwen-{timestamp_ms}.json
        json_file = self._output_dir / f"qwen-{timestamp_ms}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        return json_file
