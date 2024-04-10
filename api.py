import datetime
import jwt
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import timedelta
from werkzeug.utils import secure_filename

import constants

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
    name = db.Column(db.String(50))
    password = db.Column(db.String(50))
    user = db.Column(db.String(50))
    email = db.Column(db.String(50))


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
    return jsonify({"message": "usuario creado", "user": {"id": new_user.id, "name": new_user.name, "email": new_user.email}})


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
    name = db.Column(db.String(50))
    path = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# To upload a video
@app.route('/video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "no se proporcionó ningún archivo de video"}), 400

    video_file = request.files['video']

    if video_file.filename == '':
        return jsonify({"error": "el nombre del archivo está vacío"}), 400

    if video_file and allowed_file(video_file.filename):
        video_file.save('videos-uploaded/' + secure_filename(video_file.filename))
        return jsonify({"message": "video subido exitosamente"}), 200

    else:
        return jsonify({"error": "formato de archivo no permitido"}), 400


# Inicializar Flask-Migrate
db.create_all()
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
