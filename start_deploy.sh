#!/bin/bash

# Habilitar APIs necesarias para iniciar el despliegue
gcloud services enable sqladmin.googleapis.com
gcloud services enable servicenetworking.googleapis.com compute.googleapis.com vpcaccess.googleapis.com

# Variables de configuración del proyecto
PROJECT_ID="uniandes10"
REGION="us-west1"
ZONE="us-west1-b"
DB_INSTANCE_NAME="idrl-db"
POSTGRES_VERSION="POSTGRES_15"
DB_PWD="1sw0rd"
DB_USER="postgres"
DB_EDITION="enterprise"
DATABASE_STORAGE_SIZE="10GB"
DB_NAME="idrl"

# Configuración de Cloud Storage
BUCKET_NAME="storage-$PROJECT_ID"
BUCKET_ROLE_ID="custom.storage.admin"
BUCKET_ROLE_TITLE="Custom Storage Admin"
BUCKET_NAME="storage-admin-sa"
BUCKET_PATH="$BUCKET_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# Configuración de Pub/Sub
TOPIC_NAME="topic_video_processor"
SUBSCRIPTION_NAME="$TOPIC_NAME-sub"
FAIL_TOPIC_NAME="$TOPIC_NAME-fail-topic"

# Configuración de repositorios y artefactos
WEB_REPOSITORY_NAME="api-repository"
WORKER_REPOSITORY_NAME="worker-repository"

# Imágenes de Docker para API y Worker
WEB_IMAGE="api-image-fpv:latest"
WORKER_IMAGE="worker-image-fpv:latest"
DOCKER_WEB_IMAGE="clesmesl/$WEB_IMAGE"
DOCKER_WORKER_IMAGE="clesmesl/$WORKER_IMAGE"

# Nombres de las aplicaciones en Cloud Run
WEB_APP_NAME="web-app"
WORKER_APP_NAME="worker-app"
PORT_WEB="5050"
PORT_WORKER="8080"

# Configuración de VPC
VPC_PEERING_NAME="google-managed-services-default"
VPC_CONNECTOR_NAME="fpv-connector"

# Validar existencia del proyecto
EXISTING_PROJECT=$(gcloud projects describe $PROJECT_ID 2>&1)
if [[ $EXISTING_PROJECT == *"NOT_FOUND"* ]]; then
    echo "El proyecto no existe"
    exit 1
fi

# Configuración del proyecto y zona
gcloud services enable compute.googleapis.com
gcloud auth list
gcloud config list project
gcloud config set project $PROJECT_ID
gcloud config set core/project $PROJECT_ID
gcloud config set compute/region $REGION
gcloud config set compute/zone $ZONE
echo -e "PROJECT ID: $PROJECT_ID\nZONE: $ZONE"

## ==================== CLOUD STORAGE ====================

# Habilitar API de Cloud Storage
gcloud services enable storage-component.googleapis.com

# Crear bucket
gsutil mb -l $REGION gs://$BUCKET_NAME

# Agregar permisos de lectura a todos los usuarios
gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME

## ==================== PUB/SUB ====================

# Habilitar API de Pub/Sub
gcloud services enable pubsub.googleapis.com

# Crear Dead Letter Topic
gcloud pubsub topics create $FAIL_TOPIC_NAME

# Listar todos los topics
gcloud pubsub topics list

## ==================== CUENTA DE SERVICIO ====================

# Verificar y crear rol personalizado para Cloud Storage
EXISTING_ROLE=$(gcloud iam roles describe $BUCKET_ROLE_ID --project $PROJECT_ID 2>&1)
if [[ $EXISTING_ROLE == *"NOT_FOUND"* ]]; then
    gcloud iam roles create $BUCKET_ROLE_ID \
        --project $PROJECT_ID \
        --title "$BUCKET_ROLE_TITLE" \
        --description "Custom role for storage administration"
else
    DELETED=$(echo "$EXISTING_ROLE" | grep -c "deleted: true")
    if [ $DELETED -eq 1 ]; then
        gcloud iam roles undelete $BUCKET_ROLE_ID --project $PROJECT_ID
    fi
fi

# Actualizar rol personalizado con permisos necesarios
gcloud iam roles update $BUCKET_ROLE_ID \
    --project $PROJECT_ID \
    --add-permissions storage.buckets.create,storage.buckets.update,storage.buckets.delete,storage.buckets.get,storage.buckets.list,storage.objects.get,storage.objects.list,storage.objects.create,storage.objects.delete,storage.objects.update

# Crear cuenta de servicio para acceder a Cloud Storage y Cloud SQL
gcloud iam service-accounts create $BUCKET_NAME \
    --description="Service account to access the storage bucket and database from the VM" \
    --display-name="Service DB VM Admin Service Account"

# Asignar roles a la cuenta de servicio
for role in roles/cloudsql.client roles/storage.objectViewer roles/storage.admin roles/logging.admin roles/cloudsql.editor roles/pubsub.admin roles/run.invoker roles/iam.serviceAccountTokenCreator; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member=serviceAccount:$BUCKET_PATH \
        --role=$role
done

# Crear topic de Pub/Sub
gcloud pubsub topics create $TOPIC_NAME
gcloud pubsub subscriptions create $SUBSCRIPTION_NAME \
    --topic $TOPIC_NAME \
    --project $PROJECT_ID \
    --push-auth-service-account=$BUCKET_PATH

# Crear rango de peering VPC
gcloud compute addresses create $VPC_PEERING_NAME \
    --global \
    --purpose=VPC_PEERING \
    --prefix-length 16 \
    --description "peering range for Google" \
    --network default

# Conectar el peering de la VPC
gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges $VPC_PEERING_NAME \
    --network default

