#!/usr/bin/env python3
"""PixCollector启动脚本."""
import os
import sys

from app import create_app
from config import Config
from scheduler import task_scheduler

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 确保logs目录存在
os.makedirs('logs', exist_ok=True)

# 创建应用
app = create_app()


if __name__ == '__main__':
    if Config.DEBUG:
        task_scheduler.app = app
        with app.app_context():
            task_scheduler.start()

    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=Config.DEBUG
    )
