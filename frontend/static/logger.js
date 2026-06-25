/**
 * logger.js — 前端统一日志模块
 *
 * 功能:
 *   - 结构化日志，带时间戳和级别标识
 *   - 支持 DEBUG / INFO / WARN / ERROR 四个级别
 *   - 自动将 WARN/ERROR 维持 console.warn/console.error 行为
 *   - 可选: 将严重错误回传后端 /api/log-error
 *
 * 用法:
 *   Logger.debug('调试信息', { extra: 'data' });
 *   Logger.info('操作成功');
 *   Logger.warn('警告信息');
 *   Logger.error('错误信息', error);
 *   Logger.setLevel(Logger.DEBUG);  // 设置最低输出级别
 */
(function (global) {
    'use strict';

    const LEVELS = {
        DEBUG: 0,
        INFO: 1,
        WARN: 2,
        ERROR: 3,
        SILENT: 4,
    };

    const LEVEL_LABELS = ['DEBUG', 'INFO', 'WARN', 'ERROR'];
    const LEVEL_COLORS = {
        DEBUG: '#6b7280',
        INFO: '#059669',
        WARN: '#d97706',
        ERROR: '#dc2626',
    };

    let currentLevel = LEVELS.DEBUG;
    let reportErrorsToBackend = true;

    function formatTime() {
        const now = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const ms = String(now.getMilliseconds()).padStart(3, '0');
        return `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}.${ms}`;
    }

    function log(level, label, args) {
        if (level < currentLevel) return;

        const time = formatTime();
        const prefix = `[${time}] [${label}]`;

        switch (level) {
            case LEVELS.DEBUG:
                console.debug(prefix, ...args);
                break;
            case LEVELS.INFO:
                console.info(
                    `%c${prefix}`,
                    `color: ${LEVEL_COLORS.INFO}; font-weight: bold;`,
                    ...args
                );
                break;
            case LEVELS.WARN:
                console.warn(prefix, ...args);
                break;
            case LEVELS.ERROR:
                console.error(prefix, ...args);
                // 将严重错误回传后端
                if (reportErrorsToBackend && args.length > 0) {
                    sendErrorToBackend(args[0], args.slice(1));
                }
                break;
        }
    }

    let errorSendQueue = [];
    let errorSendTimer = null;

    function sendErrorToBackend(error, extra) {
        // 避免过于频繁发送（至少间隔 5 秒）
        const payload = {
            message: error instanceof Error ? error.message : String(error),
            stack: error instanceof Error ? error.stack : undefined,
            extra: extra.length ? JSON.stringify(extra) : undefined,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
        };
        errorSendQueue.push(payload);
        if (!errorSendTimer) {
            errorSendTimer = setTimeout(flushErrorQueue, 5000);
        }
    }

    function flushErrorQueue() {
        if (errorSendQueue.length === 0) {
            errorSendTimer = null;
            return;
        }
        const batch = errorSendQueue.splice(0, errorSendQueue.length);
        errorSendTimer = null;
        fetch('/api/log-error', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ errors: batch }),
        }).catch(() => {
            // 静默失败，避免日志发送本身产生无限循环
        });
    }

    const Logger = {
        DEBUG: LEVELS.DEBUG,
        INFO: LEVELS.INFO,
        WARN: LEVELS.WARN,
        ERROR: LEVELS.ERROR,
        SILENT: LEVELS.SILENT,

        debug(...args) {
            log(LEVELS.DEBUG, 'DEBUG', args);
        },

        info(...args) {
            log(LEVELS.INFO, 'INFO', args);
        },

        warn(...args) {
            log(LEVELS.WARN, 'WARN', args);
        },

        error(...args) {
            log(LEVELS.ERROR, 'ERROR', args);
        },

        /** 设置最低输出级别 */
        setLevel(level) {
            currentLevel = level;
        },

        /** 启用/禁用错误回传后端 */
        setReportErrors(enabled) {
            reportErrorsToBackend = enabled;
        },

        /** 创建一个带标签的子 logger */
        scope(tag) {
            return {
                debug(...args) { log(LEVELS.DEBUG, `${tag}`, args); },
                info(...args) { log(LEVELS.INFO, `${tag}`, args); },
                warn(...args) { log(LEVELS.WARN, `${tag}`, args); },
                error(...args) { log(LEVELS.ERROR, `${tag}`, args); },
            };
        },
    };

    global.Logger = Logger;

    // 启动日志
    Logger.info('前端日志系统初始化完成', { level: 'DEBUG', reportErrors: reportErrorsToBackend });

})(window);
