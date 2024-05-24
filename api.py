import subprocess
import os
import datetime
import logging
import jwt
import json
import subprocess
import pg8000
import sqlalchemy
import constants
from google.cloud import pubsub_v1
from constants import POSTGRESQL_DB, POSTGRESQL_USER, POSTGRESQL_PASSWORD,POSTGRESQL_HOST
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import timedelta
from werkzeug.utils import secure_filename
from functools import wraps
from flask import send_file
from google.oauth2 import service_account
from google.cloud import storage
from sqlalchemy.orm import sessionmaker
from google.cloud import pubsub_v1
from google.oauth2 import service_account
from sqlalchemy import create_engine
from google.auth import default

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)



def connect_unix_socket():
    """Initializes a Unix socket connection pool for a Cloud SQL instance of Postgres."""
    db_host = POSTGRESQL_HOST  
    db_user = POSTGRESQL_USER
    db_pass = POSTGRESQL_PASSWORD
    db_name = POSTGRESQL_DB
    db_port = 5432

    pool = create_engine(
        # Equivalent URL:
        # postgresql+pg8000://<db_user>:<db_pass>@<db_host>:<db_port>/<db_name>
        sqlalchemy.engine.url.URL.create(
            drivername="postgresql+pg8000",
            username=db_user,
            password=db_pass,
            host=db_host,
            port=db_port,
            database=db_name,
        ),
    )
    return pool

engine = connect_unix_socket()

# clase SessionLocal para manejar las sesiones de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = Flask(__name__)

# Postgresql connection
app.config['SQLALCHEMY_DATABASE_URI'] = get_db()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app_context = app.app_context()
app_context.push()
app.config['SQLALCHEMY_POOL_SIZE'] = 30
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 30
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20
app.config['SQLALCHEMY_POOL_RECYCLE'] = 10
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

def validate_audio(path_video):
    try:
        logger.info(f"Validando si el video cuenta con audio: {path_video}")
        command_get_info_video = f"ffmpeg -i {path_video}"
        logger.info(f"Comando de validación de audio: {command_get_info_video}")
        start_command_get_info = subprocess.run(command_get_info_video, shell=True, capture_output=True, text=True)        

        has_audio = "Stream #0:1" in start_command_get_info.stderr

        if has_audio:
            logger.info("El video tiene audio.")
            return True
        
        logger.info("El video NO cuenta con audio")
        return False
    except Exception as e:
        logger.error(f"Error al validar el audio detalle: {str(e)}")
        return False


