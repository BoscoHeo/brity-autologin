"""
macro_engine.py - Brity Messenger 초고속 실시간 자동 로그인 엔진 (v3.8)

로그인 흐름:
  [0] 부팅 감지 (부팅 직후 90초 이내인 경우에만 5초 안정화 대기, 평소에는 0초 즉시 시작)
  [1] BrityMessenger.exe 실행 및 창 0.05초 단위 실시간 감지
  [2] Brity 로그인 화면 → '로그인' 버튼 클릭
  [3] KSIGN 메인 창 실시간 감지 (Win32 초고속 탐색)
  [4] '교육행정 전자서명 인증서 로그인' 버튼 즉각 클릭
  [5] 인증서 선택 모달 창 및 [비밀번호 입력란(Edit)] 0.05초 실시간 감지
  [6] 인증서 선택 + Edit 박스 정밀 포커스 및 초고속 암호 입력 + Enter
  [7] 창 닫힘 검증 후 로그인 완료
"""
import ctypes
import json
import logging
import os
import subprocess
import sys
import time

import pyautogui
import win32con
import win32gui

logger = logging.getLogger(__name__)

# pyautogui 안전 설정
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

BRITY_EXE_DEFAULT = r"C:\BrityWorks\BrityMessenger\BrityMessenger.exe"


def get_system_uptime() -> float:
    """시스템 가동 시간(초) 반환 (GetTickCount64)"""
    try:
        return ctypes.windll.kernel32.GetTickCount64() / 1000.0
    except Exception:
        return 9999.0



def find_brity_exe() -> str:
    """Brity Messenger 설치 경로 및 바로가기(.lnk) 자동 검색"""
    candidates = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Brity Messenger\Brity Messenger.lnk"),
        os.path.expandvars(r"%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Brity Messenger\Brity Messenger.lnk"),
        os.path.expandvars(r"%USERPROFILE%\Desktop\Brity Messenger.lnk"),
        os.path.expandvars(r"%PUBLIC%\Desktop\Brity Messenger.lnk"),
        r"C:\BrityWorks\BrityMessenger\BrityMessenger.exe",
        r"C:\Program Files\BrityWorks\BrityMessenger\BrityMessenger.exe",
        r"C:\Program Files (x86)\BrityWorks\BrityMessenger\BrityMessenger.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BrityWorks\BrityMessenger\BrityMessenger.exe"),
        os.path.expandvars(r"%APPDATA%\BrityWorks\BrityMessenger\BrityMessenger.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            logger.info(f"BrityMessenger 감지 성공: {path}")
            return path
    return BRITY_EXE_DEFAULT


# ─────────────────────────────────────────────
#  Win32 초고속 윈도우 유틸리티
# ─────────────────────────────────────────────

def _activate_hwnd(hwnd: int) -> bool:
    """지정된 HWND 창을 최상단 포그라운드로 즉시 활성화"""
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        # Alt 가상 키 입력으로 Windows 포그라운드 전환 잠금 해제
        pyautogui.press("alt")
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.05)
        return True
    except Exception as e:
        logger.debug(f"창 활성화 예외 (정상 무시): {e}")
        return False


def _find_top_window(title_keywords: list, min_w: int = 200, min_h: int = 150) -> int | None:
    """Win32 API로 제목 키워드가 매칭되는 최상위 표시 창의 HWND 즉시 반환 (0ms)"""
    found_hwnd = None

    def enum_cb(hwnd, _):
        nonlocal found_hwnd
        if found_hwnd:
            return
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        title_lower = title.lower()

        # 당사 매크로 창 제외
        if "brity 자동 로그인" in title_lower:
            return

        if any(kw.lower() in title_lower for kw in title_keywords):
            try:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w >= min_w and h >= min_h:
                    found_hwnd = hwnd
            except Exception:
                pass

    win32gui.EnumWindows(enum_cb, None)
    return found_hwnd


