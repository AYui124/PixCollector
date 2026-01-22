"""数据库连接和迁移配置."""
import logging

from flask import Flask
from flask_migrate import Migrate

from models import Base, db

logger = logging.getLogger(__name__)

# 创建Migrate实例
migrate = Migrate()


def init_db(app: Flask) -> None:
    """
    初始化数据库.

    Args:
        app: Flask应用实例
    """
    db.init_app(app)
    migrate.init_app(app, db)
    logger.info("Database initialized")


def create_tables(app: Flask) -> None:
    """
    创建所有数据库表.

    Args:
        app: Flask应用实例
    """
    with app.app_context():
        # models的实体类继承Base而不是db.Model，这里不能使用db
        Base.metadata.create_all(bind=db.engine)
        logger.info("Database tables created")
