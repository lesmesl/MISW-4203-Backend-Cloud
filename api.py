from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token, JWTManager

app = Flask(__name__)

# Postgresql connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/idrl'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
    role = db.Column(db.String(50))
    email = db.Column(db.String(50))


# To create a user
@app.route('/users', methods=['POST'])
def create_user():
    return 'unimplemented', 501


'''
Video section
'''


# To upload a video
@app.route('/video', methods=['POST'])
def video():
    return 'unimplemented', 501


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
