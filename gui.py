"""
gui.py - Brity 자동 로그인 GUI 모듈

SetupWindow  : 최초 실행 시 사용자 이름 + 인증서 암호 입력 창
StatusWindow : 자동 로그인 진행 상태 표시 (토스트 스타일)
"""
import json
import logging
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import winreg

def _set_windows_autostart(enable: bool = True):
    """Windows 시작 프로그램 레지스트리에 BrityAutoLogin 등록/해제"""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "BrityAutoLogin"
    exe_path = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
            logger.info(f"시작 프로그램 등록 성공: {exe_path}")
        else:
            try:
                winreg.DeleteValue(key, app_name)
                logger.info("시작 프로그램 해제 완료")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        logger.error(f"시작 프로그램 레지스트리 설정 실패: {e}")

# ── 색상 팔레트 (다크 블루 테마) ─────────────────────
C = {
    "bg":          "#0f172a",   # 배경
    "surface":     "#1e293b",   # 카드/입력창 배경
    "border":      "#334155",   # 테두리
    "primary":     "#3b82f6",   # 기본 파란색
    "primary_dk":  "#2563eb",   # 진한 파란색
    "text":        "#f1f5f9",   # 기본 텍스트
    "muted":       "#94a3b8",   # 흐린 텍스트
    "text_dim":    "#94a3b8",   # 흐린 텍스트 (호환용)
    "success":     "#10b981",   # 성공 초록
    "error":       "#ef4444",   # 오류 빨강
    "warn":        "#f59e0b",   # 경고 노랑
}

FONT_TITLE  = ("맑은 고딕", 13, "bold")
FONT_LABEL  = ("맑은 고딕", 9)
FONT_INPUT  = ("맑은 고딕", 11)
FONT_BTN    = ("맑은 고딕", 11, "bold")
FONT_SMALL  = ("맑은 고딕", 8)
FONT_STATUS = ("맑은 고딕", 10)


def _center(root, w, h):
    """창을 화면 중앙에 배치"""
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")


def _entry(parent, var, show=None) -> tk.Entry:
    """스타일이 적용된 입력창 생성"""
    e = tk.Entry(
        parent, textvariable=var, show=show,
        font=FONT_INPUT,
        bg=C["surface"], fg=C["text"],
        insertbackground=C["text"],
        relief="flat", bd=0,
        highlightthickness=1,
        highlightbackground=C["border"],
        highlightcolor=C["primary"],
    )
    return e


def _label(parent, text, font=None, fg=None, **kwargs) -> tk.Label:
    return tk.Label(
        parent, text=text,
        font=font or FONT_LABEL,
        bg=C["bg"], fg=fg or C["muted"],
        **kwargs,
    )


def _button(parent, text, command, bg=None, fg="white", **kwargs) -> tk.Button:
    return tk.Button(
        parent, text=text, command=command,
        font=FONT_BTN,
        bg=bg or C["primary"], fg=fg,
        activebackground=C["primary_dk"], activeforeground="white",
        relief="flat", bd=0, cursor="hand2",
        **kwargs,
    )


# ─────────────────────────────────────────────────────────────────
#  SetupWindow - 최초 설정 창
# ─────────────────────────────────────────────────────────────────

