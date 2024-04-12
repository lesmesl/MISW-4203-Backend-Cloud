import subprocess

# Definir los nombres de los archivos y la escala
input_file = "drones.mp4"
recorte_video = "00:00:08"  # Duración del recorte en formato HH:MM:SS
scala = "1280:720"  # Resolución deseada del video
imagen_temp = "imagen_temp.mp4"
video_recortado = "recortado_20240412173213-1-drones.mp4"
video_escalado = "escalado_20240412173213-1-drones.mp4"
output_file = "videos-converted/procesado_20240412173213-1-drones.mp4"

# Comandos de ffmpeg para cada paso
comando_imagen = f'ffmpeg -y -loop 1 -i logo.png -t 1 -c:v libx264 -pix_fmt yuv420p -vf "scale={scala}" {imagen_temp}'
comando_recortado = f'ffmpeg -y -i {input_file} -ss 0 -t {recorte_video} -c:v copy -c:a copy {video_recortado}'
comando_escalado = f'ffmpeg -y -i {video_recortado} -vf scale={scala} {video_escalado}'
comando_unificar = f'ffmpeg -y -i {imagen_temp} -i {video_escalado} -i {imagen_temp} -filter_complex "[0:v] [1:v] [2:v] concat=n=3:v=1:a=1 [v]" -map "[v]" -preset ultrafast -strict -2 {output_file}'

# Ejecutar cada comando
subprocess.run(comando_imagen, shell=True)
subprocess.run(comando_recortado, shell=True)
subprocess.run(comando_escalado, shell=True)
subprocess.run(comando_unificar, shell=True)