def edit_video(input_file, logo, output_file,filename):
    
    MAXTIMEVIDEO = 18
    NAMEVIDEOIMAGE = f"imagen_temp_{filename}"
    VIDEO_CUTOUT = f"recortado_{filename}"
    VIDEO_SCALE = f"escalado_{filename}"
    SCALE = "1280:720"

    try:

        # Comando para convertir la imagen en video
        command_image_video = f'ffmpeg -y -loop 1 -i {logo} -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 -t 1 -c:v libx264 -pix_fmt yuv420p -vf "scale=1280:720" -c:a aac -shortest {NAMEVIDEOIMAGE}'
        logger.info(f"Comando de imagen: {command_image_video}")

        status_command_image_video = subprocess.run(command_image_video, shell=True, capture_output=True, text=True)   
        if status_command_image_video.returncode != 0:
            logger.error(f"Error al ejecutar el comando de imagen: {status_command_image_video.stderr}")
            raise Exception(f"Error al ejecutar el comando de imagen: {status_command_image_video.stderr}")
        
        # Comando para recortar el video y copiar el audio
        command_video_cutout = f'ffmpeg -y -i {input_file} -ss 0 -t {MAXTIMEVIDEO} -c:v copy -c:a copy {VIDEO_CUTOUT}'
        logger.info(f"Comando de recordado: {command_video_cutout}")

        status_command_video_cutout = subprocess.run(command_video_cutout, shell=True, capture_output=True, text=True)
        if status_command_video_cutout.returncode != 0:
            logger.error(f"Error al ejecutar el comando de recorte: {status_command_video_cutout.stderr}")
            raise Exception(f"Error al ejecutar el comando de recorte: {status_command_video_cutout.stderr}")
        
        # Comando para escalar el video
        command_video_scale = f'ffmpeg -y -i {VIDEO_CUTOUT} -vf scale={SCALE} {VIDEO_SCALE}'
        logger.info(f"Comando de escalado: {command_video_scale}")

        status_command_video_scale = subprocess.run(command_video_scale, shell=True, capture_output=True, text=True)
        if status_command_video_scale.returncode != 0:
            logger.error(f"Error al ejecutar el comando de escalado: {status_command_video_scale.stderr}")
            raise Exception(f"Error al ejecutar el comando de escalado: {status_command_video_scale.stderr}")
        
                
        # validamos si el VIDEO_SCALE cuenta con audio
        if validate_audio(VIDEO_SCALE):
            command_video_join = f'ffmpeg -y -i {NAMEVIDEOIMAGE} -i {VIDEO_SCALE} -i {NAMEVIDEOIMAGE} -filter_complex "[0:v][0:a][1:v][1:a][2:v]concat=n=3:v=1:a=1[v]" -map "[v]" -preset ultrafast -strict -2 {output_file}'
        else:
            command_video_join = f'ffmpeg -y -i {NAMEVIDEOIMAGE} -i {VIDEO_SCALE} -i {NAMEVIDEOIMAGE} -filter_complex "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]" -map "[v]" -preset ultrafast -strict -2 {output_file}'
        
        # Comando para escalar el video
        logger.info(f"Comando de unificación de imagen: {command_video_join}")
        status_command_video_join = subprocess.run(command_video_join, shell=True, capture_output=True, text=True)

        if status_command_video_join.returncode != 0:
            logger.error(f"Error al ejecutar el comando de unificación de imagen: {status_command_video_join.stderr}")
            raise Exception(f"Error al ejecutar el comando de unificación de imagen: {status_command_video_join.stderr}")

        logger.info("El video se procesó correctamente.")

        # Eliminar videos temporales
        os.remove(NAMEVIDEOIMAGE)
        os.remove(VIDEO_CUTOUT)
        os.remove(VIDEO_SCALE)
        logger.info("Videos temporales eliminados con éxito.")   

    except Exception as e:
        logger.error(f"Error al procesar el video: {str(e)}")


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
            logger.error(f"Error al decodificar el token: {str(e)}")
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
@app.route('/api/auth/signup', methods=['POST'])
def create_user():
    if request.json['password'] != request.json['confirm_password']:
        return jsonify({"message": "las contraseñas no coinciden"}), 400

    new_user = User(
        name=request.json['name'],
        email=request.json['email'],
        user=request.json['user'],
        password=request.json['password'],
    )

    db.session.add(new_user)
    db.session.commit()
    return jsonify(
        {"message": "cuenta creada exitosamente", "user": {"id": new_user.id, "name": new_user.name, "email": new_user.email}})


@app.route('/api/auth/login', methods=['POST'])
def login():
    user = User.query.filter_by(user=request.json['username'], password=request.json['password']).first()

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
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500))
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


# To upload a video
@app.route('/api/tasks', methods=['POST'])
@token_required
def upload_video(current_user):
    if not os.path.exists("shared/videos-uploaded"):
        os.makedirs("shared/videos-uploaded")

    if 'video' not in request.files:
        return jsonify({"error": "no se proporcionó ningún archivo de video"}), 400

    video_file = request.files['video']
    video_name = ''

    if video_file.filename == '':
        return jsonify({"error": "el nombre del archivo está vacío"}), 400

    if video_file and allowed_file(video_file.filename):
        now = datetime.datetime.now()
        name_time = now.strftime('%Y%m%d%H%M%S%f')
        user_id = current_user.id
        video_name = f'{name_time}-{user_id}-{video_file.filename}'
        video_file.save('shared/videos-uploaded/' + secure_filename(f'{name_time}-{user_id}-{video_file.filename}'))
    else:
        return jsonify({"error": "formato de archivo no permitido"}), 400

    # Upload file to bucket
    upload_files_buckets(video_name, video_name, 'shared/videos-uploaded/')

    video = Video(
        name=video_file.filename,
        path=secure_filename(video_name),
        user_id=current_user.id,
        rating=0
    )
    db.session.add(video)
    db.session.commit()

    task = Task(
        name=video_name,
        video_id=video.id,
        status="uploaded",
        user_id=current_user.id
    )
    db.session.add(task)
    db.session.commit()


    # Obtén las credenciales predeterminadas
    credentials, project = default(), 
    logger.info(f'Obteniendo credenciales: {credentials}')
    # Crea una instancia de PublisherClient con las credenciales especificadas
    publisher = pubsub_v1.PublisherClient(credentials=credentials)
    topic_path  = publisher.topic_path(constants.GCP_PROJECT, constants.TOPIC_NAME)


    # Publica el mensaje en el tópico
    status_publish = publisher.publish(
        topic_path, 
        data=json.dumps(
            {"file_name": video_file.filename, 
            "file_path": 'shared/videos-uploaded/' + video_name, 
            "user_id": current_user.id, 
            "task_id": task.id, 
            "video_id": video.id}
        ).encode("utf-8"))


    logger.info(f"Mensaje publicado en el tópico {status_publish.result()}")


    return jsonify({"message": "tarea de edición creada exitosamente"}), 200


