# MISW-4203-Backend-Mobile

# Paso 1

```bash 
# Levanta el proyecto
docker compose up -d
```

# Paso 2 
- Cargar la colección y las variables de entorno de postman


```
```bash 
# ejecutar esté comando dentro del contenedor
python create_queue_producer.py
```

# Comandos útiles

```bash 
# Comando para eliminar contenedores, imágenes y volúmenes
docker-compose down -v --rmi all
```


### Formato de json para el consumer
```json
{
    "id_event":1,
    "file_name": "test.pdf",
    "file_path": "/home/user/test.pdf",
    "user_id": 1
}
```
### Archivo .env
```json
SSL_CONNECTION=0
URI='amqp://admin:admin@localhost:5672'
CIPHER_KEY='ECDHE+AESGCM:!ECDSA'

PREFETCH_COUNT=1
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
