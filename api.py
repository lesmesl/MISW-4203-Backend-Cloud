import threading
import datetime
import logging
import jwt
import constants
import json
import ssl
import subprocess
import time
import pika

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import timedelta
from werkzeug.utils import secure_filename
from functools import wraps
from constants import (CIPHER_KEY, EXCHANGE_QUEUE, PREFETCH_COUNT,
                       SSL_CONNECTION, MAX_CONNECTION_RETRIES,
                       MAX_PUBLISH_RETRIES, QUEUE_PRODUCER,
                       RETRY_DELAY_CONNECTION,
                       RETRY_DELAY_PUBLISH, URI, ROUTING_KEY)


logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


app = Flask(__name__)

# Postgresql connection
db_uri = f"postgresql://{constants.POSTGRESQL_USER}:{constants.POSTGRESQL_PASSWORD}@{constants.POSTGRESQL_HOST}:{constants.POSTGRESQL_PORT}/{constants.POSTGRESQL_DB}"
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app_context = app.app_context()
app_context.push()
db = SQLAlchemy(app)
# Setting CORS
CORS(
    app,
    origins="*",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# Setting JWT
app.config['JWT_SECRET_KEY'] = "super-secret"


'''
Shared section
'''


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return jsonify({
                "message": "token inválido",
                "data": None,
                "error": "Unauthorized"
            }), 401

        if token == "null" or token == "undefined" or token == "NaN" or token == "false" or token == "true" or token == "0" or token == "1" or token == "":
            return jsonify({
                               "message": "token inválido",
                                "data": None,
                                "error": "Unauthorized"
            }), 401

        try:
            data = jwt.decode(token, app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data["user_id"]).first()
            if current_user is None:
                return jsonify({
                    "message": "token inválido",
                    "data": None,
                    "error": "Unauthorized"
                }), 401
        except Exception as e:
            return jsonify({
                "message": "algo falló",
                "data": None,
                "error": str(e)
            }), 500

        return f(current_user, *args, **kwargs)

    return decorated


'''
Health check section
'''


@app.route('/', methods=['GET'])
def index():
    return 'IDRL service is up and running!'


@app.route('/ping', methods=['GET'])
def ping():
    return 'ok'


'''
Users section
'''


# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    password = db.Column(db.String(50))
    user = db.Column(db.String(50))
    email = db.Column(db.String(100))


# To create a user
@app.route('/users', methods=['POST'])
def create_user():
    new_user = User(
        name=request.json['name'],
        email=request.json['email'],
        user=request.json['user'],
        password=request.json['password'],
    )

    db.session.add(new_user)
    db.session.commit()
    return jsonify(
        {"message": "usuario creado", "user": {"id": new_user.id, "name": new_user.name, "email": new_user.email}})


@app.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(user=request.json['user'], password=request.json['password']).first()
    if user:
        expire = timedelta(minutes=30)

        access_token = jwt.encode(
            {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "exp": datetime.datetime.utcnow() + expire,
                "iat": datetime.datetime.utcnow(),
                "nbf": datetime.datetime.utcnow()
            },
            "super-secret",
            algorithm="HS256"
        )

        if not isinstance(access_token, str):
            access_token = access_token.decode('utf-8')

        return jsonify({"message": "usuario autenticado", "token": access_token})
    else:
        return jsonify({"message": "usuario o contraseña incorrecta"}), 401


'''
Video section
'''

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}  # File extensions allowed


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500))
    path = db.Column(db.String(500))
    image = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Integer)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500))
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    status = db.Column(db.String(500))


# To upload a video
@app.route('/video', methods=['POST'])
@token_required
def upload_video(current_user):
    if 'video' not in request.files:
        return jsonify({"error": "no se proporcionó ningún archivo de video"}), 400

    video_file = request.files['video']
    video_name = ''

    if video_file.filename == '':
        return jsonify({"error": "el nombre del archivo está vacío"}), 400

    if video_file and allowed_file(video_file.filename):
        now = datetime.datetime.now()
        user_id = current_user.id
        video_name = f'{now.strftime("%Y%m%d%H%M%S")}-{user_id}-{video_file.filename}'
        video_file.save('videos-uploaded/' + secure_filename(f'{now.strftime("%Y%m%d%H%M%S")}-{user_id}-{video_file.filename}'))
    else:
        return jsonify({"error": "formato de archivo no permitido"}), 400

    video = Video(
        name=video_file.filename,
        path='videos-uploaded/' + secure_filename(video_name),
        user_id=current_user.id,
        rating=0
    )
    db.session.add(video)
    db.session.commit()

    task = Task(
        name=video_name,
        video_id=video.id,
        status="pending"
    )
    db.session.add(task)
    db.session.commit()

    # Establecer conexión con RabbitMQ
    start_channel, start_connection = RabbitConnection.start_connection()

    # publicar mensaje
    publisher = RabbitPublisher(start_channel, start_connection)

    publisher.publish_message(
        {
            "file_name": video_file.filename,
            "file_path": 'videos-uploaded/' + video_name,
            "user_id": current_user.id,
            "task_id": task.id,
            "video_id": video.id
        }
    )

    return jsonify({"message": "video subido exitosamente"}), 200


