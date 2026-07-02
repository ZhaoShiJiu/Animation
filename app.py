"""
app.py — FastAPI 主应用（路由层）。

AI 生成逻辑由 LangGraph 编排：backend/graph/
"""
import asyncio
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Callable
from urllib.parse import parse_qs

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from backend.config import (
    shanghai_tz,
    ACCESS_PASSPHRASES,
    generation_semaphore,
    SHARE_EXPIRATION_SECONDS,
)
from backend.models import (
    PassphraseRequest,
    ShareRequest,
    VideoExportRequest,
    LogErrorRequest,
)
from backend.llm_stream import extract_pdf_text
from backend.share import (
    build_share_access_page,
    build_shared_viewer_page,
    create_qr_data_url,
    get_share_record,
    save_share_to_disk,
    cleanup_expired_shares_once,
    cleanup_expired_shares_loop,
    _hash_password,
    _verify_password,
)
from backend.video_api import (
    export_video,
    download_video,
    cleanup_expired_videos_once,
    cleanup_expired_videos_loop,
)
from backend.html_postprocessor import postprocess_html
from backend.logger import get_logger

# ── LangGraph ──
from backend.graph.graphs.paper_graph import build_paper_graph
from backend.graph.graphs.three_stage_graph import build_three_stage_graph
from backend.graph.sse_adapter import stream_graph_to_sse

# 模块级编译一次，全局复用
_paper_graph = build_paper_graph()
_full_graph = build_three_stage_graph()

logger = get_logger(__name__)

# -----------------------------------------------------------------------
# FastAPI 初始化
# -----------------------------------------------------------------------
app = FastAPI(title="AI Animation Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

templates = Jinja2Templates(directory="frontend/templates")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


# ── HTTP 请求日志中间件 ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info("→ %s %s | client=%s", request.method, request.url.path,
                request.client.host if request.client else "unknown")
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.time() - start_time) * 1000
        logger.exception("✗ %s %s | 耗时=%.0fms | 未捕获异常",
                         request.method, request.url.path, elapsed)
        raise
    elapsed = (time.time() - start_time) * 1000
    status_code = response.status_code
    if status_code >= 500:
        logger.error("✗ %s %s → %s | 耗时=%.0fms",
                     request.method, request.url.path, status_code, elapsed)
    elif status_code >= 400:
        logger.warning("← %s %s → %s | 耗时=%.0fms",
                      request.method, request.url.path, status_code, elapsed)
    else:
        logger.info("← %s %s → %s | 耗时=%.0fms",
                   request.method, request.url.path, status_code, elapsed)
    return response


# -----------------------------------------------------------------------
# 辅助函数
# -----------------------------------------------------------------------
def _normalize_settings(settings: Any) -> Dict[str, Any]:
    """将 settings 统一为 dict——支持 JSON 字符串或已解析的 dict。"""
    if isinstance(settings, str):
        try:
            parsed = json.loads(settings or "{}")
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return settings if isinstance(settings, dict) else {}


# ── SSE 端点工厂 ──

_SSE_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Type": "text/event-stream; charset=utf-8",
    "X-Accel-Buffering": "no",
}


async def _stream_endpoint(
    graph,
    input_builder: Callable[[], Dict[str, Any]],
    request: Request,
    *,
    semaphore: asyncio.Semaphore = None,
) -> StreamingResponse:
    """通用 SSE 流式端点工厂。"""
    if semaphore is None:
        semaphore = generation_semaphore

    queued = semaphore.locked()

    async def event_generator():
        if queued:
            yield f"data: {json.dumps({'event': 'queued'}, ensure_ascii=False)}\n\n"
        async with semaphore:
            if queued:
                yield f"data: {json.dumps({'event': 'started'}, ensure_ascii=False)}\n\n"
            try:
                input_state = input_builder()
                async for chunk in stream_graph_to_sse(graph, input_state, request):
                    if await request.is_disconnected():
                        logger.info("客户端断开连接")
                        break
                    yield chunk
            except Exception as e:
                logger.exception("Graph 执行异常")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), headers=_SSE_HEADERS)


# -----------------------------------------------------------------------
# 配置 & 认证
# -----------------------------------------------------------------------

@app.get("/config")
async def get_public_config():
    return {"requiresPassphrase": bool(ACCESS_PASSPHRASES)}


@app.post("/verify-passphrase")
async def verify_passphrase(passphrase_request: PassphraseRequest):
    if ACCESS_PASSPHRASES and passphrase_request.passphrase not in ACCESS_PASSPHRASES:
        logger.warning("暗号验证失败")
        raise HTTPException(status_code=403, detail="暗号错误")
    logger.info("暗号验证通过")
    return {"ok": True}


# -----------------------------------------------------------------------
# 分享
# -----------------------------------------------------------------------

