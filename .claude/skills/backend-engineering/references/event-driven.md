# Event-Driven Architecture

## Technology Selection

| Technology | Best For | Ordering | Durability |
|------------|----------|----------|------------|
| Kafka | High throughput, event sourcing | Per-partition | Persistent |
| RabbitMQ | Complex routing, RPC patterns | Per-queue | Persistent |
| Redis Streams | Real-time, lightweight | Per-stream | Configurable |
| Redis Pub/Sub | Fire-and-forget notifications | None | None |
| AWS SQS | AWS-native, simple queuing | FIFO optional | Persistent |

## Kafka Patterns

### Producer with Exactly-Once Semantics
```python
from confluent_kafka import Producer

producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'enable.idempotence': True,
    'acks': 'all',
    'transactional.id': 'my-producer-1',
    'compression.type': 'lz4',
    'batch.size': 32768,
    'linger.ms': 10
})

producer.init_transactions()
try:
    producer.begin_transaction()
    producer.produce(
        'orders',
        key='order-123',
        value=order_json,
        callback=delivery_callback
    )
    producer.commit_transaction()
except Exception:
    producer.abort_transaction()
    raise
```

### Consumer with Manual Commits
```python
from confluent_kafka import Consumer

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'order-processors',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
    'isolation.level': 'read_committed'
})

consumer.subscribe(['orders'])

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        handle_error(msg.error())
        continue
    
    try:
        process_message(msg)
        consumer.commit(asynchronous=False)
    except ProcessingError:
        send_to_dlq(msg)
        consumer.commit()
```

### Async Kafka with aiokafka
```python
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

async def consume():
    consumer = AIOKafkaConsumer(
        'orders',
        bootstrap_servers='localhost:9092',
        group_id='processors',
        enable_auto_commit=False
    )
    await consumer.start()
    try:
        async for msg in consumer:
            await process_message(msg)
            await consumer.commit()
    finally:
        await consumer.stop()
```

## RabbitMQ Patterns

### Topic Exchange with Pattern Routing
```python
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost')
)
channel = connection.channel()

# Declare topic exchange
channel.exchange_declare(
    exchange='events',
    exchange_type='topic',
    durable=True
)

# Publisher with confirms
channel.confirm_delivery()
channel.basic_publish(
    exchange='events',
    routing_key='order.created.premium',
    body=message,
    properties=pika.BasicProperties(
        delivery_mode=2,  # Persistent
        content_type='application/json'
    ),
    mandatory=True
)

# Consumer with pattern subscription
channel.queue_declare(queue='premium-handler', durable=True)
channel.queue_bind(
    exchange='events',
    queue='premium-handler',
    routing_key='*.*.premium'
)
channel.basic_qos(prefetch_count=10)
channel.basic_consume(
    queue='premium-handler',
    on_message_callback=process_message
)
```

### Dead Letter Queue Setup
```python
# Main queue with DLQ
channel.queue_declare(
    queue='orders',
    durable=True,
    arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'orders.dlq',
        'x-message-ttl': 86400000  # 24 hours
    }
)

# DLQ
channel.exchange_declare(exchange='dlx', exchange_type='direct')
channel.queue_declare(queue='orders.dlq', durable=True)
channel.queue_bind(exchange='dlx', queue='orders.dlq', routing_key='orders.dlq')
```

## Redis Streams

### Producer
```python
import redis.asyncio as redis

r = redis.Redis()

# Add to stream
await r.xadd(
    'orders-stream',
    {'order_id': '123', 'status': 'created', 'amount': '99.99'}
)
```

### Consumer Group
```python
# Create consumer group
await r.xgroup_create(
    'orders-stream',
    'processors',
    id='0',
    mkstream=True
)

# Consume with acknowledgment
while True:
    messages = await r.xreadgroup(
        groupname='processors',
        consumername='worker-1',
        streams={'orders-stream': '>'},
        count=10,
        block=5000
    )
    
    for stream, entries in messages:
        for entry_id, data in entries:
            try:
                await process_order(data)
                await r.xack('orders-stream', 'processors', entry_id)
            except Exception:
                # Will be redelivered after timeout
                pass
```

### Claim Pending Messages
```python
# Claim messages stuck > 60s
pending = await r.xpending_range(
    'orders-stream', 'processors',
    min='-', max='+', count=100
)

for msg in pending:
    if msg['time_since_delivered'] > 60000:
        await r.xclaim(
            'orders-stream', 'processors', 'worker-1',
            min_idle_time=60000,
            message_ids=[msg['message_id']]
        )
```

## Transactional Outbox Pattern

Solve dual-write problem (database + broker) atomically:

```python
from sqlalchemy.ext.asyncio import AsyncSession

class OutboxEvent(Base):
    __tablename__ = 'outbox_events'
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    aggregate_type = Column(String, nullable=False)
    aggregate_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

async def create_order(session: AsyncSession, order_data: dict):
    async with session.begin():
        order = Order(**order_data)
        session.add(order)
        
        # Outbox event in same transaction
        outbox_event = OutboxEvent(
            aggregate_type='Order',
            aggregate_id=str(order.id),
            event_type='OrderCreated',
            payload=order.to_dict()
        )
        session.add(outbox_event)

# Relay process (or use Debezium CDC)
async def relay_outbox_events():
    async with async_session() as session:
        events = await session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .limit(100)
        )
        for event in events.scalars():
            await publish_to_kafka(event)
            event.published_at = datetime.utcnow()
        await session.commit()
```

## S3 Event Notifications

```python
# Lambda handler for S3 events
def handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        event_type = record['eventName']
        
        if event_type.startswith('ObjectCreated'):
            process_new_file(bucket, key)
```

## Event Schema Registry

Use Avro or Protobuf with schema registry for contract enforcement:

```python
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

schema_registry = SchemaRegistryClient({'url': 'http://localhost:8081'})

order_schema = """
{
    "type": "record",
    "name": "Order",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "created_at", "type": "long", "logicalType": "timestamp-millis"}
    ]
}
"""

serializer = AvroSerializer(schema_registry, order_schema)
```
