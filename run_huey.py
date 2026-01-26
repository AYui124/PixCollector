#!/usr/bin/env python3
"""Huey任务队列Worker运行脚本."""
import logging
import os
import signal
import sys

from huey.consumer import Consumer

import services.huey_service
from config import Config
from core.huey import huey

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
            'logs/huey_worker.log',
            encoding='utf-8',
            errors='ignore'
        ),
    ]
)
logger = logging.getLogger(__name__)


def main():
    """主函数."""
    logger.info("Starting Huey worker...")
    logger.info(f"Worker type: {Config.HUEY_WORKER_TYPE}")
    logger.info(f"Worker count: {Config.HUEY_WORKER_COUNT}")

    # 导入 huey_service 以注册所有任务
    services.huey_service.init()
    logger.info("huey_service imported and tasks registered")

    # 启动Consumer
    consumer = Consumer(
        huey,
        workers=Config.HUEY_WORKER_COUNT,
        worker_type=Config.HUEY_WORKER_TYPE,
        initial_delay=0.1,
        backoff=1.15,
        max_delay=Config.HUEY_TASK_TIMEOUT,
        health_check_interval=10,
        scheduler_interval=1,
        periodic=True,
        check_worker_health=True,
    )
    logger.info("Consumer created successfully")

    # 优雅退出处理
    def signal_handler(sig, frame):
        """处理终止信号."""
        logger.info("Shutting down Huey worker...")
        consumer.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 保持进程运行
    try:
        logger.info("Huey worker started, press Ctrl+C to stop")
        consumer.run()
    except KeyboardInterrupt:
        logger.info("Shutting down Huey worker...")
        consumer.shutdown()


if __name__ == '__main__':
    main()
