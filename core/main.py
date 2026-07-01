"""应用入口"""
import atexit
import signal
import sys

from core.hooks import configure_hooks, restore_config
from core.platform import IS_MACOS, IS_WINDOWS, setup_frozen_path


def main():
    setup_frozen_path()

    if not IS_WINDOWS and not IS_MACOS:
        print("当前仅支持 Windows 和 macOS")
        sys.exit(1)

    print("正在配置 Claude Code hooks...")
    configure_hooks()

    atexit.register(restore_config)

    def signal_handler(_sig, _frame):
        restore_config()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    print("启动红绿灯监视器...")
    if IS_WINDOWS:
        from core.windows import WindowsTrayApp

        WindowsTrayApp().run()
    else:
        from core.macos import create_macos_app

        create_macos_app().run()


if __name__ == "__main__":
    main()