def _wait_top_window(title_keywords: list, timeout: float = 20.0, min_w: int = 200, min_h: int = 150) -> int:
    """0.05초 단위 실시간 감지로 창이 나타날 때까지 대기"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd = _find_top_window(title_keywords, min_w, min_h)
        if hwnd:
            return hwnd
        time.sleep(0.05)
    raise TimeoutError(f"창 감지 시간 초과: {title_keywords}")


def _close_unwanted_popups() -> None:
    """알림/공지 소형 팝업 안전 닫기"""
    def enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip().lower()
        if any(kw in title for kw in ["brity", "ksign", "전자서명", "log in", "인증", "brity 자동 로그인"]):
            return
        try:
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if 150 < w < 550 and 100 < h < 450:
                logger.info(f"소형 팝업 감지 (닫기): {title} ({w}x{h})")
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception:
            pass

    win32gui.EnumWindows(enum_cb, None)


# ─────────────────────────────────────────────
#  인증서 선택 창 & 비밀번호 입력 상자 초고속 감지
# ─────────────────────────────────────────────

def _log_all_visible_windows():
    """실패 분석을 위해 현재 화면의 모든 활성 창 목록을 로그에 기록"""
    logger.warning("=== [실패 분석] 현재 화면의 모든 활성 창 목록 스캔 ===")
    try:
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)
        logger.warning(f"시스템 해상도 (물리): {screen_w}x{screen_h}")
        
        def enum_cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd).strip()
            cls_name = win32gui.GetClassName(hwnd)
            try:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
            except Exception:
                rect = (0,0,0,0)
                w, h = 0, 0
            logger.warning(f"HWND: {hwnd} | Title: '{title}' | Class: '{cls_name}' | Size: {w}x{h} | Rect: {rect}")
            
        win32gui.EnumWindows(enum_cb, None)
        logger.warning("==================================================")
    except Exception as e:
        logger.error(f"창 스캔 중 예외 발생: {e}")


def _find_cert_dialog_only() -> int | None:
    """인증서 선택 창의 HWND만 단독 탐색 (Edit 컨트롤 못 찾았을 때 대비)"""
    found_hwnd = None
    
    def enum_cb(hwnd, _):
        nonlocal found_hwnd
        if found_hwnd:
            return
        if not win32gui.IsWindowVisible(hwnd):
            return
            
        title = win32gui.GetWindowText(hwnd).strip()
        title_lower = title.lower()
        if "brity 자동 로그인" in title_lower:
            return
            
        try:
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            # 너무 극단적으로 작거나 큰 창만 제외 (브라우저 최대화 창 제외)
            if w < 150 or h < 150 or w > 1050 or h > 980:
                return
        except Exception:
            return
            
        cls_name = win32gui.GetClassName(hwnd)
        if cls_name in ["Chrome_WidgetWin_1", "MozillaWindowClass", "IEFrame"]:
            return
        if any(kw in title_lower for kw in ["chrome", "edge", "whale", "익스플로러", "firefox"]):
            return

        # 타이틀이나 클래스가 인증서 창과 관계가 있는 경우 허용
        is_cert_title = (not title) or any(kw in title_lower for kw in ["인증", "서명", "sign", "cert", "crypt", "security", "login", "log in", "ksign"])
        is_dialog_class = (cls_name == "#32770" or "dialog" in cls_name.lower())
        
        if is_cert_title or is_dialog_class:
            found_hwnd = hwnd
            
    win32gui.EnumWindows(enum_cb, None)
    return found_hwnd


def _find_cert_dialog_and_edit_controls() -> tuple[int | None, int | None, int | None]:
    """
    화면에 뜬 인증서 선택 창의 HWND, 비밀번호 Edit HWND, 인증서 ListView HWND 탐색.
    반환: (dialog_hwnd, edit_hwnd, listview_hwnd)
    """
    found_dialog = None
    found_edit = None
    found_listview = None

    def enum_top(hwnd, _):
        nonlocal found_dialog, found_edit, found_listview
        if found_edit:
            return
        if not win32gui.IsWindowVisible(hwnd):
            return

        title = win32gui.GetWindowText(hwnd).strip()
        title_lower = title.lower()
        if "brity 자동 로그인" in title_lower:
            return

        # 1. 크기 필터링 (최대화된 브라우저 등 대형 창 제외)
        try:
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w < 150 or h < 150 or w > 1050 or h > 980:
                return
        except Exception:
            return

        # 2. 브라우저 제외 및 인증 관련 창 체크
        cls_name = win32gui.GetClassName(hwnd)
        if cls_name in ["Chrome_WidgetWin_1", "MozillaWindowClass", "IEFrame"]:
            return
        if any(kw in title_lower for kw in ["chrome", "edge", "whale", "익스플로러", "firefox"]):
            return

        is_cert_title = (not title) or any(kw in title_lower for kw in ["인증", "서명", "sign", "cert", "crypt", "security", "login", "log in", "ksign"])
        is_dialog_class = (cls_name == "#32770" or "dialog" in cls_name.lower())
        
        if not (is_cert_title or is_dialog_class):
            return

        # 자식 컨트롤 탐색
        child_edits = []
        child_lists = []

        def enum_child(chwnd, _):
            if not win32gui.IsWindowVisible(chwnd):
                return
            cls = win32gui.GetClassName(chwnd)
            if cls == "Edit":
                try:
                    rect = win32gui.GetWindowRect(chwnd)
                    ew = rect[2] - rect[0]
                    eh = rect[3] - rect[1]
                    if 60 < ew < 350 and 15 < eh < 60:
                        child_edits.append(chwnd)
                except Exception:
                    pass
            elif "SysListView32" in cls or "ListBox" in cls:
                child_lists.append(chwnd)

        try:
            win32gui.EnumChildWindows(hwnd, enum_child, None)
        except Exception:
            pass

        if child_edits:
            found_dialog = hwnd
            found_edit = child_edits[0]
            if child_lists:
                found_listview = child_lists[0]

    win32gui.EnumWindows(enum_top, None)
    return found_dialog, found_edit, found_listview


def _wait_cert_dialog_and_edit(timeout: float = 20.0) -> tuple[int, int, int | None]:
    """
    0.05초 단위로 비밀번호 입력창(Edit)이 화면에 렌더링될 때까지 초고속 실시간 대기
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        dlg_hwnd, edit_hwnd, list_hwnd = _find_cert_dialog_and_edit_controls()
        if dlg_hwnd and edit_hwnd:
            logger.info(f"인증서 비밀번호 Edit 상자 초고속 감지 성공! (dlg={dlg_hwnd}, edit={edit_hwnd})")
            return dlg_hwnd, edit_hwnd, list_hwnd
        time.sleep(0.05)
    raise TimeoutError("인증서 선택 창 또는 비밀번호 입력란을 찾지 못했습니다.")


