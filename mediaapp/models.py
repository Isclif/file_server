from django.db import models
from PIL import Image
import os
import imageio
import uuid

import subprocess
import json
import threading


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='uploads/docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    self_id = models.UUIDField(blank=True, null=True, editable=False)

    def __str__(self):
        return self.file.name

class MediaFileImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to="uploads/images/")
    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True, null=True)
    self_id = models.UUIDField( blank=True, null=True, editable=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.file and self.file.name.endswith(("jpg", "jpeg", "png")):
            self.generate_thumbnail()

    def generate_thumbnail(self):
        """Génère un thumbnail de 200x200 px"""
        img = Image.open(self.file.path)
        img.thumbnail((200, 200))

        # Vérifier si l'image est en mode RGBA et la convertir en RGB
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # thumbnail_path = f"thumbnails/{os.path.basename(self.file.name)}"
        # img.save(os.path.join("media", thumbnail_path))

        # Définir le chemin du thumbnail
        thumbnail_path = f"thumbnails/thumbnail_{self.id}.jpg"

        # Créer les dossiers nécessaires si ils n'existent pas
        os.makedirs(os.path.join("media", "thumbnails"), exist_ok=True)

        img.save(os.path.join("media", thumbnail_path))


        self.thumbnail = thumbnail_path

        super().save()

    def __str__(self):
        return self.file.name

class MediaFileVideo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to="uploads/videos/")
    duration = models.FloatField(blank=True, null=True)
    format = models.CharField(max_length=100, blank=True, null=True)
    resolution = models.CharField(max_length=50, blank=True, null=True)
    hls_playlist = models.CharField(max_length=5000, blank=True, null=True)
    self_id = models.UUIDField( blank=True, null=True, editable=False)

    def extract_metadata(self):
        """Récupère les métadonnées de la vidéo"""
        file_path = self.file.path
        print(file_path)
        # probe = ffmpeg.probe(file_path)

        reader = imageio.get_reader(file_path)
        video_detail = reader.get_meta_data()

        print("video_detail", video_detail)
        print("fps", round(video_detail['fps']))

        resolution = video_detail.get("size", "")

        _, ext = os.path.splitext(file_path)

        print("this is the extension", ext)

        width, height = resolution
        
        self.duration = float(video_detail.get("duration", 0))
        self.resolution = f"{width}x{height}px"
        self.format = ext
        
        # print("videos stream", video_streams)

        super().save()
    
    def detect_codecs(self, file_path):
        """
        Détecte les codecs vidéo et audio d'un fichier à l'aide de FFmpeg.
        Retourne un dictionnaire contenant les codecs.
        """
        
        command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "stream=codec_name,codec_type",
            "-of", "json",
            file_path
        ]

        print("file_path:", file_path)

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True
            )
            streams = json.loads(result.stdout)["streams"]
            
            # Afficher les résultats
            # print(f"streams : {streams}")

            video_codec = None
            audio_codec = None

            for stream in streams:
                if stream.get("codec_type") == "video":
                    video_codec = stream.get("codec_name")
                elif stream.get("codec_type") == "audio":
                    audio_codec = stream.get("codec_name")
            
            # Afficher les résultats
            # print(f"Codec vidéo : {video_codec}")
            # print(f"Codec audio : {audio_codec}")

            return {"video": video_codec, "audio": audio_codec}
        except Exception as e:
            print("Erreur lors de la détection des codecs :", e)
            raise


    def segment_video(self):
        """Convertit la vidéo en HLS"""
        file_path = self.file.path

        print("self.file.path :", file_path)
        
        # Dossier de sortie pour les segments HLS
        output_folder = os.path.join("media", "hls", os.path.splitext(os.path.basename(file_path))[0])
        os.makedirs(output_folder, exist_ok=True)

        # Fichier de playlist HLS
        output_playlist = os.path.join(output_folder, "index.m3u8")

        # Détecter les codecs de la vidéo
        codecs = self.detect_codecs(file_path)
        video_codec = codecs.get("video")
        audio_codec = codecs.get("audio")

        # print("codecs", codecs)
        
        print("video_codec_option", video_codec)
        print("audio_codec_option", audio_codec)

        # Déterminer si nous devons réencoder ou copier les flux
        # video_codec_option = "copy" if video_codec == "h264" else "libx264"
        # audio_codec_option = "copy" if audio_codec == "aac" else "aac"

        # print("video_codec_option", video_codec_option)
        # print("audio_codec_option", audio_codec_option)

        # Codecs supportés par HLS
        supported_video_codecs = ["h264", "hevc"]
        supported_audio_codecs = ["aac", "mp3"]

        # Déterminer si nous devons réencoder ou copier les flux
        video_codec_option = "copy" if video_codec in supported_video_codecs else "libx264"
        audio_codec_option = "copy" if audio_codec in supported_audio_codecs else "aac"
        
        # Commande pour segmenter la vidéo en HLS
        command = [
            "ffmpeg", 
            "-i", file_path,
            # "-codec:v", "copy",  # Copier le codec vidéo sans re-encodage
            # "-codec:a", "copy",  # Copier le codec audio sans re-encodage
            "-c:v", video_codec_option,  # Réencoder la vidéo en H.264 ou copier
            "-c:a", audio_codec_option,  # Réencoder l'audio en AAC ou copier
            "-codec:s", "webvtt",  # Convertir les sous-titres en WebVTT 
            "-start_number", "0",
            "-hls_time", "10", 
            "-hls_list_size", "0", 
            "-f", "hls", 
            output_playlist
        ]
        
        try:
            print(f"Segmentation en cours... Video codec: {video_codec_option}, Audio codec: {audio_codec_option}")

            # Exécution de la commande
            def process_video():
                subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            # Exécuter le traitement dans un thread séparé
            threading.Thread(target=process_video).start()  

            # print("Sortie FFmpeg :", result.stdout.decode())
        except subprocess.CalledProcessError as e:
            print("Erreur lors de la segmentation de la vidéo :", e.stderr.decode())
            raise

        # Enregistrer le chemin relatif de la playlist HLS
        first_hls_playlist = output_playlist.replace("media/", "")  # Stocke le chemin relatif

        self.hls_playlist = first_hls_playlist.replace("\\", "/")  # modifier les slashes

        super().save()
        


    def __str__(self):
        return self.file.name
