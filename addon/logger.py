import logging
import traceback
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "debug.log"
LOG_MAX_BYTES = 2 * 1024 * 1024  # 2 MB before simple rotation
LOG_BACKUP_COUNT = 3

_logger = None


def _get_logger():
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("no_sync_note_converter")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Avoid duplicate handlers on reload
    if logger.handlers:
        _logger = logger
        return logger

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    except Exception:
        # Fallback to no handler if file cannot be created
        _logger = logger
        return logger

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    _logger = logger
    return logger


def _rotate_if_needed():
    try:
        if not LOG_FILE.exists():
            return
        if LOG_FILE.stat().st_size < LOG_MAX_BYTES:
            return
        # Simple rotation: debug.log -> debug.log.1 -> debug.log.2 etc.
        for i in range(LOG_BACKUP_COUNT, 0, -1):
            src = LOG_FILE if i == 1 else Path(f"{LOG_FILE}.{i-1}")
            dst = Path(f"{LOG_FILE}.{i}")
            if src.exists():
                if dst.exists():
                    dst.unlink()
                src.rename(dst)
        # Re-create fresh log file and reattach handler
        global _logger
        if _logger:
            for h in list(_logger.handlers):
                h.close()
                _logger.removeHandler(h)
            _logger = None
        _get_logger().info("Log rotated")
    except Exception:
        pass


def log(level, msg, *args, exc_info=False):
    _rotate_if_needed()
    logger = _get_logger()
    try:
        if exc_info and isinstance(exc_info, BaseException):
            msg = f"{msg}: {exc_info}\n{traceback.format_exc()}"
            exc_info = False
        logger.log(level, msg, *args, exc_info=exc_info)
    except Exception:
        pass


def debug(msg, *args, exc_info=False):
    log(logging.DEBUG, msg, *args, exc_info=exc_info)


def info(msg, *args, exc_info=False):
    log(logging.INFO, msg, *args, exc_info=exc_info)


def warning(msg, *args, exc_info=False):
    log(logging.WARNING, msg, *args, exc_info=exc_info)


def error(msg, *args, exc_info=False):
    log(logging.ERROR, msg, *args, exc_info=exc_info)


def get_log_file_path() -> Path:
    return LOG_FILE


def read_log_text(max_bytes=500_000) -> str:
    try:
        if not LOG_FILE.exists():
            return ""
        # Read last max_bytes for performance
        size = LOG_FILE.stat().st_size
        with LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
                # Discard partial first line
                f.readline()
            return f.read()
    except Exception as e:
        return f"Failed to read log file: {e}"


def clear_log():
    try:
        if _logger:
            for h in list(_logger.handlers):
                h.flush()
        if LOG_FILE.exists():
            LOG_FILE.write_text("", encoding="utf-8")
        info("Log cleared by user")
        return True
    except Exception as e:
        error(f"Failed to clear log: {e}", exc_info=True)
        return False


def clear_log_on_startup():
    """Clear log file on Anki start (silent, no 'cleared by user' entry)."""
    try:
        if _logger:
            for h in list(_logger.handlers):
                try:
                    h.flush()
                except Exception:
                    pass
        if LOG_FILE.exists():
            # Truncate to avoid handler file descriptor issues; keep handler open
            # Reopen file via handler if needed - simplest is to write empty content
            try:
                LOG_FILE.write_text("", encoding="utf-8")
            except Exception:
                # Fallback: open and truncate
                with LOG_FILE.open("w", encoding="utf-8"):
                    pass
        return True
    except Exception as e:
        try:
            error(f"Failed to clear log on startup: {e}", exc_info=True)
        except Exception:
            pass
        return False


# Log addon load once
info("Logger initialized - %s", datetime.now().isoformat())
