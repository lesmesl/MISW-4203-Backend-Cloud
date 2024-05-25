# Cloud Run

``` bash
# limpiar docker
docker system prune -a -f

docker build -t clesmesl/api-image-fpv:latest -f Dockerfile-api .
docker build -t clesmesl/worker-image-fpv:latest -f Dockerfile-worker .
docker push clesmesl/api-image-fpv:latest
docker push clesmesl/worker-image-fpv:latest
echo "done"

# construi contenedor através de la imagen de api con variables de entorno
$ docker run -p 5050:5050 -e PORT=5050 -e POSTGRESQL_DB=idrl2 -e POSTGRESQL_USER=postgres2 -e POSTGRESQL_PASSWORD=admin2 -e POSTGRESQL_HOST=127.0.0.1 -e POSTGRESQL_PORT=5432 -e RUN_SERVER=true -e RUN_WORKER=false -e GCP_BUCKET=storage-uniandes -e HOST=127.0.0.1 -e GCP_PROJECT=betuniandes2 -e TOPIC_NAME=topic_video_processor -e TOPIC_NAME_SUB=topic_video_processor-sub clesmesl/api-image-fpv:latest

# reconstruir la imagen local y volverla a subir


``` 

