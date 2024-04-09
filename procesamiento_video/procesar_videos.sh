#!/bin/bash

# Verificar si FFmpeg está instalado
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg no está instalado. Instálalo con 'sudo apt-get install ffmpeg'."
    exit 1
fi

# Ruta del archivo de logo
logo_path="ruta/a/tus/logo.webp"

# Directorio de entrada y salida
input_dir="ruta/a/tus/videos/originales"
output_dir="ruta/a/tus/videos/procesados"

# Crear directorio de salida si no existe
mkdir -p "$output_dir"

# Iterar sobre los archivos de video en el directorio de entrada
for file in "$input_dir"/*; do
    filename=$(basename -- "$file")
    extension="${filename##*.}"
    filename_without_extension="${filename%.*}"

    # Nombre del archivo de salida
    output_filename="$output_dir/${filename_without_extension}_procesado.${extension}"

    # Comando FFmpeg para procesar el video
    ffmpeg -ignore_unknown -i "$file" \
-loop 1 -t 3 -i "$logo_path" \
-filter_complex "\
[1:v]fade=out:st=2:d=1:alpha=1,setpts=PTS-STARTPTS[logo]; \
[0:v][logo]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:format=auto, \
scale=trunc(oh*a/2)*2:360,crop=360:360,pad=640:360:(ow-iw)/2:(oh-ih)/2, \
trim=duration=20,setpts=PTS-STARTPTS[v]" \
-map "[v]" -map 0:a? -c:v libx264 -c:a copy -t 20 -y "$output_filename"


    echo "Video procesado: $output_filename"
done

echo "Proceso completado."

