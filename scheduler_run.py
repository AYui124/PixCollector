#!/usr/bin/env python3
"""定时任务调度器运行脚本（生产环境）."""
import os
import signal
import sys
import threading

from app import create_app
from scheduler import task_scheduler

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 确保logs目录存在
os.makedirs('logs', exist_ok=True)

# 创建事件对象用于保持进程运行
shutdown_event = threading.Event()


def main():
    """主函数."""
    # 创建应用
    app = create_app()

    # 启动调度器
    with app.app_context():
        task_scheduler.app = app
        task_scheduler.start()

    # 优雅退出处理
    def signal_handler(sig, frame):
        """处理终止信号."""
        print("\n正在关闭调度器...")
        shutdown_event.set()
        task_scheduler.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 保持进程运行
    try:
        print("调度器已启动，按 Ctrl+C 停止")
        shutdown_event.wait()
    except KeyboardInterrupt:
        print("\n正在关闭调度器...")
        task_scheduler.shutdown()


if __name__ == '__main__':
    main()
