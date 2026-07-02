"""
logger.py — 统一日志模块

功能:
  - 文件日志（按大小轮转，默认 10MB/5 个备份）
  - 控制台彩色日志
  - 结构化格式：时间 | 级别 | 模块:函数:行号 | 消息
  - 各模块通过 get_logger(__name__) 获取 logger 实例

配置:
  日志文件位于项目根目录的 logs/ 子目录。
  日志级别由 credentials.json 中的 LOG_LEVEL 字段控制（默认 INFO）。
  也可通过环境变量 LOG_LEVEL 覆盖。
"""

import logging
import logging.handlers
import os
import sys
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
_LOG_DIR = os.path.join(_BASE_DIR, "storage", "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "app.log")
_LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_LOG_BACKUP_COUNT = 5
_LOG_MAX_AGE_DAYS = 30  # 超过 30 天的日志自动清理
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ---------------------------------------------------------------------------
# 预定义的日志名称 → 颜色映射（用于控制台输出）
# ---------------------------------------------------------------------------

_COLORS = {
    "DEBUG":    "\033[36m",   # 青色
    "INFO":     "\033[32m",   # 绿色
    "WARNING":  "\033[33m",   # 黄色
    "ERROR":    "\033[31m",   # 红色
    "CRITICAL": "\033[35m",   # 紫色
    "RESET":    "\033[0m",
}

# 高亮模块名
_MODULE_COLOR = "\033[1;34m"  # 粗体蓝色


class _ColoredFormatter(logging.Formatter):
    """控制台彩色日志格式化器."""

    def format(self, record: logging.LogRecord) -> str:
        level_color = _COLORS.get(record.levelname, "")
        reset = _COLORS["RESET"]

        # 保存原始的 levelname 和 name 以便恢复
        orig_levelname = record.levelname
        orig_name = record.name

        record.levelname = f"{level_color}{record.levelname}{reset}"
        record.name = f"{_MODULE_COLOR}{record.name}{reset}"

        result = super().format(record)

        record.levelname = orig_levelname
        record.name = orig_name

        return result


# ---------------------------------------------------------------------------
# 初始化（模块加载时执行一次）
# ---------------------------------------------------------------------------

_log_initialized = False


def _cleanup_old_logs():
    """清理超过 _LOG_MAX_AGE_DAYS 天的旧日志文件。"""
    try:
        import time
        cutoff = time.time() - _LOG_MAX_AGE_DAYS * 86400
        for fname in os.listdir(_LOG_DIR):
            fpath = os.path.join(_LOG_DIR, fname)
            if os.path.isfile(fpath) and fname.startswith("app.log"):
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
    except Exception:
        pass  # 清理失败不影响日志初始化


def _init_logging():
    """配置根 logger 的 handler（仅执行一次）。"""
    global _log_initialized
    if _log_initialized:
        return
    _log_initialized = True

    # 确保日志目录存在
    os.makedirs(_LOG_DIR, exist_ok=True)

    # 清理过期日志文件
    _cleanup_old_logs()

    # 读取日志级别
    log_level_str = os.environ.get("LOG_LEVEL", "").upper()
    if not log_level_str:
        try:
            creds_path = os.path.join(_BASE_DIR, "credentials.json")
            if os.path.exists(creds_path):
                with open(creds_path, "r", encoding="utf-8") as f:
                    creds = json.load(f)
                log_level_str = creds.get("LOG_LEVEL", "INFO").upper()
            else:
                log_level_str = "INFO"
        except Exception:
            log_level_str = "INFO"

    log_level = getattr(logging, log_level_str, logging.INFO)

    # 根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除已有的 handler（避免重复添加）
    root_logger.handlers.clear()

    # ── 文件 handler（带轮转） ──
    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_LOG_MAX_BYTES,
        backupCount=_LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # 文件保留所有级别
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
    root_logger.addHandler(file_handler)

    # ── 控制台 handler ──
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # 控制台也输出所有级别
    console_handler.setFormatter(_ColoredFormatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
    root_logger.addHandler(console_handler)

    # 启动日志
    root_logger.info("=" * 60)
    root_logger.info("日志系统初始化完成 | 级别: %s | 文件: %s", log_level_str, _LOG_FILE)
    root_logger.info("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger 实例。

    用法:
        from backend.logger import get_logger
        logger = get_logger(__name__)
        logger.info("请求处理中...")
        logger.error("发生错误", exc_info=True)
    """
    _init_logging()
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# 便捷函数（保持与原有 debug_llm 类似的调用方式）
# ---------------------------------------------------------------------------

def log_llm_request(provider: str, model: str, messages: list, settings: dict):
    """记录 LLM 请求信息（结构化）。"""
    logger = get_logger("llm.request")
    logger.info("→ 发送请求 | provider=%s model=%s message_count=%d",
                provider, model, len(messages))
    # 详细信息记录到 DEBUG
    logger.debug("请求详情:\n  provider: %s\n  model: %s\n  settings: %s\n  messages: %s",
                 provider, model,
                 json.dumps(settings, ensure_ascii=False, indent=2),
                 json.dumps(messages, ensure_ascii=False, indent=2))


def log_llm_response_start(provider: str):
    """记录 LLM 响应开始。"""
    logger = get_logger("llm.response")
    logger.info("← 开始接收响应 | provider=%s", provider)


def log_llm_response_end():
    """记录 LLM 响应结束。"""
    logger = get_logger("llm.response")
    logger.info("← 响应完成")


def log_llm_error(provider: str, error: str):
    """记录 LLM 错误。"""
    logger = get_logger("llm.error")
    logger.error("LLM 调用失败 | provider=%s | error=%s", provider, str(error)[:500])


def log_llm_stream_chunk(chunk: str):
    """记录流式 chunk（仅 DEBUG 级别）。"""
    logger = get_logger("llm.stream")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("chunk: %s", chunk[:200])


# ---------------------------------------------------------------------------
# 启动时打印日志文件路径
# ---------------------------------------------------------------------------

_init_logging()
