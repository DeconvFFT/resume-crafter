# Rust Backend Development

## Axum vs Actix-web

| Factor | Axum | Actix-web |
|--------|------|-----------|
| Throughput | ~6s (1M requests) | ~5.5s (fastest) |
| Tower middleware | Native | Incompatible |
| Learning curve | Gentler | Steeper, macro-heavy |

**Choose Axum** for new projects and Tower ecosystem. **Choose Actix-web** for maximum throughput.

## Axum Service Template

```rust
use axum::{
    routing::{get, post},
    Router, Json, extract::State,
    http::StatusCode,
};
use sqlx::PgPool;
use std::sync::Arc;
use tower::ServiceBuilder;
use tower_http::{
    trace::TraceLayer,
    timeout::TimeoutLayer,
    compression::CompressionLayer,
};
use std::time::Duration;

#[derive(Clone)]
struct AppState {
    db: PgPool,
}

async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({"status": "ok"}))
}

async fn list_users(
    State(state): State<Arc<AppState>>
) -> Result<Json<Vec<User>>, AppError> {
    let users = sqlx::query_as!(User, "SELECT * FROM users")
        .fetch_all(&state.db)
        .await?;
    Ok(Json(users))
}

#[tokio::main]
async fn main() {
    tracing_subscriber::init();
    
    let pool = sqlx::postgres::PgPoolOptions::new()
        .max_connections(10)
        .acquire_timeout(Duration::from_secs(5))
        .connect(&std::env::var("DATABASE_URL").unwrap())
        .await
        .unwrap();
    
    let state = Arc::new(AppState { db: pool });
    
    let app = Router::new()
        .route("/health", get(health))
        .route("/users", get(list_users))
        .with_state(state)
        .layer(ServiceBuilder::new()
            .layer(TraceLayer::new_for_http())
            .layer(TimeoutLayer::new(Duration::from_secs(10)))
            .layer(CompressionLayer::new()));
    
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await.unwrap();
    
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .unwrap();
}

async fn shutdown_signal() {
    tokio::signal::ctrl_c().await.unwrap();
    tracing::info!("Shutting down gracefully");
}
```

## SQLx Compile-Time Queries

```rust
use sqlx::FromRow;
use uuid::Uuid;

#[derive(FromRow, serde::Serialize)]
struct User {
    id: Uuid,
    email: String,
    name: String,
}

async fn get_user(pool: &PgPool, id: Uuid) -> Result<Option<User>, sqlx::Error> {
    sqlx::query_as!(
        User,
        r#"SELECT id, email, name FROM users WHERE id = $1"#,
        id
    )
    .fetch_optional(pool)
    .await
}
```

**CI without database**: Run `cargo sqlx prepare --workspace` for offline mode.

## Error Handling with thiserror

```rust
use thiserror::Error;
use axum::{
    response::{IntoResponse, Response},
    http::StatusCode,
    Json,
};

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Not found: {0}")]
    NotFound(String),
    
    #[error("Validation error: {0}")]
    Validation(String),
    
    #[error("Internal error")]
    Internal(#[from] anyhow::Error),
    
    #[error("Database error")]
    Database(#[from] sqlx::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, msg.clone()),
            AppError::Validation(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            AppError::Internal(e) => {
                tracing::error!("Internal error: {:?}", e);
                (StatusCode::INTERNAL_SERVER_ERROR, "Internal error".into())
            }
            AppError::Database(e) => {
                tracing::error!("Database error: {:?}", e);
                (StatusCode::INTERNAL_SERVER_ERROR, "Database error".into())
            }
        };
        (status, Json(serde_json::json!({"error": message}))).into_response()
    }
}
```

## Cargo.toml Dependencies

```toml
[dependencies]
axum = "0.7"
tokio = { version = "1", features = ["full"] }
tower = "0.4"
tower-http = { version = "0.5", features = ["trace", "timeout", "compression-gzip"] }
sqlx = { version = "0.7", features = ["runtime-tokio", "postgres", "uuid"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
thiserror = "1"
anyhow = "1"
uuid = { version = "1", features = ["v4", "serde"] }
```

## Project Structure

```
src/
├── main.rs
├── config.rs          # Environment config
├── error.rs           # AppError type
├── routes/
│   ├── mod.rs
│   ├── users.rs
│   └── health.rs
├── models/
│   └── user.rs
├── services/
│   └── user_service.rs
└── db/
    └── queries.rs
```

## Performance Tips

- Use `#[inline]` for hot-path functions
- Prefer `Arc<T>` over `Clone` for large state
- Use `tokio::spawn` for CPU-bound work
- Profile with `cargo flamegraph`
- Consider `mimalloc` or `jemalloc` allocators
