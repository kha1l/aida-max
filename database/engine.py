from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import Config, load_config

cfg: Config = load_config()

# Асинхронный движок SQLAlchemy для PostgreSQL.
# pool_pre_ping помогает не отдавать в работу протухшие соединения из пула,
# а pool_recycle снижает шанс упереться в server-side idle timeout.
engine = create_async_engine(
    f'postgresql+asyncpg://'
    f'{cfg.dbase.user}:'
    f'{cfg.dbase.password}@'
    f'{cfg.dbase.host}:'
    f'5432/'
    f'{cfg.dbase.name}',
    pool_pre_ping=True,
    pool_recycle=1800,
)


# Фабрика сессий для работы с БД
session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