@app.route('/api/tasks')
@token_required
def get_tasks(current_user):
    max_list = request.args.get('max', 2000)
    order = request.args.get('order', 1)

    if order == 1:
        tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.id).limit(max_list).all()
    else:
        tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.id.desc()).limit(max_list).all()

    return jsonify([{"id": task.id, "name": task.name, "video_id": task.video_id, "status": task.status} for task in tasks])


@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@token_required
def get_task(current_user, task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if task is None:
        return jsonify({"message": "tarea no encontrada"}), 404

    video = Video.query.get(task.video_id)
    if video is None:
        return jsonify({"message": "video no encontrado"}), 404

    url = f'http://{constants.HOST}/videos/{video.path}'

    return jsonify({"id": task.id, "name": task.name, "video_id": task.video_id, "status": task.status, "url": url})


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(current_user, task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if task is None:
        return jsonify({"message": "tarea no encontrada"}), 404

    db.session.delete(task)
    db.session.commit()

    return jsonify({"message": "tarea eliminada exitosamente"}), 200


@app.route('/videos/<string:video_path>', methods=['GET'])
def send_video_uploaded(video_path):
    url = get_public_url(f'procesado_{video_path}', 'shared/videos-converted/')
    return send_file(url)


@app.route('/api/videos', methods=['GET'])
def get_videos():
    videos = Video.query.all()
    return jsonify([{"id": video.id, "name": video.name, "image": video.image, "path": f'http://{constants.HOST}/videos/{video.path}', "user_id": video.user_id, "rating": video.rating} for video in videos])


@app.route('/api/videos/top', methods=['GET'])
def get_top_videos():
    videos = db.session.query(Video, User).join(User).order_by(Video.rating.desc()).all()
    return jsonify([{"id": video.id, "name": video.name, "image": video.image, "path": f'http://{constants.HOST}/videos/{video.path}', "user_id": video.user_id, "rating": video.rating, "user": {"id": user.id, "name": user.name, "email": user.email}} for video, user in videos])


@app.route('/api/videos/<int:video_id>/vote', methods=['POST'])
def vote_video(video_id):
    video = Video.query.get(video_id)
    if video is None:
        return jsonify({"message": "video no encontrado"}), 404

    if video.rating is None:
        video.rating = 0

    video.rating += 1
    db.session.commit()
    return jsonify({"message": "voto registrado exitosamente"}), 200


# Upload files google buckets
def upload_files_buckets(local_filename, remote_filename, remote_path):
    credentials, project = default()
    client = storage.Client(credentials=credentials)

    bucket_id = constants.GCP_BUCKET
    bucket = client.get_bucket(bucket_id)
    blob = bucket.blob(remote_path + remote_filename)

    file_path = remote_path + local_filename
    blob.upload_from_filename(filename=file_path)
    blob.cache_control = 'public, max-age=31536000'
    blob.patch()


def download_files_buckets(filename):
    credentials, project = default()
    client = storage.Client(credentials=credentials)

    bucket_id = constants.GCP_BUCKET
    bucket = client.get_bucket(bucket_id)
    blob = bucket.blob("shared/videos-uploaded/" + filename)

    blob.download_to_filename("shared/videos-uploaded/")


def get_public_url(file_name, file_path):
    credentials, project = default()
    client = storage.Client(credentials=credentials)

    bucket_id = constants.GCP_BUCKET
    bucket = client.get_bucket(bucket_id)
    blob = bucket.blob(file_path + file_name)

    public_url = blob.public_url

    return public_url

# Inicializar Flask-Migrate
db.create_all()
migrate = Migrate(app, db)

class Consumer:
    """
    Clase para consumir mensajes de RabbitMQ.
    """

    def __init__(self):
        # establecer el contexto de la base de datos
        app.config['SQLALCHEMY_DATABASE_URI'] = get_db()
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app_context = app.app_context()
        app_context.push()

    def consume_queue(self):
        """
        Consume mensajes de la cola de RabbitMQ y los procesa.
        """
        logger.info('Iniciando el consumo de mensajes...')
        # Obtén las credenciales predeterminadas
        credentials, project = default(), 
        logger.info(f'Obteniendo credenciales: {credentials}')
        # Crea un cliente de Pub/Sub con las credenciales predeterminadas
        subscriber = pubsub_v1.SubscriberClient(credentials=credentials)


        subscription_path = subscriber.subscription_path(
            constants.GCP_PROJECT,
            constants.TOPIC_NAME_SUB
        )
        """ 
            El "lease" es un período de tiempo durante el cual el sistema
            de mensajería espera que el suscriptor reconozca la recepción del mensaje
        """

        # Subscribe to the specified subscription and start receiving messages
        streaming_pull_future = subscriber.subscribe(
            subscription_path,
            callback=self.process_message_callback,
            flow_control=pubsub_v1.types.FlowControl(max_messages=1),
        )
        
        print(f"Listening for messages on {subscription_path}...\n")

        # Keep the script running to continue receiving messages
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()
        except Exception as e:
            logger.error(f"Error al recibir mensajes: {e}")
            streaming_pull_future.cancel() 

    def process_message_callback(self, message):
        with app.app_context():
            if not os.path.exists("shared/videos-converted"):
                os.makedirs("shared/videos-converted")
            
            # Decodifica el cuerpo del mensaje
            message_data = message.data.decode()
            message_consumer = json.loads(message_data)
            logger.info(f'Mensaje: {message_consumer}')


            try:
                task_id = message_consumer["task_id"]
                video_id = message_consumer["video_id"]
                logger.info(f"Procesando el mensaje: {task_id}")
                logger.info(f"Procesando el mensaje: {video_id}")
                
                task = Task.query.get(task_id)
                logger.info(f"Procesando el mensaje: {task}")
                video = Video.query.get(video_id)

                if task and video:
                    
                    logger.info("Procesando el video")

                    output_dir = "shared/videos-converted"

                    filename = video.path
                    file = get_public_url(filename, "shared/videos-uploaded/")

                    # Nombre del archivo de salida
                    output_filename = f"procesado_{filename}"
                    output_filename_dir = f"{output_dir}/procesado_{filename}"
                    logger.info(f"Procesando el video: {output_filename_dir}")
                    
                    # Rutas de los archivos de video, marca de agua y salida
                    video_path = file #"ruta/al/video.mp4"
                    watermark_path = "logo.png"
                    output_path = output_filename_dir #"ruta/de/salida/video_con_marca_de_agua.mp4"

                    edit_video(video_path, watermark_path, output_path, filename)

                    # Verificar si el archivo de salida existe
                    if os.path.exists(output_path):
                        logger.info("La modificación del video se realizo correctamente.")
                        # Subir video al bucket
                        upload_files_buckets(output_filename, output_filename, 'shared/videos-converted/')
                        # Actualizar estado de la tarea
                        task.status = "completado"
                        db.session.commit()
                    else:
                        logger.error("Hubo un problema al agregar la marca de agua.")
                        task.status = "problema al agregar la marca de agua"
                        db.session.commit()
                    
                    logger.info(f"Video procesado: {output_filename}")
                    message.ack()
                    logger.info("Mensaje confirmado.")
                else:
                    logger.error("No se pudo encontrar la tarea o el video asociado al mensaje.")
                    task.status = "No se pudo encontrar la tarea o el video asociado al mensaje"
                    db.session.commit()
                    
            except Exception as e:
                logger.error(f"Error al procesar el mensaje: {e}")
                task.status = "error revisar log"
                db.session.commit()

if __name__ == '__main__':

    if constants.RUN_WORKER == "true":

        consumer = Consumer()
        consumer.consume_queue()

    if constants.RUN_SERVER == "true":
        # Iniciar la aplicación Flask en el hilo principal
        app.run(debug=True, host='0.0.0.0', port=5050)