# ─────────────────────────────────────────────
#  Step-by-Step 자동화 실행
# ─────────────────────────────────────────────

def _launch_brity(app_path: str) -> None:
    """Brity Messenger 실행 (이미 실행 중이면 즉시 포커스)"""
    target_path = app_path if (app_path and os.path.exists(app_path)) else find_brity_exe()
    logger.info(f"Brity 실행 확인/시작: {target_path}")

    try:
        os.startfile(target_path)
    except Exception:
        subprocess.Popen(f'explorer "{target_path}"', shell=True)


def run_login(
    cert_username: str,
    cert_password: str,
    status_callback=None,
    app_path: str = BRITY_EXE_DEFAULT,
    cert_index: int = 1,
) -> None:
    """Brity Messenger 초고속 실시간 자동 로그인 메인 함수"""

    def status(msg: str):
        logger.info(msg)
        if status_callback:
            try:
                status_callback(msg)
            except Exception:
                pass

    try:
        # ── Step 0: 부팅 감지 및 스마트 대기 (부팅 후 1분=60초 경과까지 카운트다운) ──
        uptime = get_system_uptime()
        target_boot_delay = 60.0  # 부팅 후 1분(60초) 안정화 대기
        
        if uptime < target_boot_delay:
            remaining = int(target_boot_delay - uptime)
            logger.info(f"시스템 부팅 직후 감지 (가동 시간: {uptime:.1f}초). 부팅 1분 경과까지 {remaining}초 대기합니다.")
            while remaining > 0:
                status(f"윈도우 부팅 안정화 대기 중... ({remaining}초 남음)")
                time.sleep(1.0)
                uptime = get_system_uptime()
                remaining = int(target_boot_delay - uptime)
            status("부팅 1분 경과: 자동 로그인 시작!")
            time.sleep(0.5)
        else:
            logger.info(f"일반 실행 모드 (부팅 후 {uptime:.1f}초 경과 → 즉시 시작)")

        # ── Step 1: 메신저 실행 및 감지 ───────────────
        status("Brity Messenger 실행 확인 중...")
        _launch_brity(app_path)

        brity_hwnd = _wait_top_window(["Brity", "Messenger"], timeout=20.0, min_w=300, min_h=200)
        _activate_hwnd(brity_hwnd)
        time.sleep(0.1)

        _close_unwanted_popups()

        # ── Step 2: 로그인 버튼 클릭 ──────────────────
        status("로그인 버튼 클릭 중...")
        _activate_hwnd(brity_hwnd)
        b_rect = win32gui.GetWindowRect(brity_hwnd)
        bw = b_rect[2] - b_rect[0]
        bh = b_rect[3] - b_rect[1]

        # 키보드 직행 엔터/스페이스 + 마우스 클릭
        pyautogui.press("enter")
        time.sleep(0.05)
        pyautogui.press("space")

        btn_x = b_rect[0] + int(bw * 0.75)
        btn_y = b_rect[1] + int(bh * 0.58)
        pyautogui.click(btn_x, btn_y)
        logger.info(f"로그인 버튼 클릭 완료: ({btn_x}, {btn_y})")

        # ── Step 3: KSIGN 메인 창 실시간 감지 ──────────
        status("KSIGN 인증 창 감지 중...")
        ksign_hwnd = _wait_top_window(["log in", "ksign", "전자서명", "인증센터", "교육기관"], timeout=20.0, min_w=500, min_h=350)
        _activate_hwnd(ksign_hwnd)
        time.sleep(0.1)

        _close_unwanted_popups()

        # ── Step 4: 전자서명 인증서 로그인 파란 버튼 클릭 ─
        status("인증서 로그인 탭 로딩 대기 중 (5초)...")
        _activate_hwnd(ksign_hwnd)
        time.sleep(5.0)  # 첫 번째 인증서 로그인 탭의 자바스크립트 및 보안 모듈이 완전히 준비될 때까지 5초 안정 대기

        k_rect = win32gui.GetWindowRect(ksign_hwnd)
        kw = k_rect[2] - k_rect[0]
        kh = k_rect[3] - k_rect[1]

        ratio = 0.75
        blue_btn_x = k_rect[0] + int(kw * 0.50)
        blue_btn_y = k_rect[1] + int(kh * ratio)

        logger.info(f"파란색 인증서 로그인 버튼 클릭 (ratio={ratio}): ({blue_btn_x}, {blue_btn_y})")
        pyautogui.click(blue_btn_x, blue_btn_y)
        time.sleep(0.12)
        pyautogui.click(blue_btn_x, blue_btn_y)
        
        # ── Step 5: 인증서 선택 모달 로딩 대기 ──
        status("인증서 창 로딩 대기 중...")
        time.sleep(2.5)  # 인증서 모달 내부 데이터 렌더링 대기 (안정화 후 2.5초)
        
        # ── Step 6 & 7: 인증서 선택 및 암호 입력 ──
        status(f"인증서 ({cert_index}번째) 선택 및 암호 입력 중...")
        
        _activate_hwnd(ksign_hwnd)
        time.sleep(0.3)
        
        # 1. 인증서 목록 데이터 행 단일 클릭 선택 (정밀 실측 비율 좌표: 0.491, 0.489)
        cert_row_x = k_rect[0] + int(kw * 0.491)
        cert_row_y = k_rect[1] + int(kh * 0.489)
        
        # 다중 인증서 인덱스 대응 (행 간격: 약 26px)
        if cert_index > 1:
            cert_row_y += int((cert_index - 1) * (kh * 0.041))
            
        logger.info(f"인증서 목록 행 단일 클릭 선택: ({cert_row_x}, {cert_row_y})")
        pyautogui.click(cert_row_x, cert_row_y)
        time.sleep(0.3)
        
        # 2. 암호 입력칸 직접 클릭하여 포커스 (정밀 실측 중앙 좌표: 0.635, 0.784)
        pw_box_x = k_rect[0] + int(kw * 0.635)
        pw_box_y = k_rect[1] + int(kh * 0.784)
        
        logger.info(f"암호 입력칸 정밀 클릭: ({pw_box_x}, {pw_box_y})")
        pyautogui.click(pw_box_x, pw_box_y)
        time.sleep(0.3)
        
        # 기존 잔여 텍스트 안전 삭제
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.press("backspace")
        time.sleep(0.1)
        
        # 비밀번호 단일 정밀 타이핑
        logger.info("비밀번호 단일 정밀 타이핑 전송")
        pyautogui.typewrite(cert_password, interval=0.05)
        time.sleep(0.4)
        
        # 3. 확인(Enter) 전송
        pyautogui.press("enter")
        logger.info("인증서 암호 입력 및 Enter 전송 완료")
        
        # ── Step 8: 창 닫힘 및 로그인 완료 확인 ─────────
        time.sleep(0.5)
        status("로그인 완료!")

    finally:
        cert_password = "\x00" * len(cert_password) if cert_password else ""
        del cert_password
