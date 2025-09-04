from abc import ABC, abstractmethod


class BaseMigrationManager(ABC):
    """
    数据库迁移管理器的抽象基类。
    定义了所有具体迁移管理器必须实现的接口。
    """

    @abstractmethod
    async def run_migrations(self):
        """
        运行所有必要的数据库迁移。
        """
        pass

    @abstractmethod
    async def get_db_version(self) -> int:
        """
        获取数据库的当前版本号。
        """
        pass

    @abstractmethod
    async def set_db_version(self, version: int):
        """
        设置数据库的版本号。
        """
        pass