class SetupWindow:
    """최초 실행 시 인증서 정보 입력 창"""

    def __init__(self, root: tk.Tk, base_dir: str):
        self.root = root
        self.base_dir = base_dir
        self._build()

    def _build(self):
        self.root.title("Brity 자동 로그인 — 초기 설정")
        self.root.resizable(False, False)
        self.root.configure(bg=C["bg"])
        _center(self.root, 440, 620)

        # ── 헤더 ─────────────────────────────────────
        header = tk.Frame(self.root, bg=C["primary"], height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="🔐  Brity 자동 로그인 설정",
            font=FONT_TITLE, bg=C["primary"], fg="white",
        ).pack(expand=True)

        # ── 본문 ─────────────────────────────────────
        body = tk.Frame(self.root, bg=C["bg"], padx=32, pady=20)
        body.pack(fill="both", expand=True)

        # 1. 인증서 사용자 이름 및 순선 선택
        _label(body, "인증서 사용자 이름 (성함 또는 구분용)").pack(anchor="w", pady=(0, 4))
        self.var_name = tk.StringVar(value="첫번째 인증서")
        name_entry = _entry(body, self.var_name)
        name_entry.pack(fill="x", ipady=6, pady=(0, 8))

        # 인증서 순번 선택 (인증서가 여러 개 있을 때 몇 번째 선택할지)
        _label(body, "선택할 인증서 위치 (순번)").pack(anchor="w", pady=(0, 4))
        self.var_cert_index = tk.IntVar(value=1)
        idx_frame = tk.Frame(body, bg=C["bg"])
        idx_frame.pack(fill="x", pady=(0, 14))

        for idx, text in [(1, "1번째 (기본)"), (2, "2번째"), (3, "3번째"), (4, "4번째")]:
            tk.Radiobutton(
                idx_frame, text=text, value=idx, variable=self.var_cert_index,
                font=FONT_SMALL, bg=C["bg"], fg=C["text"],
                selectcolor=C["surface"], activebackground=C["bg"],
                activeforeground=C["text"], cursor="hand2",
            ).pack(side="left", padx=(0, 8))

        # 2. 인증서 암호
        _label(body, "인증서 암호").pack(anchor="w", pady=(0, 4))
        self.var_pw = tk.StringVar()
        pw_entry = _entry(body, self.var_pw, show="●")
        pw_entry.pack(fill="x", ipady=6, pady=(0, 4))

        # 암호 표시 토글
        self._show_pw = False
        def _toggle_pw():
            self._show_pw = not self._show_pw
            pw_entry.config(show="" if self._show_pw else "●")
            btn_toggle_pw.config(text="🙈 암호 숨기기" if self._show_pw else "👁  암호 보기")

        btn_toggle_pw = tk.Button(
            body, text="👁  암호 보기", command=_toggle_pw,
            font=FONT_SMALL, bg=C["bg"], fg=C["text_dim"],
            activebackground=C["bg"], activeforeground=C["text"],
            relief="flat", bd=0, cursor="hand2",
        )
        btn_toggle_pw.pack(anchor="e", pady=(0, 14))

        # 3. Brity Messenger 실행 파일/바로가기 선택
        _label(body, "Brity Messenger 경로 (선택 사항)").pack(anchor="w", pady=(0, 4))
        path_frame = tk.Frame(body, bg=C["bg"])
        path_frame.pack(fill="x", pady=(0, 14))
        
        from macro_engine import find_brity_exe
        self.var_app_path = tk.StringVar(value=find_brity_exe())
        path_entry = _entry(path_frame, self.var_app_path)
        path_entry.pack(side="left", fill="x", expand=True, ipady=6)
        
        def _browse():
            from tkinter import filedialog
            chosen = filedialog.askopenfilename(
                title="Brity Messenger 실행 파일 또는 바로 가기 선택",
                filetypes=[("실행 파일 및 바로가기", "*.exe;*.lnk"), ("모든 파일", "*.*")],
                parent=self.root,
            )
            if chosen:
                self.var_app_path.set(chosen)

        tk.Button(
            path_frame, text="📂 찾기", command=_browse,
            font=FONT_SMALL, bg=C["surface"], fg=C["text"],
            activebackground=C["border"], activeforeground="white",
            relief="flat", bd=0, cursor="hand2", padx=10,
        ).pack(side="right", padx=(6, 0))

        pw_entry.bind("<Return>", lambda _: self._save())

        # 암호 표시 체크박스
        self.show_pw = tk.BooleanVar()
        tk.Checkbutton(
            body, text="암호 표시", variable=self.show_pw,
            font=FONT_SMALL, bg=C["bg"], fg=C["muted"],
            activebackground=C["bg"], selectcolor=C["surface"],
            command=lambda: pw_entry.config(show="" if self.show_pw.get() else "●"),
        ).pack(anchor="w", pady=(0, 8))

        # Windows 시작 시 자동 실행 체크박스
        self.auto_start = tk.BooleanVar(value=True)
        tk.Checkbutton(
            body, text="🚀  Windows 부팅 시 자동 실행", variable=self.auto_start,
            font=FONT_SMALL, bg=C["bg"], fg=C["text"],
            activebackground=C["bg"], selectcolor=C["surface"],
        ).pack(anchor="w", pady=(0, 20))

        # 보안 안내 박스
        notice = tk.Frame(body, bg=C["surface"], padx=14, pady=10)
        notice.pack(fill="x", pady=(0, 22))
        tk.Label(
            notice,
            text="🔒  비밀번호는 이 PC에만 암호화하여 저장됩니다.\n     외부 서버로 전송되지 않습니다.",
            font=FONT_SMALL, bg=C["surface"], fg=C["muted"],
            justify="left",
        ).pack(anchor="w")

        # 저장 버튼
        _button(body, "저장 및 자동 로그인 시작", self._save, pady=12).pack(fill="x")

        # 하단 안내
        _label(
            body,
            "설정 변경 시: config.json 과 key.bin 삭제 후 재실행",
            font=FONT_SMALL,
        ).pack(pady=(14, 0))

    def _save(self):
        name = self.var_name.get().strip()
        pw   = self.var_pw.get()

        if not name:
            messagebox.showwarning("입력 오류", "사용자 이름을 입력하세요.", parent=self.root)
            return
        if not pw:
            messagebox.showwarning("입력 오류", "인증서 암호를 입력하세요.", parent=self.root)
            return

        try:
            from encryptor import encrypt
            config = {
                "app_path": self.var_app_path.get().strip() or r"C:\BrityWorks\BrityMessenger\BrityMessenger.exe",
                "cert_username": name,
                "cert_index": self.var_cert_index.get(),
                "cert_password_encrypted": encrypt(pw),
                "auto_start": self.auto_start.get(),
            }
            config_path = os.path.join(self.base_dir, "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            # Windows 시작 프로그램 레지스트리 설정 (실패해도 무시하고 진행)
            try:
                _set_windows_autostart(self.auto_start.get())
            except Exception as reg_err:
                logger.error(f"레지스트리 설정 에러 무시: {reg_err}")

            logger.info(f"설정 저장 완료: {config_path}")

        except Exception as e:
            logger.error(f"설정 저장 중 에러: {e}")
            messagebox.showerror("저장 오류", f"설정 저장에 실패했습니다:\n{e}", parent=self.root)
            return

        # 저장 완료 → 안내 후 창 닫기 및 매크로 실행
        saved_pw = pw
        app_path = config["app_path"]
        cert_idx = config["cert_index"]
        
        messagebox.showinfo("설정 완료", "인증서 정보가 안전하게 저장되었습니다.\n자동 로그인을 시작합니다.", parent=self.root)
        
        # 설정 창 완벽히 파괴 후 메인 루프 깔끔히 탈출
        self.root.destroy()
        
        # 깨끗한 새 루프에서 상태창 연동 매크로 실행
        _run_macro_window(name, saved_pw, app_path, cert_idx)


# ─────────────────────────────────────────────────────────────────
#  StatusWindow - 진행 상태 토스트 창
# ─────────────────────────────────────────────────────────────────

class StatusWindow:
    """자동 로그인 진행 상태를 화면 우측 하단에 표시"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._done = False
        self._build()

    def _build(self):
        self.root.title("Brity 자동 로그인")
        self.root.resizable(False, False)
        self.root.configure(bg=C["bg"])
        self.root.attributes("-topmost", True)

        # 화면 우측 하단
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 360, 160
        self.root.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 60}")

        frame = tk.Frame(self.root, bg=C["bg"], padx=22, pady=18)
        frame.pack(fill="both", expand=True)

        # 제목
        tk.Label(
            frame, text="🔐  Brity 자동 로그인",
            font=("맑은 고딕", 10, "bold"),
            bg=C["bg"], fg=C["primary"],
        ).pack(anchor="w")

        # 상태 텍스트
        self.var_status = tk.StringVar(value="⏳  시작 중...")
        self.lbl_status = tk.Label(
            frame, textvariable=self.var_status,
            font=FONT_STATUS, bg=C["bg"], fg=C["text"],
        )
        self.lbl_status.pack(anchor="w", pady=(10, 8))

        # 프로그레스 바
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Brity.Horizontal.TProgressbar",
            troughcolor=C["surface"],
            background=C["primary"],
            thickness=6,
        )
        self.progress = ttk.Progressbar(
            frame, mode="indeterminate", length=310,
            style="Brity.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x")
        self.progress.start(12)

    def update_status(self, msg: str):
        """스레드에서 호출 가능한 상태 업데이트"""
        self.root.after(0, lambda: self.var_status.set(f"⏳  {msg}"))

    def show_success(self):
        if self._done:
            return
        self._done = True
        self.var_status.set("✅  로그인 완료!")
        self.lbl_status.config(fg=C["success"])
        self.progress.stop()
        self.progress.config(value=100, mode="determinate")
        self.root.after(3000, self.root.destroy)

    def show_error(self, err_msg: str):
        if self._done:
            return
        self._done = True
        self.var_status.set("❌  오류가 발생했습니다")
        self.lbl_status.config(fg=C["error"])
        self.progress.stop()
        self.progress.destroy()

        frame = self.root.winfo_children()[0]

        tk.Label(
            frame,
            text=err_msg[:55] + ("..." if len(err_msg) > 55 else ""),
            font=FONT_SMALL, bg=C["bg"], fg=C["error"],
        ).pack(anchor="w", pady=(4, 0))

        _button(
            frame, "설정 초기화 후 재실행", self._reset,
            bg=C["error"], pady=6,
        ).pack(anchor="w", pady=(8, 0))

    def _reset(self):
        """config.json + key.bin 삭제 후 창 닫기"""
        import main as _main
        for fname in ("config.json", "key.bin"):
            path = os.path.join(_main.BASE_DIR, fname)
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"삭제: {path}")
        self.root.destroy()
        messagebox.showinfo(
            "초기화 완료",
            "설정이 초기화되었습니다.\n프로그램을 다시 실행하세요.",
        )


# ─────────────────────────────────────────────────────────────────
#  내부 헬퍼: 매크로 실행 + 상태 창 연동
# ─────────────────────────────────────────────────────────────────

def _run_macro_window(cert_username: str, cert_password: str, app_path: str, cert_index: int = 1):
    """상태 창을 열고 별도 스레드에서 매크로 실행"""
    import macro_engine

    root = tk.Tk()
    win  = StatusWindow(root)

    def _worker():
        try:
            # ── 0. GitHub 자동 업데이트 확인 (최대 1.5초 타임아웃) ──
            try:
                import updater
                has_update, new_ver, dl_url = updater.check_for_update(current_version="v3.8", timeout_sec=1.5)
                if has_update and dl_url:
                    win.update_status(f"새 버전({new_ver}) 발견! 자동 업데이트 중...")
                    if updater.apply_update(dl_url, status_callback=win.update_status):
                        return
            except Exception as up_err:
                logger.debug(f"업데이트 확인 건너뜀: {up_err}")

            macro_engine.run_login(
                cert_username=cert_username,
                cert_password=cert_password,
                status_callback=win.update_status,
                app_path=app_path,
                cert_index=cert_index,
            )
            root.after(0, win.show_success)
        except Exception as exc:
            logger.exception("자동 로그인 오류")
            root.after(0, lambda: win.show_error(str(exc)))

    threading.Thread(target=_worker, daemon=True).start()
    root.mainloop()
