"""
make_call.py
------------
Drop this file in your project root (next to the `backend/` folder).
Just run:  python make_call.py

Uvicorn logs are now VISIBLE so you can see the exact error when the call connects.

Optional args:
  python make_call.py --keep-alive   # keep server running after call is initiated
"""

import argparse
import subprocess
import sys
import time
import os
import requests

# ── Edit your defaults here ───────────────────────────────────────
DEFAULT_PHONE = "+919392165195"
DEFAULT_NAME  = "Teja"
HOST          = "127.0.0.1"
PORT          = 8000
# ─────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(description="Start FastAPI and initiate call")
    parser.add_argument("--phone",      default=DEFAULT_PHONE, help="Customer phone number")
    parser.add_argument("--name",       default=DEFAULT_NAME,  help="Customer name")
    parser.add_argument("--keep-alive", action="store_true",
                        help="Keep the server running after the call is initiated")
    return parser.parse_args()


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Poll the base URL until the server responds or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            requests.get(url, timeout=1)
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(0.4)
    return False


def main():
    args = parse_args()
    base_url = f"http://{HOST}:{PORT}"

    print("\n" + "=" * 52)
    print("  FastAPI Call Initiator")
    print("=" * 52)
    print(f"  Phone  : {args.phone}")
    print(f"  Name   : {args.name}")
    print(f"  Server : {base_url}")
    print("=" * 52 + "\n")

    # ── Step 1: Launch uvicorn as a subprocess ───────────────────────────
    # stdout/stderr are inherited (None) so you see ALL logs in this terminal.
    # This makes it easy to spot the exact line that causes "application error".
    print("[1/3] Starting uvicorn server (logs shown below)...")
    print("-" * 52)

    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", HOST,
        "--port", str(PORT),
    ]

    script_dir = os.path.dirname(os.path.abspath(__file__))

    server_proc = subprocess.Popen(
        cmd,
        cwd=script_dir,
        stdout=None,   # ← inherit: uvicorn logs appear in YOUR terminal
        stderr=None,   # ← inherit: exceptions/tracebacks appear in YOUR terminal
    )

    # ── Step 2: Wait until server accepts requests ───────────────────────
    print("\n[2/3] Waiting for server to be ready...", end="", flush=True)
    if not wait_for_server(base_url, timeout=30):
        print("\n[ERROR] Server did not start within 30 seconds. Exiting.")
        server_proc.terminate()
        sys.exit(1)
    print(" Ready!\n")

    # ── Step 3: POST to /initiate-call ───────────────────────────────────
    print(f"[3/3] Calling {args.name} at {args.phone} ...")
    try:
        resp = requests.post(
            f"{base_url}/initiate-call",
            params={"customer_phone": args.phone, "customer_name": args.name},
            timeout=30,
        )
        resp.raise_for_status()
        print(f"\n✅ Call initiated successfully!")
        print(f"   Response : {resp.json()}\n")
        print("-" * 52)
        print("  Server is running. Watch logs above for errors.")
        print("  Answer the call — any tracebacks will print here.")
        print("-" * 52)

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP {e.response.status_code} error: {e.response.text}")
        server_proc.terminate()
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        server_proc.terminate()
        sys.exit(1)

    # ── Step 4: Always keep alive so webhook callbacks can reach the server ─
    # The call itself triggers CALLBACKS from Twilio back to your server.
    # If the server shuts down immediately, Twilio gets no response → error.
    # So we always stay alive until Ctrl+C, regardless of --keep-alive.
    print("\nPress Ctrl+C to stop the server.\n")
    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print("\n[INFO] Stopping server...")
        server_proc.terminate()
        server_proc.wait()
        print("[INFO] Done.")


if __name__ == "__main__":
    main()