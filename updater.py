import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

logger = logging.getLogger(__name__)

REPO_OWNER = "BoscoHeo"
REPO_NAME = "brity-autologin"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"


def _parse_version(v_str: str) -> tuple:
    """'v3.8' -> (3, 8) 형태의 튜플로 변환"""
    try:
        clean = v_str.lstrip("vV").strip()
        return tuple(map(int, clean.split(".")))
    except Exception:
        return (0, 0)


def check_for_update(current_version: str, timeout_sec: float = 2.0) -> tuple[bool, str, str]:
    """
    최신 릴리스가 있는지 확인.
    반환값: (업데이트_있음_여부, 최신_버전_문자열, 다운로드_URL)
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "User-Agent": "BrityAutoLogin-Updater",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as res:
            if res.status != 200:
                return False, "", ""
            data = json.loads(res.read().decode("utf-8"))
            
        latest_tag = data.get("tag_name", "")
        if not latest_tag:
            return False, "", ""
            
        if _parse_version(latest_tag) > _parse_version(current_version):
            # EXE 파일 다운로드 URL 찾기
            for asset in data.get("assets", []):
                if asset.get("name") == "BrityAutoLogin.exe":
                    return True, latest_tag, asset.get("browser_download_url", "")
                    
        return False, latest_tag, ""
    except Exception as e:
        logger.debug(f"업데이트 확인 중 예외(네트워크/타임아웃 등): {e}")
        return False, "", ""


def apply_update(download_url: str, status_callback=None) -> bool:
    """
    최신 EXE를 다운로드하여 자체 교체(Self-Update) 후 재실행
    """
    if not getattr(sys, "frozen", False):
        logger.info("개발/스크립트 환경에서는 자동 업데이트 교체를 건너뜁니다.")
        return False
        
    current_exe = os.path.abspath(sys.executable)
    exe_dir = os.path.dirname(current_exe)
    new_exe = os.path.join(exe_dir, "BrityAutoLogin_new.exe")
    bat_path = os.path.join(exe_dir, "_updater.bat")
    
    def status(msg: str):
        logger.info(msg)
        if status_callback:
            try:
                status_callback(msg)
            except Exception:
                pass

    try:
        status("최신 버전 다운로드 중...")
        req = urllib.request.Request(download_url, headers={"User-Agent": "BrityAutoLogin-Updater"})
        with urllib.request.urlopen(req, timeout=30.0) as resp, open(new_exe, "wb") as out:
            out.write(resp.read())
            
        status("업데이트 교체 및 재실행 중...")
        # 윈도우 배치 스크립트로 현재 프로세스 종료 후 덮어쓰기 & 재실행
        bat_content = f"""@echo off
timeout /t 1 /nobreak >nul
move /y "{new_exe}" "{current_exe}" >nul
start "" "{current_exe}"
del "%~f0"
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
            
        subprocess.Popen(f'cmd.exe /c "{bat_path}"', shell=True, creationflags=0x08000000)
        sys.exit(0)
    except Exception as e:
        logger.error(f"자동 업데이트 적용 실패: {e}")
        if os.path.exists(new_exe):
            try:
                os.remove(new_exe)
            except Exception:
                pass
        return False
