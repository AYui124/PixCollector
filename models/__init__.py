"""数据库模型初始化."""
from models.api_key import ApiKey
from models.artwork import Artwork
from models.collection_log import CollectionLog
from models.follow import Follow
from models.scheduler_config import SchedulerConfig
from models.system_config import SystemConfig
from models.user import User

__all__ = [
    'User',
    'Artwork',
    'Follow',
    'CollectionLog',
    'SchedulerConfig',
    'SystemConfig',
    'ApiKey'
]
