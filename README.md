# MISW-4203-Backend-Mobile

# Paso 1

```bash 
# Levanta el proyecto
docker compose up -d
```

# Paso 2 
- Cargar la colección y las variables de entorno de postman


# Comandos útiles

```bash 
# Comando para eliminar contenedores, imágenes y volúmenes
docker-compose down -v --rmi all

# Liberar memoria si se bajarón los contenedores y sigue elevada pero borra todo
docker system prune -a --volumes

# Guia si windows se eleva la ram
https://medium.com/@ahmadsalahuddeen6017/how-to-resolve-high-ram-usage-by-vmmem-exe-when-running-docker-on-wsl-698c92018a9f

```

### Formato de json para probar manualmente el consumer
```json
    {
        "file_name": video_file.filename,
        "file_path": 'videos-uploaded/' + video_name,
        "user_id": current_user.id,
        "task_id": task.id,
        "video_id": video.id
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

### Lista de videos verticales
https://www.pexels.com/video/a-woman-busy-writing-on-a-paper-4778723/


