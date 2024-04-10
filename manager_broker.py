import json
import logging
import ssl
import time

import pika
from constants import (CIPHER_KEY, EXCHANGE_QUEUE, PREFETCH_COUNT,
                       SSL_CONNECTION, MAX_CONNECTION_RETRIES,
                       MAX_PUBLISH_RETRIES, QUEUE_CONSUMER,
                       RETRY_DELAY_CONNECTION,
                       RETRY_DELAY_PUBLISH, URI, ROUTING_KEY)

logging.basicConfig(level=logging.INFO)

# Configuración de registro para RabbitMQ
logging.getLogger("pika").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class RabbitConnection:
    """
    Clase para establecer una conexión con RabbitMQ.
    """

    @classmethod
    def start_connection(cls):
        """
        Establece la conexión con RabbitMQ y devuelve el canal y la conexión.

        Returns:
            pika.channel.Channel: Canal de comunicación con RabbitMQ.
            pika.BlockingConnection: Conexión con RabbitMQ.
        """
        # Configuración de RabbitMQ
        parameters = pika.URLParameters(URI)

        if SSL_CONNECTION:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ssl_context.set_ciphers(CIPHER_KEY)
            parameters.ssl_options = pika.SSLOptions(context=ssl_context)
            logger.info("SSL de RabbitMQ instalado")

        retries = 0
        connected = False
        connection = None
        channel = None

        while not connected and retries < MAX_CONNECTION_RETRIES:
            try:
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                connected = True
            except (pika.exceptions.ChannelWrongStateError, pika.exceptions.AMQPConnectionError, pika.exceptions.AMQPChannelError):
                logger.error("Error de conexión RabbitMQ")

            except Exception as error:
                logger.error(f'Error desconocido {str(error)}')

            if not connected:
                retries += 1
                time.sleep(RETRY_DELAY_CONNECTION)
                logger.warning(
                    f"realizando reintento de rabbitmq #{retries} de {MAX_CONNECTION_RETRIES}")

        if not connected:
            logger.error(
                f"No se pudo establecer conexión con RabbitMQ después de {MAX_CONNECTION_RETRIES} intentos")
            raise pika.exceptions.AMQPConnectionError(
                "No se pudo establecer la conexión con RabbitMQ después de varios intentos.")

        return channel, connection


class RabbitConsumer:
    """
    Clase para consumir mensajes de RabbitMQ.
    """

    def __init__(self, channel, connection):
        self.channel = channel
        self.connection = connection

    def consume_queue(self):
        """
        Consume mensajes de la cola de RabbitMQ y los procesa.
        """
        logger.info('Iniciando el consumo de mensajes...')

        while True:
            try:

                # configuración del consumer
                self.channel.basic_qos(prefetch_count=PREFETCH_COUNT)
                self.channel.queue_declare(
                    QUEUE_CONSUMER, durable=True)
                # Consumir mensajes de RabbitMQ
                self.channel.basic_consume(
                    queue=QUEUE_CONSUMER, on_message_callback=self.process_message_callback)
                logger.info(
                    f'Iniciado con éxito el consumo de mensajes de la cola {QUEUE_CONSUMER}...')
                self.channel.start_consuming()
            
            except (pika.exceptions.ChannelWrongStateError, pika.exceptions.AMQPConnectionError, pika.exceptions.AMQPChannelError):
                logger.error(
                    'Se perdió la conexión con RabbitMQ. Restableciendo la conexión...')
                reconnected_channel, reconnected_connection = RabbitConnection.start_connection()
                self.channel = reconnected_channel
                self.connection = reconnected_connection

            except Exception as error:
                logger.error(f"Error al consumir mensajes: {str(error)}")
                raise Exception(str(error))

    def process_message_callback(self, ch, method, properties, body):
        """
        Procesa un mensaje de RabbitMQ.

        Args:
            ch (pika.channel.Channel): Canal de RabbitMQ.
            method (pika.spec.Basic.Deliver): Método de RabbitMQ.
            properties (pika.spec.BasicProperties): Propiedades del mensaje.
            body (bytes): Cuerpo del mensaje.
        """

        message_consumer = json.loads(body.decode())

        message_id = message_consumer['id_event']
        logger.info(f'Mensaje consumido con el ID: {message_id}')

        logger.info(f'Procesando mensaje: {message_id}')
        logger.info(f'Mensaje: {message_consumer}')

        # Publica el mensaje en RabbitMQ
        publisher = RabbitPublisher(self.channel, self.connection)
        publisher.publish_message(
            {'message': 'Hola mundo'})


        # Verificar el estado del canal antes de realizar la confirmación (ack)
        if ch.is_open:
            # Confirmar el procesamiento del mensaje
            logger.info(
                f'se inicia el retiro el mensaje del ack: {message_id}')
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            logger.warning(
                "El canal de RabbitMQ está cerrado. No se puede realizar la confirmación para publicar (ack).")


class RabbitPublisher:
    """
    Clase para publicar mensajes en RabbitMQ.
    """

    def __init__(self, channel, connection):
        self.channel = channel
        self.connection = connection

    def publish_message(self, message):
        """
        Publica un mensaje en la cola de RabbitMQ.

        Args:
            message (dict): Mensaje a publicar.
        """
        message_json = json.dumps(message)
        retries = 0
        published = False

        while not published and retries < MAX_PUBLISH_RETRIES:
            try:
                self.channel.basic_publish(
                    exchange=EXCHANGE_QUEUE, routing_key=ROUTING_KEY, body=message_json)
                published = True
                logger.info('Mensaje publicado en RabbitMQ')
            except (pika.exceptions.ChannelWrongStateError, pika.exceptions.ConnectionClosed, pika.exceptions.StreamLostError) as error_exception:

                logger.error(
                    f"Error al publicar el mensaje: {str(error_exception)}")
                time.sleep(RETRY_DELAY_PUBLISH)

                # Intentar restablecer la conexión con RabbitMQ
                try:
                    self.channel, self.connection = RabbitConnection.start_connection()
                    logger.info(
                        'Conexión con RabbitMQ recuperada para publicar el mensaje')

                except Exception as e:
                    retries += 1
                    logger.error(
                        f"Intento de publicar el mensaje de RabbitMQ: #{retries} de {MAX_PUBLISH_RETRIES}")
                    logger.error(
                        'No se pudo restablecer la conexión con RabbitMQ')
            except Exception as e:
                logger.error(f"Error al publicar el mensaje: {str(e)}")
                break

def run():

    try:
        # Inicializar variables
        start_connection = None

        # Establecer conexión con RabbitMQ
        start_channel, start_connection = RabbitConnection.start_connection()


        # Crear instancia de RabbitConsumer y consumir la cola
        consumer = RabbitConsumer(
            start_channel, start_connection)
        consumer.consume_queue()

    except Exception as e:
        logger.error(
            f"Ocurrió un error durante el consumo de mensajes: {str(e)}")
        raise e  # elevar la excepción
    finally:
        # Verificar el estado del canal antes de realizar la confirmación (ack)
        if start_connection is not None and start_connection.is_open:
            logger.warning("Se cerrara la conexión de RabbitMQ")
            start_connection.close()


if __name__ == "__main__":
    run()
