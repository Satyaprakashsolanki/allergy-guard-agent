#!/bin/bash
set -e

echo "=== AllergyGuard Backend Startup ==="

# Wait for database to be ready (extra safety beyond healthcheck)
echo "Waiting for database connection..."
python -c "
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

async def wait_for_db():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('DATABASE_URL not set!')
        sys.exit(1)

    engine = create_async_engine(db_url)
    max_retries = 30
    retry_interval = 2

    for i in range(max_retries):
        try:
            async with engine.connect() as conn:
                await conn.execute(text('SELECT 1'))
                print(f'Database connection successful!')
                return
        except Exception as e:
            print(f'Waiting for database... (attempt {i+1}/{max_retries})')
            await asyncio.sleep(retry_interval)

    print('Could not connect to database after maximum retries')
    sys.exit(1)

asyncio.run(wait_for_db())
"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Migrations complete!"

# Start the application
echo "Starting FastAPI application..."
exec "$@"
