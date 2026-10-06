#!/usr/bin/env python3
"""Project Installer & Environment Bootstrapper.

Automates:
1. Virtual environment verification and setup
2. Dependency installation from requirements.txt
3. AI Log Hook setup and configuration
4. Environment variable (.env) template initialization
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_cmd(cmd: list[str], cwd: Path = ROOT) -> int:
    print(f">> Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def setup_env_file() -> None:
    env_file = ROOT / ".env"
    example_file = ROOT / ".env.example"
    if not env_file.exists() and example_file.exists():
        print("-> Creating .env from .env.example...")
        env_file.write_text(example_file.read_text(encoding="utf-8"), encoding="utf-8")
        print("   [OK] .env initialized. Please update your API keys.")
    else:
        print("   [OK] .env already exists.")


def setup_hooks() -> None:
    print("-> Configuring AI Log Git hooks...")
    hooks_script = ROOT / "scripts" / ("setup_hooks.ps1" if os.name == "nt" else "setup_hooks.sh")
    if hooks_script.exists():
        if os.name == "nt":
            run_cmd(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(hooks_script)])
        else:
            run_cmd(["bash", str(hooks_script)])
    print("   [OK] Git hooks configured.")


def main() -> None:
    print("=" * 60)
    print("  VCare Medical Agent - Project Setup & Installer")
    print("=" * 60)

    # 1. Environment file
    setup_env_file()

    # 2. Install requirements
    print("-> Installing Python dependencies...")
    pip_cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
    run_cmd(pip_cmd)

    req_file = ROOT / "requirements.txt"
    if req_file.exists():
        req_cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        code = run_cmd(req_cmd)
        if code != 0:
            print("   [WARNING] Some dependencies failed to install.")
        else:
            print("   [OK] Dependencies installed successfully.")

    # 3. Setup hooks
    setup_hooks()

    print("=" * 60)
    print("  Setup Completed Successfully!")
    print("  Run backend: python -m uvicorn src.main:app --reload")
    print("=" * 60)


if __name__ == "__main__":
    main()
