"""
MemeNews Admin Panel - FastAPI Application
"""

import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Depends, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .auth import AuthManager
from .settings import SettingsManager
from .scheduler_control import SchedulerControl

# FastAPI 앱 생성
app = FastAPI(
    title="MemeNews Admin",
    description="MemeNews 콘텐츠 관리 시스템",
    version="1.0.0",
)

# 세션 미들웨어 추가
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# 정적 파일 및 템플릿 설정
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 매니저 초기화
auth_manager = AuthManager()
settings_manager = SettingsManager()
scheduler_control = SchedulerControl()


def get_current_user(request: Request) -> Optional[str]:
    """현재 로그인한 사용자 반환"""
    return request.session.get("user")


def require_login(request: Request):
    """로그인 필수 의존성"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user


# ===== Health Check =====
@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ===== Authentication =====
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """로그인 페이지"""
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """로그인 처리"""
    if auth_manager.verify_password(username, password):
        request.session["user"] = username
        request.session["login_time"] = datetime.now().isoformat()
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "아이디 또는 비밀번호가 올바르지 않습니다."
    })


@app.get("/logout")
async def logout(request: Request):
    """로그아웃"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


# ===== Dashboard =====
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: str = Depends(require_login)):
    """대시보드 메인 페이지"""
    stats = {
        "total_generated": scheduler_control.get_total_generated(),
        "today_generated": scheduler_control.get_today_generated(),
        "scheduler_status": scheduler_control.get_status(),
        "channels": scheduler_control.get_channel_stats(),
    }
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "page": "dashboard"
    })


# ===== Settings =====
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: str = Depends(require_login)):
    """설정 페이지"""
    settings = settings_manager.get_all_settings()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "page": "settings"
    })


@app.post("/settings/api-keys")
async def save_api_keys(
    request: Request,
    user: str = Depends(require_login),
    gemini_api_key: str = Form(default=""),
    youtube_client_id: str = Form(default=""),
    youtube_client_secret: str = Form(default=""),
    youtube_refresh_token: str = Form(default=""),
    tiktok_access_token: str = Form(default=""),
    instagram_access_token: str = Form(default=""),
    instagram_account_id: str = Form(default=""),
    slack_webhook: str = Form(default=""),
    discord_webhook: str = Form(default=""),
):
    """API 키 저장"""
    api_keys = {
        "gemini_api_key": gemini_api_key,
        "youtube_client_id": youtube_client_id,
        "youtube_client_secret": youtube_client_secret,
        "youtube_refresh_token": youtube_refresh_token,
        "tiktok_access_token": tiktok_access_token,
        "instagram_access_token": instagram_access_token,
        "instagram_account_id": instagram_account_id,
        "slack_webhook": slack_webhook,
        "discord_webhook": discord_webhook,
    }

    # 빈 값은 기존 값 유지
    for key, value in list(api_keys.items()):
        if not value:
            del api_keys[key]

    settings_manager.save_api_keys(api_keys)
    return RedirectResponse(url="/settings?saved=true", status_code=302)


# ===== Password Change =====
@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request, user: str = Depends(require_login)):
    """비밀번호 변경 페이지"""
    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "user": user,
        "page": "change_password"
    })


@app.post("/change-password")
async def change_password(
    request: Request,
    user: str = Depends(require_login),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """비밀번호 변경"""
    if new_password != confirm_password:
        return templates.TemplateResponse("change_password.html", {
            "request": request,
            "user": user,
            "error": "새 비밀번호가 일치하지 않습니다.",
            "page": "change_password"
        })

    if not auth_manager.verify_password(user, current_password):
        return templates.TemplateResponse("change_password.html", {
            "request": request,
            "user": user,
            "error": "현재 비밀번호가 올바르지 않습니다.",
            "page": "change_password"
        })

    if len(new_password) < 8:
        return templates.TemplateResponse("change_password.html", {
            "request": request,
            "user": user,
            "error": "비밀번호는 8자 이상이어야 합니다.",
            "page": "change_password"
        })

    auth_manager.change_password(user, new_password)
    return RedirectResponse(url="/settings?password_changed=true", status_code=302)


# ===== Content Generation =====
@app.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request, user: str = Depends(require_login)):
    """콘텐츠 생성 페이지"""
    channels = scheduler_control.get_available_channels()
    return templates.TemplateResponse("generate.html", {
        "request": request,
        "user": user,
        "channels": channels,
        "page": "generate"
    })


@app.post("/generate/{channel}")
async def generate_content(
    request: Request,
    channel: str,
    user: str = Depends(require_login),
    dry_run: bool = Form(default=False)
):
    """콘텐츠 생성 실행"""
    try:
        result = await scheduler_control.run_channel(channel, dry_run=dry_run)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ===== Scheduler Control =====
@app.get("/scheduler", response_class=HTMLResponse)
async def scheduler_page(request: Request, user: str = Depends(require_login)):
    """스케줄러 관리 페이지"""
    status = scheduler_control.get_status()
    schedule = scheduler_control.get_schedule()
    return templates.TemplateResponse("scheduler.html", {
        "request": request,
        "user": user,
        "status": status,
        "schedule": schedule,
        "page": "scheduler"
    })


@app.post("/scheduler/start")
async def start_scheduler(request: Request, user: str = Depends(require_login)):
    """스케줄러 시작"""
    scheduler_control.start()
    return {"success": True, "status": "running"}


@app.post("/scheduler/stop")
async def stop_scheduler(request: Request, user: str = Depends(require_login)):
    """스케줄러 중지"""
    scheduler_control.stop()
    return {"success": True, "status": "stopped"}


# ===== Logs =====
@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, user: str = Depends(require_login)):
    """로그 조회 페이지"""
    logs = scheduler_control.get_recent_logs(100)
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "page": "logs"
    })


@app.get("/api/logs")
async def get_logs(
    request: Request,
    user: str = Depends(require_login),
    limit: int = 50,
    offset: int = 0
):
    """로그 API"""
    logs = scheduler_control.get_recent_logs(limit, offset)
    return {"logs": logs}


# ===== Output Files =====
@app.get("/output", response_class=HTMLResponse)
async def output_page(request: Request, user: str = Depends(require_login)):
    """생성된 콘텐츠 조회"""
    files = scheduler_control.get_output_files()
    return templates.TemplateResponse("output.html", {
        "request": request,
        "user": user,
        "files": files,
        "page": "output"
    })
