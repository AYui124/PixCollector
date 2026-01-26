"""基础Repository类."""
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from sqlalchemy import func, select

from core.database import BaseModel
from core.session import session_scope

T = TypeVar('T', bound=BaseModel)

if TYPE_CHECKING:
    pass


class BaseRepository(Generic[T]):
    """
    基础Repository，提供通用的CRUD操作.
    """

    _instance: ClassVar['BaseRepository | None'] = None

    def __init__(self, model_class: type[T]):
        """
        初始化Repository.

        Args:
            model_class: 模型类
        """
        self.model_class = model_class

    @classmethod
    def get_instance(cls) -> 'BaseRepository':
        """
        获取单例实例，如果不存在则创建.

        Returns:
            Repository实例
        """
        if cls._instance is None:
            # 注意：这里需要子类实现具体的创建逻辑
            # 因为基类无法知道应该传入什么 model_class
            raise NotImplementedError(
                "Subclasses must implement get_instance method"
            )
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例实例."""
        cls._instance = None

    def create(self, **kwargs: Any) -> T:
        """
        创建新记录.

        Args:
            **kwargs: 模型属性

        Returns:
            创建的模型实例
        """
        with self.get_session() as session:
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.flush()
            session.refresh(instance)
            return instance

    def update(self, id: int, **kwargs: Any) -> T | None:
        """
        更新记录.

        Args:
            id: 记录ID
            **kwargs: 要更新的属性

        Returns:
            更新后的模型实例或None
        """
        with self.get_session() as session:
            instance: T | None = session.execute(
                select(self.model_class).where(self.model_class.id == id)
            ).scalar_one_or_none()

            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                session.flush()
                session.refresh(instance)
                return instance
            return None

    def delete(self, id: int) -> bool:
        """
        删除记录.

        Args:
            id: 记录ID

        Returns:
            是否删除成功
        """
        with self.get_session() as session:
            instance = session.execute(
                select(self.model_class).where(self.model_class.id == id)
            ).scalar_one_or_none()

            if instance:
                session.delete(instance)
                return True
            return False

    def count(self) -> int:
        """
        统计记录数量.

        Returns:
            记录数量
        """
        with self.get_session() as session:

            result = session.execute(
                select(func.count()).select_from(self.model_class)
            ).scalar() or 0
            return result

    def get_session(self):
        """
        获取Session对象（用于复杂查询）.

        Returns:
            Session对象
        """
        return session_scope()

    @contextmanager
    def with_session(self) -> Generator[Any, None, None]:
        """
        提供事务范围，允许在同一个 session 中执行多个操作.

        Yields:
            Session: SQLAlchemy Session 实例
        """
        with self.get_session() as session:
            yield session
            # session_scope 会自动 commit 或 rollback
