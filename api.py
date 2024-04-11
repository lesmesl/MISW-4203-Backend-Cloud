import datetime
import jwt
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import timedelta
from werkzeug.utils import secure_filename
from functools import wraps

import constants
from manager_broker import RabbitConnection, RabbitPublisher

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

    # TODO: Implement a task queue to process the video

    # Establecer conexión con RabbitMQ
    start_channel, start_connection = RabbitConnection.start_connection()

    # publicar mensaje
    publisher = RabbitPublisher(start_channel, start_connection)

    publisher.publish_message(
        {
            "file_name": video_file.filename,
            "file_path": video_name,
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


# Inicializar Flask-Migrate
db.create_all()
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
