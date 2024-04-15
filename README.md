# MISW-4203-Backend-CLoud 

La International FPV Drone Racing League (IDRL) es una organización líder dedicada a promover y avanzar en el emocionante deporte de las carreras de drones en Primera Persona (FPV) a nivel global. La tecnología FPV permite a los pilotos obtener visuales en tiempo real desde una cámara instalada en el dron, ofreciendo una experiencia de carrera inmersiva y emocionante como ninguna otra. Con un compromiso de fomentar el talento y la innovación dentro de la comunidad FPV, IDRL se enorgullece en anunciar el lanzamiento de una iniciativa innovadora: FPV Enthusiast Tour - IDRL.

La IDRL busca promover el deporte de carreras de drones FPV a nivel global. Para facilitar la clasificación al FPV Enthusiast Tour - IDRL, se requiere desarrollar una plataforma web donde los pilotos puedan cargar sus videos y el público vote por sus favoritos.

El backend REST de la aplicación web ha sido implementado para proporcionar a los usuarios una interfaz interactiva y accesible para explorar la plataforma. Este backend incluye un conjunto de servicios REST meticulosamente diseñados para facilitar varias funciones esenciales, como la creación de cuentas de usuario, el inicio de sesión, el listado y manejo de tareas de edición de vídeos, la subida y edición de vídeos, la consulta de detalles sobre tareas específicas y la eliminación de vídeos. Estas funcionalidades aseguran una experiencia de usuario fluida y eficiente, permitiendo a los usuarios gestionar sus contenidos y preferencias con facilidad.


## Información del Equipo de Desarrollo

| **Proyecto**        | International FPV Drone Racing League (IDRL)   |                     |
|-----------------|---------------------|---------------------|
| **Grupo**       |       Grupo 16      |                     |
| **Integrantes** | **Nombre**          | **Rol**             |
|                 | Anderson Rodriguez  | Desarrollador        |
|                 | Pedro Buitrago | Desarrollador |
|                 | Irina Sinning  | Desarrollador  |
|                 |Camilo Lesmes  | Desarrollador |

# Instrucciones de Instalación y Configuración

## Paso 1: Levantar el Proyecto
Para iniciar el proyecto, use el siguiente comando en su terminal:
```bash 
docker compose up -d
```

## Paso 2: Cargar la colección y las variables de entorno de Postman
Utilice las colecciones de Postman proporcionadas para probar la API y asegurarse de que todo funcione como se espera.

- Cargar la colección y las variables de entorno de postman


### Comandos útiles

```bash 
# Comando para eliminar contenedores, imágenes y volúmenes
docker-compose down -v --rmi all

# Liberar memoria si se bajarón los contenedores y sigue elevada pero borra todo
docker system prune -a --volumes

# Guia si windows se eleva la ram
https://medium.com/@ahmadsalahuddeen6017/how-to-resolve-high-ram-usage-by-vmmem-exe-when-running-docker-on-wsl-698c92018a9f

```

### Formato de json para probar manualmente el consumer
```json
    {
        "file_name": "",
        "file_path": "videos-uploaded + video_name",
        "user_id": 1,
        "task_id": 1,
        "video_id": 1
    }
```
## Enlaces

### Lista de videos verticales
https://www.pexels.com/video/a-woman-busy-writing-on-a-paper-4778723/

### Enlaces al Repositorio del Proyecto
* [README](https://github.com/lesmesl/MISW-4203-Backend-Cloud/blob/main/README.md)
* [WIKI](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki) 
* [Diseño de Arquitectura](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki/Entrega-1:-Arquitectura-de-la-Aplicaci%C3%B3n:--International-FPV-Drone-Racing-League-(IDRL))
* [Código General de Aplicación](https://github.com/lesmesl/MISW-4203-Backend-Cloud/blob/main) 
* [Sustentaciones en Video](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki/Sustentaciones-en-Video)
* [Documentación Páginas de la wiki del Proyecto](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki/Documentaci%C3%B3n-P%C3%A1ginas-de-la-wiki-del-Proyecto)
* [Documentos PDF del Proyecto](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki/Documentos-PDF-del-Proyecto--IDRL)


# Entregas del Proyecto

## Semanas 1 – 2: Entrega 1 - Aplicaciones Web Escalables en un Entorno Tradicional

### Entregables:
* **Aplicación web con funcionalidades básicas implementadas**.
  * **Backend REST desarrollado para la aplicación**.
    * [**Pagina WIKI Entrega 1: Backend REST + Procesamiento Asíncrono**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki/Entrega-1:-Backend-REST---Procesamiento-As%C3%ADncrono)
    * [**Código API.py**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/blob/main/api.py)
    * [**Video de demostracion de Proyecto - API**](https://www.youtube.com/watch?v=IJIeDC9ll08)
  * **Procesos asíncronos para la edición de videos implementados**.
    * [**Página WIKI Entrega 1: Backend REST + Procesamiento Asíncrono**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki/Entrega-1:-Backend-REST---Procesamiento-As%C3%ADncrono)
    * [**Código de API.py + Procesos asíncronos**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/blob/main/api.py)
    * [**Video de demostracion de Proyecto - API + Procesos asíncronos**](https://www.youtube.com/watch?v=IJIeDC9ll08)
  * **Documentación en Postman de la API REST**
    * [**Página WIKI Entrega 1: Documentación en Postman**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki/Documentaci%C3%B3n-en-Postman-de-la-API-REST)
    * [**Workspace de Colecciones Postman: IDRL API**](https://www.postman.com/speeding-sunset-217733/workspace/public-idrl-api-uniandes/collection/5831053-9e42e5ab-53d2-4fc6-9081-d4d3a481e191) 
    * [**Código de Colecciones Postman: IDRL API.postman_collection.json**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/blob/main/IDRL%20API.postman_collection.json)
    * [**Código de Environment backend Cloud.postman_environment.json**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/blob/main/Environment%20backend%20Cloud.postman_environment.json)
    * [**Video de demostracion de Proyecto - API + Procesos asíncronos y Colecciones en Postman**](https://www.youtube.com/watch?v=IJIeDC9ll08)
* **Arquitectura de la Aplicación**
    * [**Página Wiki E1- Arquitectura de la Aplicación**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki/Entrega-1:-Arquitectura-de-la-Aplicaci%C3%B3n:--International-FPV-Drone-Racing-League-(IDRL))
     * [**E1 - Arquitectura de la Aplicación.pdf**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/files/14972150/E1.-.Arquitectura.de.la.Aplicacion.pdf)
     * [**Video de demostracion de Proyecto - API + Procesos asíncronos y Colecciones en Postman, Arquitectura y Análisis de Capacidad**](https://www.youtube.com/watch?v=IJIeDC9ll08)
* **Análisis de Capacidad**
     * [**Pagina Wiki E1 - Plan de Análisis de Capacidad**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki/Entrega-1:-An%C3%A1lisis-de-Capacidad)
     * [**E1 - Plan de Análisis de Capacidad.pdf**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/files/14971625/E1.-.Plan.de.Analisis.de.Capacidad.pdf)
     * [**Video de demostracion de Proyecto - API + Procesos asíncronos y Colecciones en Postman, Arquitectura y Análisis de Capacidad**](https://www.youtube.com/watch?v=IJIeDC9ll08)
* [**Manual de configuración del entorno de desarrollo y despliegue**](https://github.com/lesmesl/MISW-4203-Backend-Cloud/wiki/Manual-de-Configuraci%C3%B3n-del-Entorno-de-Desarrollo-y-Despliegue)
