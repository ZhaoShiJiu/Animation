"""
video_api.py — 视频导出/下载路由 + 清理。
从 app.py 拆分出来。
"""
import asyncio
import json
import logging

from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

from backend.config import (
    shanghai_tz,
    export_semaphore,
    VIDEO_STORAGE_DIR,
    VIDEO_CLEANUP_INTERVAL_SECONDS,
    VIDEO_DEFAULT_RETENTION_SECONDS,
    VIDEO_EXPIRATION_SECONDS,
)
from backend.models import VideoExportRequest
from backend.video_exporter import get_video_exporter
from backend.html_postprocessor import postprocess_html
from backend.share import get_share_record

logger = logging.getLogger(__name__)

async def export_video(video_request: VideoExportRequest, request: Request):
    """Export an HTML animation page to MP4 video via SSE progress stream."""
    # Resolve HTML content — prefer share_id, fall back to direct html
    html_content = None
    if video_request.share_id:
        record = get_share_record(video_request.share_id)
        if record:
            html_content = record.get("html") or ""
        if not html_content:
            raise HTTPException(status_code=404, detail="Share not found or expired")

    if not html_content and video_request.html:
        html_content = video_request.html

    if not html_content:
        raise HTTPException(status_code=400, detail="Either html or share_id is required")

    # 服务端后处理增强
    try:
        html_content = postprocess_html(html_content)
    except Exception:
        logger.exception("视频导出：HTML 后处理增强失败")

    exporter = get_video_exporter()
    progress_queue: asyncio.Queue = asyncio.Queue()
    queued = export_semaphore.locked()

    async def _push(status: str, percent: float, message: str):
        await progress_queue.put({
            "status": status, "percent": percent, "message": message,
        })

    retention = VIDEO_EXPIRATION_SECONDS.get(
        video_request.expires_in, VIDEO_DEFAULT_RETENTION_SECONDS
    )

    async def _do_export():
        return await exporter.export(
            html=html_content,
            width=video_request.width,
            height=video_request.height,
            fps=video_request.fps,
            duration_hint=video_request.duration_seconds,
            retention_seconds=retention,
            on_progress=_push,
        )

    async def event_generator():
        nonlocal queued

        if queued:
            yield f"data: {json.dumps({'event': 'queued', 'message': '导出任务排队中...'})}\n\n"

        async with export_semaphore:
            if queued:
                yield f"data: {json.dumps({'event': 'started', 'message': '导出任务开始执行'})}\n\n"

            render_task = asyncio.create_task(_do_export())

            while True:
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if render_task.done():
                        exc = render_task.exception()
                        if exc:
                            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
                        break
                    yield "data: {\"event\":\"heartbeat\"}\n\n"
                    continue

                if event["status"] == "complete":
                    try:
                        video_id = render_task.result()
                    except Exception as exc:
                        logger.exception("视频导出任务异常: %s", exc)
                        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
                        return
                    logger.info("视频导出完成 | video_id=%s", video_id)
                    yield f"data: {json.dumps({'event': '[DONE]', 'video_id': video_id})}\n\n"
                    return
                elif event["status"] == "error":
                    yield f"data: {json.dumps({'error': event['message']})}\n\n"
                    return
                else:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if await request.is_disconnected():
                    render_task.cancel()
                    break

    headers = {
        "Cache-Control": "no-store",
        "Content-Type": "text/event-stream; charset=utf-8",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), headers=headers)


async def download_video(video_id: str):
    """Download a rendered MP4 video by ID."""
    exporter = get_video_exporter()
    path = exporter.get_video_path(video_id)
    if not path:
        logger.warning("视频下载失败——未找到 | video_id=%s", video_id)
        raise HTTPException(status_code=404, detail="Video not found or expired")
    meta = exporter.get_metadata(video_id) or {}
    filename = f"animation_{video_id}.mp4"
    logger.info("视频下载 | video_id=%s | file=%s", video_id, filename)
    return FileResponse(path, media_type="video/mp4", filename=filename)


async def cleanup_expired_videos_once():
    exporter = get_video_exporter()
    exporter.cleanup_expired(VIDEO_DEFAULT_RETENTION_SECONDS)


async def cleanup_expired_videos_loop():
    while True:
        await cleanup_expired_videos_once()
        await asyncio.sleep(VIDEO_CLEANUP_INTERVAL_SECONDS)


