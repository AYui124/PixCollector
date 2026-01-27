"""Huey任务队列初始化."""
from huey import RedisExpireHuey

from config import Config

# 创建Huey实例
huey = RedisExpireHuey(
    'pixcollector',
    host=Config.HUEY_REDIS_HOST,
    port=int(Config.HUEY_REDIS_PORT),
    db=int(Config.HUEY_REDIS_DB),
    password=Config.HUEY_REDIS_PASSWORD,
    always_eager=False,  # 生产环境设置为False，开发环境可以设为True同步执行
    result=True,  # 存储任务结果
    store_none=False,  # 不存储None值
)
