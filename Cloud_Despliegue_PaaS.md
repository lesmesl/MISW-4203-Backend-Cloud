# Manual de despliegue / configuración

1. Debemos tener configurado el proyecto en la plataforma de Google Cloud Platform.
2. Debemos activar la consola (shell) de Google Cloud Platform.
3. Descargamos el archivo de despliegue que se ubica dentro del respositiorio de GitHub llamado `start_deploy.sh`

```bash 
# quitamos el blob de la url para descargar
curl -L -o start_deploy.sh https://raw.githubusercontent.com/lesmesl/MISW-4203-Backend-Cloud/feat/pub-sub/start_deploy.sh
```
4. Ejecutamos el archivo de despliegue dentro del servidor con el siguiente comando:

```bash
sh start_deploy.sh
```
5. Una vez desplegado es importante verificar que el API y Worker dentro de Cloud Run estén activos. Una forma de verificar es ejecutando los siguientes endpoint:
```bash 
# API
https://web-app-dpd6vwykta-uw.a.run.app/ping
# response: pong

# Consumer
https://worker-app-dpd6vwykta-uw.a.run.app/ping
# response: pong
https://worker-app-dpd6vwykta-uw.a.run.app/cosumer
# response: {"message": "hilo iniciado"}