@app.route('/videos', methods=['GET'])
def get_videos():
    videos = Video.query.all()
    return jsonify([{"id": video.id, "name": video.name, "image": video.image, "path": video.path, "user_id": video.user_id, "rating": video.rating} for video in videos])


@app.route('/videos/top', methods=['GET'])
def get_top_videos():
    # Obtener los videos con mayor rating incluyendo el usuario que lo subió
    videos = db.session.query(Video, User).join(User).order_by(Video.rating.desc()).all()
    return jsonify([{"id": video.id, "name": video.name, "image": video.image, "path": video.path, "user_id": video.user_id, "rating": video.rating, "user": {"id": user.id, "name": user.name, "email": user.email}} for video, user in videos])


@app.route('/videos/<int:video_id>/vote', methods=['POST'])
def vote_video(video_id):
    video = Video.query.get(video_id)
    if video is None:
        return jsonify({"message": "video no encontrado"}), 404

    if video.rating is None:
        video.rating = 0

    video.rating += 1
    db.session.commit()
    return jsonify({"message": "voto registrado exitosamente"}), 200

def run_consumer():
    try:
        # Establecer conexión con RabbitMQ
        start_channel, start_connection = RabbitConnection.start_connection()
        consumer = RabbitConsumer(start_channel, start_connection)
        consumer.consume_queue()
    except Exception as e:
        logger.error(
            f"Ocurrió un error durante el consumo de mensajes: {str(e)}")
        raise e


# Inicializar Flask-Migrate
db.create_all()
migrate = Migrate(app, db)


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


        try:

            # configuración del consumer
            self.channel.basic_qos(prefetch_count=PREFETCH_COUNT)
            self.channel.queue_declare(
                QUEUE_PRODUCER, durable=True)
            # Consumir mensajes de RabbitMQ
            self.channel.basic_consume(
                queue=QUEUE_PRODUCER, on_message_callback=self.process_message_callback)
            logger.info(
                f'Iniciado con éxito el consumo de mensajes de la cola {QUEUE_PRODUCER}...')
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
        logger.info(f'Mensaje: {message_consumer}')

        try:
            task_id = message_consumer["task_id"]
            video_id = message_consumer["video_id"]
            logger.info(f"Procesando el mensaje: {task_id}")
            logger.info(f"Procesando el mensaje: {video_id}")
            task = Task.query.get(task_id)
            video = Video.query.get(video_id)

            if task and video:
                # Procesar el video
                # Ruta del archivo de logo
                logo_path = "ruta/a/tus/logo.webp"

                # Directorio de entrada y salida
                input_dir = "ruta/a/tus/videos/originales"
                output_dir = "ruta/a/tus/videos/procesados"

                file = video.path
                filename = video.name
                extension = filename.split(".")[-1]
                filename_without_extension = filename[:-(len(extension) + 1)]

                # Nombre del archivo de salida
                output_filename = f"{output_dir}/{filename_without_extension}_procesado.{extension}"

                # Comando FFmpeg para procesar el video
                cmd = [
                    "ffmpeg", "-ignore_unknown", "-i", file,
                    "-loop", "1", "-t", "3", "-i", logo_path,
                    "-filter_complex",
                    f"[1:v]fade=out:st=2:d=1:alpha=1,setpts=PTS-STARTPTS[logo];"
                    f"[0:v][logo]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:format=auto,"
                    f"scale=trunc(oh*a/2)*2:360,crop=360:360,pad=640:360:(ow-iw)/2:(oh-ih)/2,"
                    f"trim=duration=20,setpts=PTS-STARTPTS[v]",
                    "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-c:a", "copy", "-t", "20", "-y", output_filename
                ]

                subprocess.run(cmd, check=True)

                # Actualizar estado de la tarea
                task.status = "completado"
                db.session.commit()

                logger.info(f"Video procesado: {output_filename}")
            else:
                logger.warning("No se pudo encontrar la tarea o el video asociado al mensaje.")

        except Exception as e:
            logger.error(f"Error al procesar el mensaje: {e}")

        # Verificar el estado del canal antes de realizar la confirmación (ack)
        if ch.is_open:
            # Confirmar el procesamiento del mensaje
            logger.info(f'Se inicia el retiro del mensaje del ack {method.delivery_tag}')
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            logger.warning("El canal de RabbitMQ está cerrado. No se puede realizar la confirmación para publicar (ack).")


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

if __name__ == '__main__':
   # Crear un hilo para el consumidor
    consumer_thread = threading.Thread(target=run_consumer)
    consumer_thread.start()

    # Iniciar la aplicación Flask en el hilo principal
    app.run(debug=True, host='0.0.0.0', port=5050)