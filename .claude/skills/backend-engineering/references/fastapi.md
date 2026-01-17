# FastAPI Patterns

## Async Database Access (SQLAlchemy 2.0)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=20,          # Base connections per worker
    max_overflow=10,       # Burst capacity
    pool_pre_ping=True,    # Detect stale connections
    pool_recycle=1800      # Refresh every 30 minutes
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Pool sizing formula**: `pool_size = 10-25` for app servers, `max_overflow = 5-10` for burst.

## Dependency Injection

```python
from typing import Annotated
from fastapi import Depends

DBSession = Annotated[AsyncSession, Depends(get_db_session)]

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user(self, user_id: int) -> User:
        return await self.db.get(User, user_id)

async def get_user_service(db: DBSession) -> UserService:
    return UserService(db)

@router.get("/users/{user_id}")
async def get_user(
    user_id: int, 
    service: Annotated[UserService, Depends(get_user_service)]
):
    return await service.get_user(user_id)
```

## Background Tasks

| Approach | Use Case | Notes |
|----------|----------|-------|
| `BackgroundTasks` | Fire-and-forget, <100ms | No retries, lost on restart |
| Celery | Heavy processing, distributed | Sync workers, setup complexity |
| ARQ | Async-native queues | Smaller ecosystem |

### Celery with Retries
```python
@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def process_order(self, order_id: int):
    try:
        execute_order_processing(order_id)
    except TransientError as exc:
        self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

## Project Structure

Organize by domain, not file type:

```
src/
├── auth/
│   ├── router.py      # API endpoints
│   ├── schemas.py     # Pydantic models
│   ├── models.py      # SQLAlchemy models
│   ├── service.py     # Business logic
│   └── repository.py  # Data access
├── orders/
│   └── ...
├── core/
│   ├── config.py      # pydantic-settings
│   ├── database.py    # Connection setup
│   └── security.py    # Auth utilities
└── main.py
```

## Testing with pytest-asyncio

```python
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def async_client(db_session):
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_user(async_client):
    response = await async_client.post(
        "/users", json={"email": "test@example.com"}
    )
    assert response.status_code == 201
```

## Error Handling

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )
```

## Performance Tips

1. Use `orjson` for faster JSON serialization
2. Enable response compression with `GZipMiddleware`
3. Use connection pooling for all external services
4. Profile with `py-spy` for hot spots
5. Consider `uvloop` for event loop performance
