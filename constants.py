import os
from dotenv import load_dotenv

load_dotenv()

POSTGRESQL_DB = os.getenv("POSTGRESQL_DB")
POSTGRESQL_HOST = os.getenv("POSTGRESQL_HOST")
POSTGRESQL_USER = os.getenv("POSTGRESQL_USER")
POSTGRESQL_PASSWORD = os.getenv("POSTGRESQL_PASSWORD")
POSTGRESQL_PORT = os.getenv("POSTGRESQL_PORT")

RUN_SERVER = os.getenv("RUN_SERVER")
RUN_WORKER = os.getenv("RUN_WORKER")

GCP_BUCKET = os.getenv("GCP_BUCKET")
HOST = os.getenv("HOST")

GCP_PROJECT = os.getenv("GCP_PROJECT")
TOPIC_NAME = os.getenv("TOPIC_NAME")
TOPIC_NAME_SUB = os.getenv("TOPIC_NAME_SUB")