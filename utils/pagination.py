"""分页工具类."""
from typing import Any


class Pagination:
    """分页结果类."""

    def __init__(
        self,
        items: list[Any],
        total: int,
        page: int,
        per_page: int
    ):
        """
        初始化分页.

        Args:
            items: 当前页数据
            total: 总记录数
            page: 当前页码
            per_page: 每页数量
        """
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.pages = (total + per_page - 1) // per_page

    @property
    def has_prev(self) -> bool:
        """是否有上一页."""
        return self.page > 1

    @property
    def has_next(self) -> bool:
        """是否有下一页."""
        return self.page < self.pages

    @property
    def prev_num(self) -> int | None:
        """上一页页码."""
        return self.page - 1 if self.has_prev else None

    @property
    def next_num(self) -> int | None:
        """下一页页码."""
        return self.page + 1 if self.has_next else None

    def iter_pages(
        self,
        left_edge: int = 2,
        left_current: int = 2,
        right_current: int = 3,
        right_edge: int = 2
    ):
        """
        生成页码迭代器.

        Args:
            left_edge: 左侧边缘页数
            left_current: 当前页左侧页数
            right_current: 当前页右侧页数
            right_edge: 右侧边缘页数

        Yields:
            页码或None（表示省略号）
        """
        last = 0
        for num in range(1, self.pages + 1):
            is_center = (
                self.page - left_current - 1 <
                num <
                self.page + right_current
            )
            if (
                num <= left_edge or
                is_center or
                num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num
        if last != self.pages:
            yield None


def paginate_results(
    items: list[Any],
    total: int,
    page: int,
    per_page: int
) -> Pagination:
    """
    分页结果.

    Args:
        items: 当前页数据
        total: 总记录数
        page: 当前页码
        per_page: 每页数量

    Returns:
        分页对象
    """
    return Pagination(items, total, page, per_page)
