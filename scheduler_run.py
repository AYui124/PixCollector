#!/usr/bin/env python3
"""定时任务调度器运行脚本（生产环境）."""
import logging
import os
import signal
import sys
import threading

from core.database import get_engine
from scheduler import task_scheduler

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 确保logs目录存在
os.makedirs('logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            'logs/scheduler.log',
            encoding='utf-8',
            errors='ignore'
        ),
    ]
)
logger = logging.getLogger(__name__)

# 创建事件对象用于保持进程运行
shutdown_event = threading.Event()


def main():
    """主函数."""
    # 初始化数据库引擎
    get_engine()

    # 启动调度器
    logger.info("Starting scheduler...")
    task_scheduler.start()

    # 优雅退出处理
    def signal_handler(sig, frame):
        """处理终止信号."""
        logger.info("正在关闭调度器...")
        shutdown_event.set()
        task_scheduler.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 保持进程运行
    try:
        logger.info("调度器已启动，按 Ctrl+C 停止")
        shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("正在关闭调度器...")
        task_scheduler.shutdown()


if __name__ == '__main__':
    main()
