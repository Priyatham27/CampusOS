import motor.motor_asyncio
from redis import Redis
from apps.api.app.core.config import settings
from apps.api.app.core.logger import logger

class DatabaseManager:
    def __init__(self):
        self.client: motor.motor_asyncio.AsyncIOMotorClient = None
        self.db: motor.motor_asyncio.AsyncIOMotorDatabase = None
        self.redis_client = None

    def connect(self):
        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL.split('@')[-1]}...") # Obfuscate username/pwd
            self.client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
            # Retrieve database name from URL if present, otherwise default to campusos
            db_name = settings.MONGODB_URL.split("/")[-1].split("?")[0] or "campusos"
            self.db = self.client[db_name]
            logger.info(f"MongoDB connection initialized: '{db_name}'")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise e

        # Redis connection with mock fallback
        try:
            logger.info(f"Connecting to Redis at {settings.REDIS_URL}...")
            self.redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test ping
            self.redis_client.ping()
            logger.info("Redis connection established.")
        except Exception as e:
            logger.warning(f"Redis is unavailable: {e}. Falling back to In-Memory Cache.")
            self.redis_client = InMemoryCache()

    def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

class InMemoryCache:
    def __init__(self):
        self._store = {}

    def get(self, key: str):
        return self._store.get(key)

    def set(self, key: str, value: str, ex: int = None):
        self._store[key] = value

    def delete(self, key: str):
        self._store.pop(key, None)

    def ping(self):
        return True

db_manager = DatabaseManager()

# Dependency to get db session
def get_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    if db_manager.db is None:
        db_manager.connect()
    return db_manager.db

def get_redis():
    if db_manager.redis_client is None:
        db_manager.connect()
    return db_manager.redis_client
