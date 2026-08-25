"""
main.py - Brity 자동 로그인 매크로 진입점

실행 흐름:
  1. config.json 없음 → 설정 창(SetupWindow) 표시
  2. config.json 있음 → 복호화 후 자동 로그인 실행
"""
import json
import logging
import os
import sys
import tkinter as tk
from tkinter import messagebox

# ── 로그 설정 ──────────────────────────────────────────
LOG_LEVEL = logging.DEBUG   # 배포 시 INFO로 변경

def _setup_logging(base_dir: str):
    log_path = os.path.join(base_dir, "brity_autologin.log")
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

# ── 기본 경로 ──────────────────────────────────────────
if getattr(sys, "frozen", False):
    # PyInstaller로 빌드된 exe 실행 시
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 개발 환경 (python main.py)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def _load_config() -> dict | None:
    """config.json 로드. 없으면 None 반환."""
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    _setup_logging(BASE_DIR)
    logger = logging.getLogger(__name__)
    logger.info(f"=== Brity 자동 로그인 시작 (BASE_DIR={BASE_DIR}) ===")

    config = _load_config()

    if config is None:
        # ── 최초 실행: 설정 창 ─────────────────────────
        logger.info("config.json 없음 → 설정 창 표시")
        from gui import SetupWindow
        root = tk.Tk()
        SetupWindow(root, BASE_DIR)
        root.mainloop()

    else:
        # ── 이후 실행: 자동 로그인 ────────────────────
        logger.info("config.json 발견 → 자동 로그인 실행")
        cert_username = config.get("cert_username", "")
        enc_password = config.get("cert_password_encrypted", "")
        app_path     = config.get("app_path", r"C:\BrityWorks\BrityMessenger\BrityMessenger.exe")
        cert_index   = config.get("cert_index", 1)

        try:
            from encryptor import decrypt
            cert_password = decrypt(enc_password)
        except Exception as e:
            logger.error(f"비밀번호 복호화 실패: {e}")
            from tkinter import messagebox
            messagebox.showerror(
                "복호화 오류",
                f"저장된 암호를 읽을 수 없습니다.\n({e})\n\n설정을 다시 하시려면 config.json과 key.bin 파일을 직접 삭제해 주세요."
            )
            return

        def _worker(status_win):
            def callback(msg):
                status_win.update_status(msg)

            try:
                run_login(
                    cert_username=cert_username,
                    cert_password=cert_password,
                    status_callback=callback,
                    app_path=app_path,
                    cert_index=cert_index,
                )
                time.sleep(1.0)
            except Exception as login_err:
                logger.error(f"자동 로그인 오류: {login_err}", exc_info=True)
                status_win.update_status(f"오류 발생: {login_err}", is_error=True)
                time.sleep(3.0)
            finally:
                status_win.close()

        from gui import _run_macro_window
        _run_macro_window(cert_username, cert_password, app_path, cert_index)


if __name__ == "__main__":
    main()
