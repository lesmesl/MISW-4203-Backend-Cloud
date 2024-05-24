#!/bin/bash

gcloud services enable sqladmin.googleapis.com
gcloud services enable sql-component.googleapis.com

PROJECT_ID="uniandes10"
REGION="us-west1"
ZONE="us-west1-b"
## ===================================================
DB_INSTANCE_NAME="idrl-db"
echo "DB INSTANCE NAME: $DB_INSTANCE_NAME"
POSTGRES_VERSION="POSTGRES_15"
DB_PWD="1sw0rd"
DB_USER="postgres"
DB_EDITION="enterprise"
DATABASE_STORAGE_SIZE="10GB"
DB_NAME="idrl"
# CLOUD STORAGE - TAGS DE CUENTAS DE SERVICIO
BUCKET_NAME="storage-$PROJECT_ID"
BUCKET_ROLE_ID="custom.storage.admin"
BUCKET_ROLE_TITLE="Custom Storage Admin"
BUCKET_SA_NAME="storage-admin-sa"
BUCKET_SA_EMAIL="$BUCKET_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
# PUBSUB
TOPIC_NAME="topic_video_processor"
TOPIC_NAME_SUBSCRIPTION="$TOPIC_NAME-subscription"
FAIL_TOPIC_NAME="$TOPIC_NAME-fail-topic"
## REPOSITORIO DE ARTIFACTOS
WEB_REPOSITORY_NAME="api-repository"
WORKER_REPOSITORY_NAME="worker-repository"
## IMAGENES DOCKER
WEB_IMAGE="api-image-fpv:latest"
WORKER_IMAGE="worker-image-fpv:latest"
DOCKER_WEB_IMAGE="clesmesl/$WEB_IMAGE"
DOCKER_WORKER_IMAGE=$DOCKER_WEB_IMAGE
## CLOUD RUN APSS
WEB_APP_NAME="web-app"
WORKER_APP_NAME="worker-app"
PORT_WEB="5050"
PORT_WORKER="80"
## VPC PEERING
VPC_PEERING_NAME="google-managed-services-default"
VPC_CONNECTOR_NAME="fpv-connector"

## VALIDAR QUE EXISTE UN PROYECTO
EXISTING_PROJECT=$(gcloud projects describe $PROJECT_ID 2>&1)
if [[ $EXISTING_PROJECT == *"NOT_FOUND"* ]]; then
    echo "El proyecto no existe"
    exit 1
fi

# CONFIGURAR PROYECTO Y ZONA
gcloud services enable compute.googleapis.com
gcloud auth list
gcloud config list project
gcloud config set project $PROJECT_ID
gcloud config set core/project $PROJECT_ID
#gcloud compute project-info describe --project $(gcloud config get-value project)
gcloud config set compute/region $REGION
gcloud config set compute/zone $ZONE
echo -e "PROJECT ID: $PROJECT_ID\nZONE: $ZONE"

## ==================== HABILITAR EL API DE VPC ====================

gcloud services enable servicenetworking.googleapis.com compute.googleapis.com vpcaccess.googleapis.com

## ==================== CLOUD STORAGE ====================

# HABILITAR API DE STORAGE
gcloud services enable storage-component.googleapis.com

# CREAR BUCKET
gsutil mb -l $REGION gs://$BUCKET_NAME

# # AGREGAR PERMISOS DE LECTURA A TODOS LOS USUARIOS
gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME

# ## ==================== PUBSUB ====================

# HABILITAR API DE PUBSUB
gcloud services enable pubsub.googleapis.com

# # CREAR TOPIC
# gcloud pubsub topics create misw-4204-cloud-topic-fpv-task
gcloud pubsub topics create $TOPIC_NAME

# # CREAR DEAD LETTER TOPIC
# gcloud pubsub topics create misw-4204-cloud-topic-fpv-task-dead-letter
gcloud pubsub topics create $FAIL_TOPIC_NAME

# # GET ALL TOPICS LIST
gcloud pubsub topics list

# # PUBLISH MESSAGE
# gcloud pubsub topics publish misw-4204-cloud-topic-fpv-task --message "Hello, World!" 
# gcloud pubsub topics publish $TOPIC_NAME --message "Hello, World!"

# #GET SUBSCRIPTION MESSAGES
# gcloud pubsub subscriptions pull misw-4204-cloud-topic-fpv-task-subscription --auto-ack
#gcloud pubsub subscriptions pull $TOPIC_NAME_SUBSCRIPTION --auto-ack

