"""数据库连接管理（不依赖Flask）."""
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, Integer, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from config import Config

# 全局引擎实例
_engine: Engine | None = None
_session_factory: sessionmaker | None = None


# 声明式基类
class Base(DeclarativeBase):
    """SQLAlchemy声明式基类."""
    pass


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )


def get_engine() -> Engine:
    """
    获取或创建数据库引擎.

    Returns:
        Engine: SQLAlchemy引擎实例
    """
    global _engine

    if _engine is None:
        _engine = create_engine(
            Config.SQLALCHEMY_DATABASE_URI,
            pool_pre_ping=Config.SQLALCHEMY_ENGINE_OPTIONS.get(
                'pool_pre_ping', True
            ),
            pool_recycle=Config.SQLALCHEMY_ENGINE_OPTIONS.get(
                'pool_recycle', 3600
            ),
            echo=Config.DEBUG
        )

    return _engine


def get_session_factory() -> sessionmaker:
    """
    获取或创建Session工厂.

    Returns:
        sessionmaker: Session工厂
    """
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            bind=engine,
            autocommit=False,  # 关闭自动提交，由session_scope统一管理
            autoflush=False,   # 关闭自动刷新，避免隐式查询
            expire_on_commit=False  # 提交后不失效实例，方便块外访问属性
        )
    return _session_factory


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    提供事务范围的Session.

    Yields:
        Session: SQLAlchemy Session实例

    Example:
        with session_scope() as session:
            user = session.query(User).first()
            user.name = 'new name'
            # 自动提交或回滚
    """
    session_factory = get_session_factory()
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_engine() -> None:
    """
    关闭数据库引擎，释放连接池资源（项目优雅退出时调用）.
    适用于CLI/定时任务等非常驻进程，常驻服务（如API）无需调用.
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()  # 关闭引擎并释放所有连接
        _engine = None
    # 重置会话工厂，下次调用会重新创建
    _session_factory = None


def create_all_tables():
    """创建所有数据库表."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