@app.post("/share")
async def create_share_link(share_request: ShareRequest, request: Request):
    ttl_seconds = SHARE_EXPIRATION_SECONDS.get(share_request.expiresIn)
    if share_request.expiresIn not in SHARE_EXPIRATION_SECONDS:
        raise HTTPException(status_code=400, detail="Invalid expiration")
    if not share_request.html.strip():
        raise HTTPException(status_code=400, detail="HTML content is required")

    try:
        enhanced_html = postprocess_html(share_request.html)
    except Exception:
        logger.exception("HTML 后处理增强失败，使用原始 HTML")
        enhanced_html = share_request.html

    share_id = secrets.token_urlsafe(16)
    created_at = datetime.now(shanghai_tz)
    expires_at = created_at + timedelta(seconds=ttl_seconds) if ttl_seconds else None
    hashed_password = _hash_password(share_request.password) if share_request.password else ""
    record = {
        "html": build_shared_viewer_page(enhanced_html, share_request.sourceWidth, share_request.sourceHeight),
        "password": hashed_password,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    from backend.config import shared_html_links
    shared_html_links[share_id] = record
    await save_share_to_disk(share_id, record)
    share_url = str(request.url_for("read_shared_html", share_id=share_id))
    logger.info("分享链接已创建 | share_id=%s | expires_in=%s | url=%s",
                share_id, share_request.expiresIn, share_url)
    return {
        "url": share_url,
        "qrCode": create_qr_data_url(share_url),
        "createdAt": created_at.isoformat(),
        "expiresAt": expires_at.isoformat() if expires_at else None,
        "password": share_request.password,
    }


@app.get("/share/{share_id}", response_class=HTMLResponse)
async def read_shared_html(share_id: str):
    shared = await get_share_record(share_id)
    if not shared:
        raise HTTPException(status_code=404, detail="Share link expired or not found")
    if shared["password"]:
        return HTMLResponse(build_share_access_page())
    return HTMLResponse(shared["html"])


@app.post("/share/{share_id}", response_class=HTMLResponse)
async def verify_shared_html(share_id: str, request: Request):
    shared = await get_share_record(share_id)
    if not shared:
        raise HTTPException(status_code=404, detail="Share link expired or not found")
    body = (await request.body()).decode()
    form = parse_qs(body)
    password = form.get("password", [""])[0]
    if shared["password"] and not _verify_password(password, shared["password"]):
        return HTMLResponse(build_share_access_page("访问密码错误"), status_code=403)
    return HTMLResponse(shared["html"])


# -----------------------------------------------------------------------
# 日志上报
# -----------------------------------------------------------------------

@app.post("/api/log-error")
async def log_frontend_error(error_request: LogErrorRequest):
    for err in error_request.errors:
        logger.error(
            "前端错误 | 消息=%s | URL=%s | UA=%s | 时间=%s | 堆栈=%s | 附加=%s",
            err.get("message", "unknown")[:300],
            err.get("url", ""),
            err.get("userAgent", "")[:200],
            err.get("timestamp", ""),
            (err.get("stack") or "")[:500],
            (err.get("extra") or "")[:500],
        )
    return {"ok": True}


# -----------------------------------------------------------------------
# AI 生成（LangGraph）
# -----------------------------------------------------------------------

@app.post("/paper/generate")
async def generate_paper(
    request: Request,
    pdf: UploadFile = File(...),
    focus: str = Form(""),
    settings: str = Form("{}"),
):
    """PDF 论文 → 动画（单阶段直达）。"""
    parsed_settings = _normalize_settings(settings)

    async def build_input():
        paper = await extract_pdf_text(pdf)
        return {
            "topic": paper.get("filename", "论文"),
            "settings": parsed_settings,
            "pdf_filename": paper["filename"],
            "pdf_text": paper["text"],
            "pdf_truncated": paper["truncated"],
            "focus": focus.strip(),
            "retry_count": 0,
            "max_retries": 2,
        }

    return await _stream_endpoint(_paper_graph, build_input, request)


@app.post("/generate/full")
async def generate_full(request: Request):
    """主题 → 文案 → 动画指导 → 动画 三阶段全流程。

    请求体：{"topic": "...", "settings": {...}}
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体必须是 JSON")
    topic = body.get("topic", "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic 不能为空")
    settings = _normalize_settings(body.get("settings", {}))

    return await _stream_endpoint(
        _full_graph,
        lambda: {
            "topic": topic,
            "settings": settings,
            "retry_count": 0,
            "max_retries": 2,
        },
        request,
    )


# -----------------------------------------------------------------------
# 视频导出
# -----------------------------------------------------------------------

@app.post("/export/video")
async def export_video_route(video_request: VideoExportRequest, request: Request):
    """Export an HTML animation page to MP4 video via SSE progress stream."""
    return await export_video(video_request, request)


@app.get("/video/{video_id}")
async def download_video_route(video_id: str):
    """Download a rendered MP4 video by ID."""
    return await download_video(video_id)


# -----------------------------------------------------------------------
# 首页
# -----------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"time": datetime.now(shanghai_tz).strftime("%Y%m%d%H%M%S")},
    )


# -----------------------------------------------------------------------
# 启动
# -----------------------------------------------------------------------

@app.on_event("startup")
async def startup_tasks():
    await cleanup_expired_shares_once()
    asyncio.create_task(cleanup_expired_shares_loop())
    await cleanup_expired_videos_once()
    asyncio.create_task(cleanup_expired_videos_loop())


# -----------------------------------------------------------------------
# 本地启动
# -----------------------------------------------------------------------
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