# ## ==================== CUENTA DE SERVICIO ====================

EXISTING_ROLE=$(gcloud iam roles describe custom.storage.admin --project $PROJECT_ID 2>&1)
echo $EXISTING_ROLE

if [[ $EXISTING_ROLE == *"NOT_FOUND"* ]]; then
    # CREAR EL ROL PERSONALIZADO
    gcloud iam roles create $BUCKET_ROLE_ID \
    --project $PROJECT_ID \
    --title "$BUCKET_ROLE_TITLE" \
    --description "Custom role for storage administration"
else
    # El rol existe, verificamos si está en estado eliminado
    DELETED=$(echo "$EXISTING_ROLE" | grep -c "deleted: true")
    if [ $DELETED -eq 1 ]; then
        gcloud iam roles undelete $BUCKET_ROLE_ID \
            --project $PROJECT_ID
    fi
fi

gcloud iam roles update $BUCKET_ROLE_ID \
    --project $PROJECT_ID \
    --add-permissions storage.buckets.create,storage.buckets.update,storage.buckets.delete,storage.buckets.get,storage.buckets.list,storage.objects.get,storage.objects.list,storage.objects.create,storage.objects.delete,storage.objects.update

# CREAR CUENTA DE SERVICIO PARA PERMISOS DE STORAGE Y SQL
gcloud iam service-accounts create $BUCKET_SA_NAME \
    --description="Service account to access the storage bucket and database from the vm" \
    --display-name="Service DB VM Admin Service Account"

# ASIGNAR ROL A CUENTA DE SERVICIO
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$BUCKET_SA_EMAIL \
    --role=projects/$PROJECT_ID/roles/$BUCKET_ROLE_ID
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$BUCKET_SA_EMAIL --role=roles/cloudsql.client
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$BUCKET_SA_EMAIL --role=roles/storage.objectViewer
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$BUCKET_SA_EMAIL --role=roles/storage.admin
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$BUCKET_SA_EMAIL --role=roles/logging.admin
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$BUCKET_SA_EMAIL --role=roles/cloudsql.editor
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$BUCKET_SA_EMAIL --role=roles/pubsub.admin
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$BUCKET_SA_EMAIL --role=roles/run.invoker
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$BUCKET_SA_EMAIL --role=roles/iam.serviceAccountTokenCreator
gcloud iam roles create custom.storage.admin \
    --project $PROJECT_ID \
    --title "Custom Storage Admin" \
    --description "Custom role for storage administration" \
    --permissions="storage.buckets.create,storage.buckets.update,storage.buckets.delete,storage.buckets.get,storage.buckets.list,storage.objects.get,storage.objects.list,storage.objects.create,storage.objects.delete,storage.objects.update"

# ## ==================== CREAR RANDO IP PARA LA INSTANCIA ====================


gcloud compute addresses create $VPC_PEERING_NAME \
    --global \
    --purpose=VPC_PEERING \
    --prefix-length 16 \
    --description "peering range for Google" \
    --network default

gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges $VPC_PEERING_NAME \
    --network default

## Crear el conector de VPC

gcloud compute networks vpc-access connectors create $VPC_CONNECTOR_NAME \
    --region $REGION \
    --network default \
    --range "10.8.0.0/28"

# Verificar la creación del conector VPC
gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR_NAME --region=$REGION

# ## ==================== INSTANCIA DE BASE DE DATOS ====================

# HABILITAR API DE SQL
gcloud services enable sql-component.googleapis.com

## CREAR INSTANCIA DE BASE DE DATOS
gcloud sql instances create $DB_INSTANCE_NAME \
    --database-version $POSTGRES_VERSION \
    --root-password $DB_PWD \
    --edition $DB_EDITION \
    --region $REGION \
    --storage-size $DATABASE_STORAGE_SIZE \
    --no-storage-auto-increase \
    --memory 3.75GB \
    --cpu 1 \
    --no-assign-ip \
    --network default

# Obtener la IP privada de la instancia de Cloud SQL
DB_PRIVATE_IP=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(ipAddresses.ipAddress)")
echo "Private IP of Cloud SQL instance: $DB_PRIVATE_IP"

# ## ==================== BASE DE DATOS ====================

# CREAR BASE DE DATOS
gcloud sql databases create $DB_NAME \
    --instance $DB_INSTANCE_NAME

# ASIGNAR CONTRASENIA A USUARIO POR DEFECTO
gcloud sql users set-password $DB_USER \
    --instance $DB_INSTANCE_NAME \
    --password $DB_PWD

