import subprocess
import sys
import os
import time

def run_backend():
    # Start FastAPI backend (uvicorn)
    return subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])

def run_frontend():
    # Start Streamlit frontend
    return subprocess.Popen([
        sys.executable, "-m", "streamlit",
        "run", "app.py",
        "--server.port", "8501"
    ])

if __name__ == "__main__":
    print("🚆 Starting KMRL Induction System (Backend + Frontend)...")

    # Run backend first
    backend_proc = run_backend()
    time.sleep(3)  # small delay to ensure backend starts

    # Run frontend
    frontend_proc = run_frontend()

    try:
        # Wait until both processes exit
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("Shutting down...")
        backend_proc.terminate()
        frontend_proc.terminate()
