"""
config.py — 全局配置、常量、信号量。
"""
import asyncio
import json
import os

import pytz

# ── 时区 ──
shanghai_tz = pytz.timezone("Asia/Shanghai")

# ── 凭证 ──
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT_DIR, "credentials.json"), encoding="utf-8") as f:
    credentials = json.load(f)
API_KEY = credentials["API_KEY"]
BASE_URL = credentials.get("BASE_URL", "")
MODEL = credentials.get("MODEL", "")
ENABLE_DEBUG_OUTPUT = credentials.get("ENABLE_DEBUG_OUTPUT", True)
MAX_CONCURRENT_GENERATION_TASKS = credentials.get("MAX_CONCURRENT_GENERATION_TASKS", 1)
MAX_PAPER_UPLOAD_BYTES = credentials.get("MAX_PAPER_UPLOAD_BYTES", 20 * 1024 * 1024)
MAX_PAPER_TEXT_CHARS = credentials.get("MAX_PAPER_TEXT_CHARS", 120000)
ACCESS_PASSPHRASES = credentials.get("ACCESS_PASSPHRASES")
MAX_CONCURRENT_EXPORT_TASKS = credentials.get("MAX_CONCURRENT_EXPORT_TASKS", 1)

# ── 信号量 ──
generation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATION_TASKS)
export_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXPORT_TASKS)

# ── 分享配置 ──
shared_html_links = {}
SHARE_STORAGE_DIR = os.path.join(_ROOT_DIR, "storage", "shared_html")
SHARE_CLEANUP_INTERVAL_SECONDS = 300
SHARE_EXPIRATION_SECONDS = {
    "1h": 60 * 60,
    "3h": 3 * 60 * 60,
    "6h": 6 * 60 * 60,
    "8h": 8 * 60 * 60,
    "1d": 24 * 60 * 60,
    "3d": 3 * 24 * 60 * 60,
    "7d": 7 * 24 * 60 * 60,
    "forever": None,
}

# ── 视频导出配置 ──
VIDEO_STORAGE_DIR = os.path.join(_ROOT_DIR, "storage", "exported_videos")
VIDEO_CLEANUP_INTERVAL_SECONDS = 300
VIDEO_DEFAULT_RETENTION_SECONDS = 60 * 60  # 1 hour
VIDEO_EXPIRATION_SECONDS = {
    "10m": 10 * 60,
    "1h": 60 * 60,
    "6h": 6 * 60 * 60,
    "1d": 24 * 60 * 60,
    "7d": 7 * 24 * 60 * 60,
}

# ── 动画配置 ──
DURATION_SECONDS_HINT = {
    "preview": 12,
    "short": 30,
    "medium": 60,
    "long": 90,
}

# ── LLM 客户端 ──
# LLM 调用统一由 backend/graph/__init__.py 的 ChatOpenAI 管理

if not API_KEY or API_KEY.startswith("sk-REPLACE_ME") or API_KEY == "<your-api-key>":
    raise RuntimeError(
        "请在 credentials.json 中配置有效的 API_KEY（当前为空或占位符）"
    )
