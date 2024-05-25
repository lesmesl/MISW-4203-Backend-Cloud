# Cloud Run

``` bash
# construir la IMAGEN del dockerfile llado dockerfile-api
docker build -t clesmesl/api-image-fpv:latest -f Dockerfile-api .
docker build -t clesmesl/worker-image-fpv:latest -f Dockerfile-worker .

POSTGRESQL_DB=idrl2
POSTGRESQL_USER=postgres2
POSTGRESQL_PASSWORD=admin2
POSTGRESQL_HOST=35.247.34.41
POSTGRESQL_PORT=5432
RUN_SERVER=true
RUN_WORKER=false
GCP_BUCKET=storage-uniandes
# HOST=34.49.33.203 #IP del balanceador de carga
HOST=127.0.0.12
GCP_PROJECT=betuniandes2
TOPIC_NAME=topic_video_processor
TOPIC_NAME_SUB=topic_video_processor-sub

# construi contenedor através de la imagen de api con variables de entorno
$ docker run -p 5050:5050 -e PORT=5050 -e POSTGRESQL_DB=idrl2 -e POSTGRESQL_USER=postgres2 -e POSTGRESQL_PASSWORD=admin2 -e POSTGRESQL_HOST=127.0.0.1 -e POSTGRESQL_PORT=5432 -e RUN_SERVER=true -e RUN_WORKER=false -e GCP_BUCKET=storage-uniandes -e HOST=127.0.0.1 -e GCP_PROJECT=betuniandes2 -e TOPIC_NAME=topic_video_processor -e TOPIC_NAME_SUB=topic_video_processor-sub clesmesl/api-image-fpv:latest

docker system prune -a -f

docker image ls

docker build -t clesmesl/api-image-fpv:latest -f Dockerfile-api .
docker build -t clesmesl/worker-image-fpv:latest -f Dockerfile-worker .
docker push clesmesl/api-image-fpv:latest
docker push clesmesl/worker-image-fpv:latest
echo "done"
# reconstruir la imagen local y volverla a subir


``` 

