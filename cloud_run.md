# Cloud Run

``` bash
# construir la IMAGEN del dockerfile llado dockerfile-api
$ docker build -t clesmesl/api-image-fpv:latest -f Dockerfile-api .

# construir la IMAGEN del dockerfile llado dockerfile-worker
$ docker build -t clesmesl/worker-image-fpv:latest -f Dockerfile-worker .

docker image ls

$ docker push clesmesl/api-image-fpv:latest
$ docker push clesmesl/worker-image-fpv:latest
```