# Crear conector de VPC
gcloud compute networks vpc-access connectors create $VPC_CONNECTOR_NAME \
    --region $REGION \
    --network default \
    --range "10.8.0.0/28"

# Verificar la creación del conector VPC
gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR_NAME --region=$REGION

## ==================== INSTANCIA DE BASE DE DATOS ====================

# Habilitar API de Cloud SQL
gcloud services enable sql-component.googleapis.com

# Crear instancia de base de datos
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

# Crear base de datos
gcloud sql databases create $DB_NAME --instance $DB_INSTANCE_NAME

# Asignar contraseña al usuario por defecto
gcloud sql users set-password $DB_USER --instance $DB_INSTANCE_NAME --password $DB_PWD

# URL de conexión a la base de datos
DB_CONNECTION_URL="postgresql://$DB_USER:$DB_PWD@$DB_PRIVATE_IP:5432/$DB_NAME"
echo "DB CONNECTION URL: $DB_CONNECTION_URL"

## ==================== CONEXIONES DE BASE DE DATOS ====================

# Obtener el nombre de conexión de la instancia de Cloud SQL
CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format='value(connectionName)')
echo "CONNECTION NAME: $CONNECTION_NAME"

## ====================== CREAR REPOSITORIO ===================

# Habilitar APIs de Artifact Registry y Cloud Run
gcloud services enable artifactregistry.googleapis.com run.googleapis.com

# Crear repositorios de artefactos para la aplicación web y worker
gcloud artifacts repositories create $WEB_REPOSITORY_NAME \
    --project $PROJECT_ID \
    --repository-format docker \
    --location $REGION \
    --description "Repositorio de artefacto para la aplicación web"
echo "Creado el repositorio de artefacto para la aplicación web $WEB_REPOSITORY_NAME"

gcloud artifacts repositories create $WORKER_REPOSITORY_NAME \
    --project $PROJECT_ID \
    --repository-format docker \
    --location $REGION \
    --description "Repositorio de artefacto para la aplicación Worker"
echo "Creado el repositorio de artefacto para la aplicación worker $WORKER_REPOSITORY_NAME"

## ====================== DESCARGAR LAS IMÁGENES DE DOCKER ===================
docker pull $DOCKER_WEB_IMAGE
docker pull $DOCKER_WORKER_IMAGE
echo "Imagen de la aplicación web/worker descargada"

## ====================== ETIQUETAR LA IMAGEN ===================
docker tag $DOCKER_WEB_IMAGE $REGION-docker.pkg.dev/$PROJECT_ID/$WEB_REPOSITORY_NAME/$WEB_IMAGE
docker tag $DOCKER_WORKER_IMAGE $REGION-docker.pkg.dev/$PROJECT_ID/$WORKER_REPOSITORY_NAME/$WORKER_IMAGE

## ====================== AUTENTICAR CON EL REPOSITORIO ===================
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

## ====================== SUBIR LA IMAGEN ===================
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$WEB_REPOSITORY_NAME/$WEB_IMAGE
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$WORKER_REPOSITORY_NAME/$WORKER_IMAGE

## ====================== CLOUD RUN ===================
INSTANCE_UNIX_SOCKET="/cloudsql/$CONNECTION_NAME"

# Desplegar aplicación web en Cloud Run
gcloud run deploy $WEB_APP_NAME \
    --project $PROJECT_ID \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/$WEB_REPOSITORY_NAME/$WEB_IMAGE  \
    --ingress all \
    --port $PORT_WEB \
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
    --set-env-vars "GCP_PROJECT=$PROJECT_ID" \
    --set-env-vars "TOPIC_NAME=$TOPIC_NAME" \
    --set-env-vars "TOPIC_NAME_SUB=$SUBSCRIPTION_NAME" \
    --service-account $BUCKET_PATH \
    --tag http-web-server \
    --description "Servicios API REST - capa web" \
    --cpu 2 \
    --memory 4Gi \
    --add-cloudsql-instances $CONNECTION_NAME \
    --vpc-egress=all-traffic \
    --vpc-connector $VPC_CONNECTOR_NAME \
    --allow-unauthenticated \
    --min-instances 1 \
    --max-instances 3 \
    --concurrency 120 \
    --cpu-boost

# Desplegar aplicación worker en Cloud Run
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
    --set-env-vars "GCP_PROJECT=$PROJECT_ID" \
    --set-env-vars "TOPIC_NAME=$TOPIC_NAME" \
    --set-env-vars "TOPIC_NAME_SUB=$SUBSCRIPTION_NAME" \
    --service-account $BUCKET_PATH \
    --tag http-batch-server \
    --description "Servicio de procesamiento de tareas en segundo plano - capa batch" \
    --cpu 2 \
    --memory 4Gi \
    --min-instances 1 \
    --max-instances 3 \
    --add-cloudsql-instances $CONNECTION_NAME \
    --vpc-egress=all-traffic \
    --vpc-connector $VPC_CONNECTOR_NAME \
    --allow-unauthenticated

## ====================== OBTENER LA IP PARA AÑADIRLO A LA SUSCRIPCIÓN ===================

WEB_APP_URL=$(gcloud run services describe $WEB_APP_NAME --region $REGION --format='value(status.url)')
WORKER_APP_URL=$(gcloud run services describe $WORKER_APP_NAME --region $REGION --format='value(status.url)')

echo "WEB APP URL: $WEB_APP_URL"
echo "BATCH APP URL: $WORKER_APP_URL"

# Crear suscripción de Pub/Sub con endpoint de la aplicación worker
gcloud pubsub subscriptions create $SUBSCRIPTION_NAME \
    --topic $TOPIC_NAME \
    --push-endpoint $WORKER_APP_URL \
    --push-auth-service-account $BUCKET_PATH \
    --dead-letter-topic $FAIL_TOPIC_NAME
