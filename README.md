# MISW-4203-Backend-Mobile

## ejecutar el api
```bash
docker-compose up -d
```

## formato de json para el consumer
```json
{
    "id_event":1,
    "file_name": "test.pdf",
    "file_path": "/home/user/test.pdf",
    "user_id": 1
}
```
## Archivo .env
```json
SSL_CONNECTION=0
URI='amqp://admin:admin@localhost:5672'
CIPHER_KEY='ECDHE+AESGCM:!ECDSA'

PREFETCH_COUNT=1
CONSUME_QUEUE=videoQueue
PRODUCER_QUEUE=videoPublishQueue
EXCHANGE_QUEUE=videoExchange
ROUTING_KEY=videoKey

MAX_CONSUMER_RETRIES = 2
RETRY_DELEY_CONSUMER = 5
MAX_CONNECTION_RETRIES = 2
RETRY_DELAY_CONNECTION = 1
MAX_PUBLISH_RETRIES = 2
RETRY_DELAY_PUBLISH = 1
```

## Comando para eliminar contenedores, imágenes y volúmenes
```bash 
docker-compose down -v --rmi all
```