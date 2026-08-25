@echo off
chcp 65001 > nul
echo.
echo ====================================================
echo   Brity 자동 로그인 - exe 빌드 스크립트
echo ====================================================
echo.

:: 가상환경 활성화 (있는 경우)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: PyInstaller로 단일 exe 빌드
pyinstaller ^
    --onefile ^
    --windowed ^
    --name BrityAutoLogin ^
    --icon NONE ^
    --hidden-import pywinauto ^
    --hidden-import pywinauto.base_wrapper ^
    --hidden-import pywinauto.controls ^
    --hidden-import comtypes ^
    --hidden-import comtypes.client ^
    --hidden-import cryptography ^
    --collect-all pywinauto ^
    main.py

echo.
if exist "dist\BrityAutoLogin.exe" (
    echo [성공] dist\BrityAutoLogin.exe 생성 완료!
    echo.
    echo 배포 방법:
    echo   BrityAutoLogin.exe 파일만 선생님들께 전달하세요.
    echo   처음 실행 시 설정 창이 자동으로 열립니다.
) else (
    echo [실패] 빌드 오류가 발생했습니다. 위 로그를 확인하세요.
)
echo.
pause