DB_CONNECTION_URL="postgresql://$DB_USER:$DB_PWD@$DB_PRIVATE_IP:5432/$DB_NAME"
echo "DB CONNECTION URL: $DB_CONNECTION_URL"

## ==================== CONEXIONES DE BASE DE DATOS ====================

CONECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format='value(connectionName)')
echo "CONNECTION NAME: $CONECTION_NAME"

# # HACER PRUEBA DE CONEXION DE BASE DE DATOS DESDE LA INSTANCIA POR SSH
# # sudo apt-get install postgresql-client -y
# # psql --host=35.197.11.11 --port=5432 --username=postgres --password --dbname=db-test

## ======================  HABILITAR SERVICIO DE ARTIFACT ===================

gcloud services enable artifactregistry.googleapis.com  run.googleapis.com

## ======================  CREAR REPOSITORIO ===================

gcloud artifacts repositories create $WEB_REPOSITORY_NAME \
    --project $PROJECT_ID \
    --repository-format docker \
    --location $REGION \
    --description "Repositorio de artefacto para la aplicacion web"

echo "Creado el repositorio de artefacto para la aplicacion web $WEB_REPOSITORY_NAME"

gcloud artifacts repositories create $WORKER_REPOSITORY_NAME \
    --project $PROJECT_ID \
    --repository-format docker \
    --location $REGION \
    --description "Repositorio de artefacto para la aplicacion Worker"

echo "Creado el repositorio de artefacto para la aplicacion worker $WORKER_REPOSITORY_NAME"


## ======================  DESCARGAR LAS IMAGENES DE DOCKER ===================
echo "Descargando imagen de la aplicacion $DOCKER_WEB_IMAGE"
docker pull $DOCKER_WEB_IMAGE
echo "Imagen de la aplicacion web/worker descargada"

## ======================  ETIQUETAR LA IMAGEN ===================
echo "docker tag $DOCKER_WEB_IMAGE $REGION-docker.pkg.dev/$PROJECT_ID/$WEB_REPOSITORY_NAME/$WEB_IMAGE"
docker tag $DOCKER_WEB_IMAGE $REGION-docker.pkg.dev/$PROJECT_ID/$WEB_REPOSITORY_NAME/$WEB_IMAGE

echo "docker tag $DOCKER_WORKER_IMAGE $REGION-docker.pkg.dev/$PROJECT_ID/$WORKER_REPOSITORY_NAME/$WORKER_IMAGE"
docker tag $DOCKER_WORKER_IMAGE $REGION-docker.pkg.dev/$PROJECT_ID/$WORKER_REPOSITORY_NAME/$WORKER_IMAGE
# docker tag nipoanz/worker-fpv:6.0.5 us-west1-docker.pkg.dev/misw-4204-cloud/fpv-batch-repository/worker-fpv:6.0.5

## ======================  AUTENTICAR CON EL REPOSITORIO ===================

gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

## ======================  SUBIR LA IMAGEN ===================

docker push $REGION-docker.pkg.dev/$PROJECT_ID/$WEB_REPOSITORY_NAME/$WEB_IMAGE

docker push $REGION-docker.pkg.dev/$PROJECT_ID/$WORKER_REPOSITORY_NAME/$WORKER_IMAGE
# docker push us-west1-docker.pkg.dev/misw-4204-cloud/fpv-batch-repository/worker-fpv:6.0.5

## ======================  CLOUD RUN ===================

# https://cloud.google.com/sql/docs/postgres/connect-connectors#python
# https://cloud.google.com/sql/docs/postgres/connect-run#public-ip-default_1

echo "connectionName: $CONECTION_NAME"
INSTANCE_UNIX_SOCKET="/cloudsql/$CONECTION_NAME"
# echo "INSTANCE UNIX SOCKET: $INSTANCE_UNIX_SOCKET"
# echo "Instance db user: $DB_USER"
# echo "Instance db password: $DB_PWD"
# echo "Instance db name: $DB_NAME"
# Limites de servicio
# https://cloud.google.com/run/quotas#cloud_run_limits

