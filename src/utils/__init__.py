import logging
import sys
import os

_USER_DATA_DIRNAME = ".manju-forge"
_LEGACY_USER_DATA_DIRNAME = ".lumen-x"


# User data directory for logs, config, and data
def get_user_data_dir() -> str:
    """Returns the user data directory for the application.

    On first invocation, transparently migrates the legacy ``~/.lumen-x``
    directory to ``~/.manju-forge`` if the new path does not yet exist.
    Existing installations therefore keep their logs, config, projects,
    and webview storage without manual intervention.
    """
    home = os.path.expanduser("~")
    new_path = os.path.join(home, _USER_DATA_DIRNAME)
    legacy_path = os.path.join(home, _LEGACY_USER_DATA_DIRNAME)

    if not os.path.exists(new_path) and os.path.isdir(legacy_path):
        try:
            os.rename(legacy_path, new_path)
        except OSError:
            # Cross-device or permission issue — keep using legacy path so
            # the user still sees their data, even if migration failed.
            return legacy_path

    return new_path


def get_log_dir() -> str:
    """Returns the log directory."""
    log_dir = os.path.join(get_user_data_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def setup_logging(level=logging.INFO, log_file=None):
    """Configures the logging system."""
    handlers = []
    
    # If no log file specified, use default in user directory
    if log_file is None:
        try:
            log_file = os.path.join(get_log_dir(), "app.log")
        except OSError as exc:
            print(
                f"WARNING: Log directory unavailable in user home: {exc}. "
                "Falling back to console logging.",
                file=sys.stderr,
            )
            log_file = None
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        try:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            handlers.append(file_handler)
        except OSError as exc:
            # In restricted environments (tests/sandbox), fallback to console-only logging.
            print(
                f"WARNING: File logging unavailable at '{log_file}': {exc}. "
                "Falling back to console logging.",
                file=sys.stderr,
            )
    
    # 添加控制台处理器（会被重定向到日志文件）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    handlers.append(console_handler)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def get_logger(name):
    """Returns a logger with the specified name."""
    return logging.getLogger(name)

