"""
video_exporter.py — HTML to MP4 video export module.

Two rendering paths:
  1. HyperFrames (primary)   — for HTML with data-composition-id attributes
  2. Playwright (fallback)   — universal browser recording for any HTML

Usage:
    exporter = VideoExporter()
    video_id = await exporter.export(html, width=1920, height=1080, fps=24,
                                      on_progress=progress_callback)
"""

import os
import re
import json
import secrets
import shutil
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable

import pytz

shanghai_tz = pytz.timezone("Asia/Shanghai")

# ---------------------------------------------------------------------------
# HyperFrames project skeleton files
# ---------------------------------------------------------------------------

_HF_PACKAGE_JSON = """{
  "name": "animation-export",
  "private": true,
  "type": "module",
  "scripts": {
    "render": "npx --yes hyperframes@0.6.121 render"
  }
}"""

_HF_HYPERFRAMES_JSON = """{
  "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
  "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
  "paths": {
    "blocks": "compositions",
    "components": "compositions/components",
    "assets": "assets"
  }
}"""

_HF_META_TEMPLATE = '{"id": "{id}", "name": "{id}", "createdAt": "{created_at}"}'


# ---------------------------------------------------------------------------
# VideoExporter
# ---------------------------------------------------------------------------

class VideoExporter:
    """Manages video export from HTML animation pages."""

    # ------------------------------------------------------------------
    # Playwright network sandbox
    # ------------------------------------------------------------------

    # CDN domains allowed during rendering (GSAP, MathJax, fonts)
    _ALLOWED_CDN_DOMAINS = {
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "cdn.jsdelivr.net",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "unpkg.com",
    }

    @staticmethod
    async def _block_external_requests(route):
        """Block external requests except to known CDN domains.

        Allows data: URIs, about:blank, and requests to whitelisted CDNs.
        All other requests (fetch calls, external images, unknown hosts)
        are aborted to prevent SSRF and data exfiltration.
        """
        url = route.request.url
        if url.startswith(("data:", "about:")):
            await route.continue_()
            return
        # Allow known CDN hosts (for GSAP, MathJax, fonts)
        try:
            from urllib.parse import urlparse
            host = urlparse(url).hostname or ""
            if host in VideoExporter._ALLOWED_CDN_DOMAINS or host.endswith(
                tuple("." + d for d in VideoExporter._ALLOWED_CDN_DOMAINS)
            ):
                await route.continue_()
                return
        except Exception:
            pass
        await route.abort()

    def __init__(self, storage_dir: str = None, temp_dir: str = None):
        base = os.path.dirname(__file__)
        self.storage_dir = storage_dir or os.path.join(base, "exported_videos")
        self.temp_dir = temp_dir or os.path.join(base, "temp_render")
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def has_hyperframes_markup(html: str) -> bool:
        """Check if HTML contains HyperFrames data-composition-id attribute."""
        return bool(re.search(r'data-composition-id\s*=', html, re.IGNORECASE))

    @staticmethod
    def parse_duration(html: str, default: float = 30.0) -> float:
        """Extract animation duration from <meta name='animation-duration'>."""
        match = re.search(
            r'<meta\s+name=["\']animation-duration["\']\s+content=["\']([\d.]+)["\']',
            html, re.IGNORECASE,
        )
        if match:
            return float(match.group(1))
        return default

    @staticmethod
    def parse_resolution(html: str) -> tuple:
        """Extract resolution from data-width/data-height or meta viewport."""
        w = re.search(r'data-width=["\'](\d+)["\']', html)
        h = re.search(r'data-height=["\'](\d+)["\']', html)
        if w and h:
            return int(w.group(1)), int(h.group(1))
        vp = re.search(r'width\s*=\s*(\d+).*?height\s*=\s*(\d+)', html, re.IGNORECASE)
        if vp:
            return int(vp.group(1)), int(vp.group(2))
        return 1920, 1080

    # ------------------------------------------------------------------
    # HyperFrames rendering path
    # ------------------------------------------------------------------

    async def _hyperframes_render(
        self,
        html: str,
        video_id: str,
        width: int,
        height: int,
        fps: int,
        quality: str = "standard",
        on_progress: Optional[Callable[..., Awaitable[None]]] = None,
    ) -> str:
        """Render HTML → MP4 via HyperFrames CLI.

        Creates a temporary HyperFrames project directory, writes the
        animation HTML as index.html, and invokes the render subprocess.
        """
        project_dir = os.path.join(self.temp_dir, video_id)
        output_path = os.path.join(self.storage_dir, f"{video_id}.mp4")

        try:
            # --- Create project skeleton ---
            os.makedirs(project_dir, exist_ok=True)

            with open(os.path.join(project_dir, "index.html"), "w", encoding="utf-8") as fh:
                fh.write(html)
            with open(os.path.join(project_dir, "package.json"), "w", encoding="utf-8") as fh:
                fh.write(_HF_PACKAGE_JSON)
            with open(os.path.join(project_dir, "hyperframes.json"), "w", encoding="utf-8") as fh:
                fh.write(_HF_HYPERFRAMES_JSON)
            now_iso = datetime.now(shanghai_tz).isoformat()
            with open(os.path.join(project_dir, "meta.json"), "w", encoding="utf-8") as fh:
                fh.write(_HF_META_TEMPLATE.format(id=video_id, created_at=now_iso))

            if on_progress:
                await on_progress("initializing", 5, "启动 HyperFrames 渲染引擎...")

            # --- Run render ---
            cmd = [
                "npx", "--yes", "hyperframes@0.6.121", "render",
                "--quiet",
                "-o", output_path,
                "-f", str(fps),
                "-q", quality,
                "--format", "mp4",
                ".",
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            last_pct = 5
            async for line in proc.stdout:
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue
                pct_match = re.search(r'(\d{1,3})%', line_str)
                if pct_match:
                    raw = int(pct_match.group(1))
                    last_pct = min(85, 5 + int(raw * 0.8))
                    if on_progress:
                        await on_progress("rendering", last_pct,
                                          f"HyperFrames 渲染中... {raw}%")

            await proc.wait()

            if proc.returncode != 0:
                raise RuntimeError(
                    f"HyperFrames render exited with code {proc.returncode}"
                )

            # --- Locate output ---
            if not os.path.exists(output_path):
                default = os.path.join(project_dir, "renders", f"{video_id}.mp4")
                if os.path.exists(default):
                    shutil.move(default, output_path)
                else:
                    # Search for any mp4 in the project dir
                    found = None
                    for root, _dirs, files in os.walk(project_dir):
                        for fname in files:
                            if fname.endswith(".mp4"):
                                found = os.path.join(root, fname)
                                break
                        if found:
                            break
                    if found:
                        shutil.move(found, output_path)
                    else:
                        raise RuntimeError(
                            "HyperFrames render completed but no MP4 output found"
                        )

            if on_progress:
                await on_progress("encoding", 90, "正在完成编码...")

            return output_path

        finally:
            try:
                shutil.rmtree(project_dir, ignore_errors=True)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Playwright recording path (fallback)
    # ------------------------------------------------------------------

    async def _playwright_record(
        self,
        html: str,
        video_id: str,
        width: int,
        height: int,
        fps: int,
        duration: float,
        on_progress: Optional[Callable[..., Awaitable[None]]] = None,
    ) -> str:
        """Record HTML animation → MP4 via Playwright headless Chromium.

        Opens the HTML in a headless browser, records the viewport as WebM,
        then converts to MP4 via FFmpeg.
        """
        output_path = os.path.join(self.storage_dir, f"{video_id}.mp4")
        temp_dir = os.path.join(self.temp_dir, video_id)
        os.makedirs(temp_dir, exist_ok=True)

        try:
            from playwright.async_api import async_playwright

            if on_progress:
                await on_progress("initializing", 5, "启动无头浏览器...")

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--disable-background-networking",
                        "--disable-sync",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-web-security",
                    ],
                )
                context = await browser.new_context(
                    viewport={"width": width, "height": height},
                    record_video_dir=temp_dir,
                    record_video_size={"width": width, "height": height},
                    # Block external network requests for security
                    extra_http_headers={
                        "Content-Security-Policy": "default-src 'none'; "
                                                    "script-src 'unsafe-inline'; "
                                                    "style-src 'unsafe-inline'; "
                                                    "img-src data:; "
                                                    "font-src data:; "
                                                    "media-src data:; "
                                                    "connect-src 'none';",
                    },
                )
                page = await context.new_page()

                # Block all external requests at the network level
                await page.route("**/*", self._block_external_requests)

                # Load HTML with a timeout guard
                await page.set_content(html, wait_until="load", timeout=30000)

                if on_progress:
                    await on_progress("recording", 20, "正在录制动画...")

                # Wait for the animation duration with progress updates
                record_duration = duration + 2  # 2s buffer
                elapsed = 0.0
                step = 1.0
                while elapsed < record_duration:
                    await asyncio.sleep(step)
                    elapsed += step
                    pct = min(85, 20 + int((elapsed / record_duration) * 65))
                    if on_progress:
                        await on_progress(
                            "recording", pct,
                            f"录制中... {min(int(elapsed), int(duration))}s / {int(duration)}s",
                        )

                # Retrieve video path BEFORE closing context
                webm_path = None
                if page.video:
                    vp = await page.video.path()
                    if vp and os.path.exists(vp):
                        webm_path = vp

                await context.close()
                await browser.close()

            if not webm_path or not os.path.exists(webm_path):
                # Try to find any webm in the temp dir
                candidates = [
                    os.path.join(temp_dir, f)
                    for f in os.listdir(temp_dir)
                    if f.endswith(".webm")
                ]
                if candidates:
                    webm_path = max(candidates, key=os.path.getsize)

            if not webm_path or not os.path.exists(webm_path):
                raise RuntimeError("Playwright recording produced no video file")

            # FFmpeg: WebM → MP4
            if on_progress:
                await on_progress("encoding", 90, "正在转码为 MP4...")

            await self._webm_to_mp4(webm_path, output_path, fps)

            return output_path

        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # FFmpeg helper
    # ------------------------------------------------------------------

    @staticmethod
    async def _webm_to_mp4(input_path: str, output_path: str, fps: int):
        """Convert WebM video to H.264 MP4 using FFmpeg."""
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-an",  # no audio track
            output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(
                f"FFmpeg conversion failed (exit {proc.returncode})"
            )

    # ------------------------------------------------------------------
    # Main export entry point
    # ------------------------------------------------------------------

    async def export(
        self,
        html: str,
        width: int = 1920,
        height: int = 1080,
        fps: int = 24,
        duration_hint: Optional[float] = None,
        quality: str = "standard",
        retention_seconds: Optional[int] = None,
        on_progress: Optional[Callable[..., Awaitable[None]]] = None,
    ) -> str:
        """Export an HTML animation page to MP4 video.

        Auto-detects the rendering path:
          - ``data-composition-id`` present  → HyperFrames (deterministic)
          - absent                          → Playwright (universal)

        Parameters
        ----------
        html : str
            Complete animation HTML source.
        width, height : int
            Output resolution.
        fps : int
            Frame rate (12–60).
        duration_hint : float or None
            Animation duration in seconds; parsed from the HTML meta tag
            when not provided.
        quality : str
            ``"draft"`` | ``"standard"`` | ``"high"`` (HyperFrames only).
        on_progress : callable(status, percent, message) or None
            Async callback for SSE progress streaming.

        Returns
        -------
        video_id : str
            Unique ID for retrieving the rendered MP4.
        """
        video_id = secrets.token_urlsafe(16)

        if duration_hint is None:
            duration_hint = self.parse_duration(html)

        if on_progress:
            await on_progress("starting", 0, "正在准备视频导出...")

        use_hf = self.has_hyperframes_markup(html)

        try:
            if use_hf:
                if on_progress:
                    await on_progress("starting", 2,
                                      "检测到 HyperFrames 格式，使用确定性渲染...")
                try:
                    await self._hyperframes_render(
                        html, video_id, width, height, fps, quality, on_progress,
                    )
                except Exception as exc:
                    if on_progress:
                        await on_progress(
                            "fallback", 5,
                            f"HyperFrames 渲染失败 ({str(exc)[:60]})，切换到备用录制模式...",
                        )
                    use_hf = False  # fall through to Playwright

            if not use_hf:
                if on_progress:
                    await on_progress("starting", 2, "使用浏览器录制模式...")
                await self._playwright_record(
                    html, video_id, width, height, fps, duration_hint, on_progress,
                )
        except Exception as exc:
            if on_progress:
                await on_progress("error", 0, f"视频导出失败: {str(exc)[:80]}")
            raise

        # Persist metadata
        now = datetime.now(shanghai_tz)
        metadata = {
            "video_id": video_id,
            "width": width,
            "height": height,
            "fps": fps,
            "duration_seconds": duration_hint,
            "created_at": now.isoformat(),
            "retention_seconds": retention_seconds,
            "rendering_path": "hyperframes" if use_hf else "playwright",
        }
        meta_path = os.path.join(self.storage_dir, f"{video_id}.json")
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, ensure_ascii=False, indent=2)

        if on_progress:
            await on_progress("complete", 100, "视频导出完成！")

        return video_id

    # ------------------------------------------------------------------
    # Video retrieval / lifecycle
    # ------------------------------------------------------------------

    def get_video_path(self, video_id: str) -> Optional[str]:
        """Return the MP4 file path for *video_id*, or ``None``."""
        meta_path = os.path.join(self.storage_dir, f"{video_id}.json")
        if not os.path.exists(meta_path):
            return None
        mp4_path = os.path.join(self.storage_dir, f"{video_id}.mp4")
        if os.path.exists(mp4_path):
            return mp4_path
        return None

    def get_metadata(self, video_id: str) -> Optional[dict]:
        """Return metadata dict for *video_id*, or ``None``."""
        meta_path = os.path.join(self.storage_dir, f"{video_id}.json")
        if not os.path.exists(meta_path):
            return None
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None

    def delete_video(self, video_id: str):
        """Delete a video and its metadata file."""
        meta_path = os.path.join(self.storage_dir, f"{video_id}.json")
        mp4_path = os.path.join(self.storage_dir, f"{video_id}.mp4")
        for p in (meta_path, mp4_path):
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass

    def cleanup_expired(self, default_max_age_seconds: int):
        """Remove expired videos.

        Uses per-video ``retention_seconds`` from metadata if present,
        otherwise falls back to *default_max_age_seconds*.
        """
        now = datetime.now(shanghai_tz)
        for filename in os.listdir(self.storage_dir):
            if not filename.endswith(".json"):
                continue
            meta_path = os.path.join(self.storage_dir, filename)
            try:
                with open(meta_path, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
                created_str = meta.get("created_at")
                if not created_str:
                    continue
                retention = meta.get("retention_seconds") or default_max_age_seconds
                created_at = datetime.fromisoformat(created_str)
                if now - created_at > timedelta(seconds=retention):
                    video_id = meta.get("video_id", filename[:-5])
                    self.delete_video(video_id)
            except Exception:
                continue


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_exporter: Optional[VideoExporter] = None


def get_video_exporter() -> VideoExporter:
    """Return the module-level ``VideoExporter`` singleton."""
    global _exporter
    if _exporter is None:
        _exporter = VideoExporter()
    return _exporter
