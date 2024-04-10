from constants import (URI,QUEUE_CONSUMER)
import pika


try:
    parameters = pika.URLParameters(URI)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(
        queue=str(QUEUE_CONSUMER),
        durable=True,
        arguments={"x-queue-type": "classic"}
    )
    print(f"Quees creada: {QUEUE_CONSUMER}")

except Exception as error:
    print(f"Error en el proceso: {str(error)}")
