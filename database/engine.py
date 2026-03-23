from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import Config, load_config

cfg: Config = load_config()

# Асинхронный движок SQLAlchemy для PostgreSQL
engine = create_async_engine(f'postgresql+asyncpg://'
                             f'{cfg.dbase.user}:'
                             f'{cfg.dbase.password}@'
                             f'{cfg.dbase.host}:'
                             f'5432/'
                             f'{cfg.dbase.name}')


# Фабрика сессий для работы с БД
session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
