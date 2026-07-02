"""
share.py — 分享链接生成、存储、验证、清理。
从 app.py 拆分出来。
"""
import asyncio
import base64
import html
import io
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any

import qrcode
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

from backend.config import (
    shanghai_tz,
    shared_html_links,
    SHARE_STORAGE_DIR,
    SHARE_CLEANUP_INTERVAL_SECONDS,
    SHARE_EXPIRATION_SECONDS,
)
from backend.html_postprocessor import postprocess_html

logger = logging.getLogger(__name__)

def build_share_access_page(error_message: str = ""):
    error_html = f'<p class="error">{html.escape(error_message)}</p>' if error_message else ""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>访问分享动画</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 24px; font-family: 'MiSans', 'HarmonyOS Sans SC', 'Microsoft YaHei', sans-serif; color: #000; background: linear-gradient(90deg, rgba(0,0,0,.06) 1px, transparent 1px), linear-gradient(0deg, rgba(0,0,0,.06) 1px, transparent 1px), #fff; background-size: 48px 48px; }}
        .card {{ width: min(420px, 100%); padding: 28px; background: #fff; border: 1px solid #000; box-shadow: 12px 12px 0 #000; display: grid; gap: 14px; }}
        p {{ margin: 0; font-size: .72rem; font-weight: 900; letter-spacing: .18em; }}
        h1 {{ margin: 0; font-size: clamp(2rem, 7vw, 4rem); letter-spacing: -.08em; line-height: .95; }}
        input {{ min-height: 52px; border: 1px solid #000; padding: 0 14px; font: inherit; }}
        input:focus, button:focus-visible {{ outline: 2px solid #000; outline-offset: 3px; }}
        button {{ min-height: 50px; border: 1px solid #000; background: #000; color: #fff; font: inherit; font-weight: 900; cursor: pointer; }}
        button:hover {{ background: #fff; color: #000; }}
        .error {{ color: #b10000; letter-spacing: 0; }}
    </style>
</head>
<body>
    <form class="card" method="post">
        <p>SHARED ANIMATION</p>
        <h1>请输入访问密码</h1>
        {error_html}
        <input name="password" type="password" placeholder="访问密码" required autofocus>
        <button type="submit">进入</button>
    </form>
</body>
</html>"""


def create_qr_data_url(value: str):
    image = qrcode.make(value)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_shared_viewer_page(html_content: str, source_width: int, source_height: int):
    safe_width = min(max(source_width, 320), 4096)
    safe_height = min(max(source_height, 320), 4096)
    escaped_srcdoc = html.escape(html_content, quote=True)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>ZSJ-观想录分享</title>
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; background: #fff; }}
        body {{ display: grid; place-items: center; font-family: 'MiSans', 'HarmonyOS Sans SC', 'Microsoft YaHei', sans-serif; }}
        .viewer {{ width: min(100vw, calc(100vh * {safe_width} / {safe_height})); height: min(100vh, calc(100vw * {safe_height} / {safe_width})); border: 1px solid #000; background: #111; overflow: hidden; }}
        iframe {{ width: {safe_width}px; height: {safe_height}px; border: 0; display: block; background: #fff; transform: scale(var(--viewer-scale, 1)); transform-origin: top left; }}
        .orientation-prompt {{ position: fixed; inset: 0; z-index: 10; display: none; place-items: center; padding: 24px; background: rgba(255, 255, 255, .94); color: #000; text-align: center; font-weight: 900; }}
        .orientation-prompt.visible {{ display: grid; }}
        .orientation-card {{ display: grid; gap: 16px; max-width: 420px; padding: 24px; border: 1px solid #000; background: #fff; box-shadow: 8px 8px 0 #000; }}
        .orientation-card button {{ min-height: 44px; padding: 0 16px; border: 1px solid #000; background: #000; color: #fff; font: inherit; font-weight: 900; cursor: pointer; }}
    </style>
</head>
<body>
    <main class="viewer"><iframe sandbox="allow-scripts allow-same-origin" srcdoc="{escaped_srcdoc}"></iframe></main>
    <div id="orientation-prompt" class="orientation-prompt">
        <div class="orientation-card">
            <div>移动端适配较差，推荐PC端查看</div>
            <button type="button" id="orientation-dismiss">继续竖屏观看</button>
        </div>
    </div>
    <script>
        (function () {{
            var dismissed = false;
            var prompt = document.getElementById('orientation-prompt');
            var viewer = document.querySelector('.viewer');
            var sourceWidth = {safe_width};
            var sourceHeight = {safe_height};
            document.getElementById('orientation-dismiss').addEventListener('click', function () {{
                dismissed = true;
                prompt.classList.remove('visible');
            }});
            function fitViewer() {{
                var scale = Math.min(viewer.clientWidth / sourceWidth, viewer.clientHeight / sourceHeight);
                viewer.style.setProperty('--viewer-scale', scale.toString());
            }}
            function shouldShowMobilePrompt() {{
                return !dismissed && /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
            }}
            function updatePrompt() {{
                fitViewer();
                prompt.classList.toggle('visible', shouldShowMobilePrompt());
            }}
            window.addEventListener('resize', updatePrompt);
            window.addEventListener('orientationchange', updatePrompt);
            updatePrompt();
        }})();
    </script>
</body>
</html>"""


def get_share_paths(share_id: str):
    return {
        "meta": os.path.join(SHARE_STORAGE_DIR, f"{share_id}.json"),
        "html": os.path.join(SHARE_STORAGE_DIR, f"{share_id}.html"),
    }


def serialize_share_record(record: Dict[str, Any]):
    return {
        "password": record["password"],
        "created_at": record["created_at"].isoformat(),
        "expires_at": record["expires_at"].isoformat() if record["expires_at"] else None,
    }


def parse_share_datetime(value: str):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return shanghai_tz.localize(parsed)
    return parsed.astimezone(shanghai_tz)


def load_share_from_disk(share_id: str):
    paths = get_share_paths(share_id)
    if not os.path.exists(paths["meta"]) or not os.path.exists(paths["html"]):
        return None
    with open(paths["meta"], "r", encoding="utf-8") as file:
        meta = json.load(file)
    with open(paths["html"], "r", encoding="utf-8") as file:
        html_content = file.read()
    record = {
        "html": html_content,
        "password": meta["password"],
        "created_at": parse_share_datetime(meta["created_at"]),
        "expires_at": parse_share_datetime(meta["expires_at"]) if meta.get("expires_at") else None,
    }
    shared_html_links[share_id] = record
    return record


def save_share_to_disk(share_id: str, record: Dict[str, Any]):
    os.makedirs(SHARE_STORAGE_DIR, exist_ok=True)
    paths = get_share_paths(share_id)
    with open(paths["html"], "w", encoding="utf-8") as file:
        file.write(record["html"])
    with open(paths["meta"], "w", encoding="utf-8") as file:
        json.dump(serialize_share_record(record), file, ensure_ascii=False, indent=2)


def delete_share(share_id: str):
    shared_html_links.pop(share_id, None)
    for path in get_share_paths(share_id).values():
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def get_share_record(share_id: str):
    record = shared_html_links.get(share_id) or load_share_from_disk(share_id)
    if not record:
        return None
    if record["expires_at"] and record["expires_at"] <= datetime.now(shanghai_tz):
        delete_share(share_id)
        return None
    return record


def cleanup_expired_shares_once():
    now = datetime.now(shanghai_tz)
    os.makedirs(SHARE_STORAGE_DIR, exist_ok=True)
    for share_id, record in list(shared_html_links.items()):
        if record["expires_at"] and record["expires_at"] <= now:
            delete_share(share_id)
    for filename in os.listdir(SHARE_STORAGE_DIR):
        if not filename.endswith(".json"):
            continue
        share_id = filename[:-5]
        record = load_share_from_disk(share_id)
        if record and record["expires_at"] and record["expires_at"] <= now:
            delete_share(share_id)


async def cleanup_expired_shares_loop():
    while True:
        cleanup_expired_shares_once()
        await asyncio.sleep(SHARE_CLEANUP_INTERVAL_SECONDS)
