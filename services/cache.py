from redis.asyncio import Redis
from config import Config, load_config


class RedisCache:
    """Создаёт и хранит Redis-клиент для кеша и FSM."""

    def __init__(self, db: int):
        """Инициализирует подключение к указанной Redis-базе."""
        # Клиент Redis для хранения FSM/кеша
        self.cfg: Config = load_config()
        self.db = db
        self.redis = Redis(
            host=self.cfg.redis.host,
            port=self.cfg.redis.port,
            decode_responses=True,
            db=self.db
        )

    def get_redis(self):
        """Возвращает готовый экземпляр Redis-клиента."""
        # Возвращает готовый redis-клиент
        return self.redis
