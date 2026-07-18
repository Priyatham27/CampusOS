import asyncio
from app.main import db_manager
from app.models.org_engine import ORG_ENGINE_MODELS
from app.models.identity import IDENTITY_MODELS
from app.models.catalog import CATALOG_MODELS
from beanie import init_beanie

async def run():
    print('Connecting...')
    db_manager.connect()
    print('Init Beanie...')
    try:
        await init_beanie(database=db_manager.db, document_models=ORG_ENGINE_MODELS + IDENTITY_MODELS + CATALOG_MODELS)
        print('Done!')
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(run())