gcloud run deploy $WEB_APP_NAME \
    --project $PROJECT_ID \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/$WEB_REPOSITORY_NAME/$WEB_IMAGE  \
    --ingress all \
    --region $REGION \
    --platform managed \
    --set-env-vars "POSTGRESQL_DB=$DB_NAME" \
    --set-env-vars "POSTGRESQL_USER=$DB_USER" \
    --set-env-vars "POSTGRESQL_PASSWORD=$DB_PWD" \
    --set-env-vars "POSTGRESQL_HOST=$DB_PRIVATE_IP" \
    --set-env-vars "POSTGRESQL_PORT=5432" \
    --set-env-vars "RUN_SERVER=true" \
    --set-env-vars "RUN_WORKER=false" \
    --set-env-vars "GCP_BUCKET=$BUCKET_NAME" \
    --set-env-vars "HOST=127.0.0.1" \
    --set-env-vars "GCP_PROJECT=betuniandes" \
    --set-env-vars "TOPIC_NAME=$TOPIC_NAME" \
    --set-env-vars "TOPIC_NAME_SUB=$TOPIC_NAME_SUBSCRIPTION" \
    --service-account $BUCKET_SA_EMAIL \
    --tag http-web-server \
    --description "Servicios api rest - capa web" \
    --cpu 2 \
    --memory 4Gi \
    --add-cloudsql-instances $CONECTION_NAME \
    --vpc-egress=all-traffic \
    --vpc-connector $VPC_CONNECTOR_NAME \
    --allow-unauthenticated \
    --use-http2 \
    --min-instances 1 \
    --max-instances 3 \
    --concurrency 120 \
    --cpu-boost


gcloud run deploy $WORKER_APP_NAME \
    --project $PROJECT_ID \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/$WORKER_REPOSITORY_NAME/$WORKER_IMAGE  \
    --ingress all \
    --port $PORT_WORKER \
    --region $REGION \
    --platform managed \
    --set-env-vars "POSTGRESQL_DB=$DB_NAME" \
    --set-env-vars "POSTGRESQL_USER=$DB_USER" \
    --set-env-vars "POSTGRESQL_PASSWORD=$DB_PWD" \
    --set-env-vars "POSTGRESQL_HOST=$DB_PRIVATE_IP" \
    --set-env-vars "POSTGRESQL_PORT=5432" \
    --set-env-vars "RUN_SERVER=false" \
    --set-env-vars "RUN_WORKER=true" \
    --set-env-vars "GCP_BUCKET=$BUCKET_NAME" \
    --set-env-vars "HOST=127.0.0.1" \
    --set-env-vars "GCP_PROJECT=betuniandes" \
    --set-env-vars "TOPIC_NAME=$TOPIC_NAME" \
    --set-env-vars "TOPIC_NAME_SUB=$TOPIC_NAME_SUBSCRIPTION" \
    --service-account $BUCKET_SA_EMAIL \
    --tag http-batch-server \
    --description "Servicio de procesamiento de tareas en segundo plano - capa batch" \
    --cpu 2 \
    --memory 4Gi \
    --min-instances 1 \
    --max-instances 3 \
    --add-cloudsql-instances $CONECTION_NAME \
    --vpc-egress=all-traffic \
    --vpc-connector $VPC_CONNECTOR_NAME \
    --allow-unauthenticated


## ======================  DESCRIBIR EL SERVICIO ===================

# gcloud run services describe $WEB_APP_NAME --region $REGION
# gcloud run services describe $WORKER_APP_NAME --region $REGION

## ======================  OBTENER LA IP DEL SERVICIO ===================

WEB_APP_URL=$(gcloud run services describe $WEB_APP_NAME --region $REGION --format='value(status.url)')
WORKER_APP_URL=$(gcloud run services describe $WORKER_APP_NAME --region $REGION --format='value(status.url)')
#  gcloud run services describe batch-app  --region us-west1 --format='value(status.url)'

## Añadir variables de entorno a web app
echo "WEB APP URL: $WEB_APP_URL"
echo "BATCH APP URL: $WORKER_APP_URL"

## ====================== CREAR SUSCRIPCION ===================

# # CREATE SUBSCRIPTION
# gcloud pubsub subscriptions create misw-4204-cloud-topic-fpv-task-subscription --topic misw-4204-cloud-topic-fpv-task  --max-delivery-attempts 5 --dead-letter-topic misw-4204-cloud-topic-fpv-task-dead-letter
gcloud pubsub subscriptions create $TOPIC_NAME_SUBSCRIPTION \
    --topic $TOPIC_NAME \
    --ack-deadline 600 \
    --max-delivery-attempts 5 \
    --push-endpoint $WORKER_APP_URL \
    --push-auth-service-account $BUCKET_SA_EMAIL \
    --dead-letter-topic $FAIL_TOPIC_NAME

# # GET ALL SUBSCRIPTIONS LIST
gcloud pubsub subscriptions list