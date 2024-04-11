import threading
import datetime
import logging
import jwt
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import timedelta
from werkzeug.utils import secure_filename
from functools import wraps
from flask import send_file

import constants
from manager_broker import RabbitConnection, RabbitConsumer, RabbitPublisher

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


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    password = db.Column(db.String(50))
    user = db.Column(db.String(50))
    email = db.Column(db.String(100))


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


# To create a user
@app.route('/api/auth/signup', methods=['POST'])
def create_user():
    if request.json['password'] != request.json['password_confirmation']:
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
        {"message": "usuario creado", "user": {"id": new_user.id, "name": new_user.name, "email": new_user.email}})


@app.route('/api/auth/login', methods=['POST'])
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


@app.route('/videos', methods=['GET'])
def get_videos():
    videos = Video.query.all()
    return jsonify([{"id": video.id, "name": video.name, "image": video.image, "path": video.path,
                     "user_id": video.user_id, "rating": video.rating} for video in videos])


@app.route('/videos/top', methods=['GET'])
def get_top_videos():
    # Obtener los videos con mayor rating incluyendo el usuario que lo subió
    videos = db.session.query(Video, User).join(User).order_by(Video.rating.desc()).all()
    return jsonify([{"id": video.id, "name": video.name, "image": video.image, "path": video.path,
                     "user_id": video.user_id, "rating": video.rating,
                     "user": {"id": user.id, "name": user.name, "email": user.email}} for video, user in videos])


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


@app.route('/video/<path:filename>', methods=['GET'])
def send_robots_txt():
    return send_file(app.config['BASE_DIR'] + '/robots.txt')


'''
Task section
'''


@app.route('/api/tasks', methods=['GET'])
@token_required
def get_tasks(current_user):
    max_list = request.args.get('max', 10)
    order = request.args.get('order', 1)

    if order == 1:
        tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.id.desc()).limit(max_list).all()
    else:
        tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.id.asc()).limit(max_list).all()

    return jsonify([{"id": task.id, "name": task.name, "video_id": task.video_id, "status": task.status} for task in tasks])


# To upload a video
@app.route('/api/tasks', methods=['POST'])
@token_required
def upload_video(current_user):
    if 'video' not in request.files:
        return jsonify({"error": "no se proporcionó ningún archivo de video; la tarea no fue creada"}), 400

    video_file = request.files['video']
    video_name = ''

    if video_file.filename == '':
        return jsonify({"error": "el nombre del archivo está vacío; la tarea no fue creada"}), 400

    if video_file and allowed_file(video_file.filename):
        now = datetime.datetime.now()
        user_id = current_user.id
        video_name = f'{now.strftime("%Y%m%d%H%M%S")}-{user_id}-{video_file.filename}'
        video_file.save(
            'videos-uploaded/' + secure_filename(f'{now.strftime("%Y%m%d%H%M%S")}-{user_id}-{video_file.filename}'))
    else:
        return jsonify({"error": "formato de archivo no permitido; la tarea no fue creada"}), 400

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
        status="uploaded"
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

    return jsonify({"message": "tarea creada exitosamente"}), 200


@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@token_required
def get_task(current_user, task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if task is None:
        return jsonify({"message": "tarea no encontrada"}), 404

    video = Video.query.get(task.video_id)
    if video is None:
        return jsonify({"message": "video no encontrado"}), 404

    if task.status == "processed":

    video_url = f"http://localhost:5050/video/{video.path}"
    return jsonify({"id": task.id, "name": task.name, "video_id": task.video_id, "status": task.status, "video_url": video_url})


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

if __name__ == '__main__':
    # Crear un hilo para el consumidor
    consumer_thread = threading.Thread(target=run_consumer)
    consumer_thread.start()

    # Iniciar la aplicación Flask en el hilo principal
    app.run(debug=True, host='0.0.0.0', port=5050)
