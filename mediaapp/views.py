import os
from django.http import JsonResponse
from rest_framework.decorators import api_view, parser_classes
from django.core.files.storage import default_storage
from .models import MediaFileVideo, MediaFileImage, Document
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import shutil

from .utils import verify_token

from .serializers import ( ImageSerializer, DocumentSerializer )

from django.conf import settings

UPLOAD_DIR = os.path.join(settings.BASE_DIR, "media", "uploads", "videos") 

os.makedirs(UPLOAD_DIR, exist_ok=True)  

def save_chunk(file_id, chunk_number, file):
    chunk_path = os.path.join(UPLOAD_DIR, f"{file_id}_chunk{chunk_number}")
    with default_storage.open(chunk_path, "wb") as destination:
        for chunk in file.chunks():
            destination.write(chunk)

def merge_chunks(file_id, total_chunks, file_name):
    file_path = os.path.join(UPLOAD_DIR, file_name)
    with open(file_path, "wb") as final_file:
        for i in range(total_chunks):
            chunk_path = os.path.join(UPLOAD_DIR, f"{file_id}_chunk{i}")
            with open(chunk_path, "rb") as chunk_file:
                final_file.write(chunk_file.read())
            os.remove(chunk_path)  # Supprimer le chunk après fusion
    return file_path

@csrf_exempt 
def upload_chunk(request):
    if request.method == "POST":
        file_id = request.POST["file_id"]
        chunk_number = int(request.POST["chunk_number"])
        total_chunks = int(request.POST["total_chunks"])
        file = request.FILES["file"]

        self_id = request.POST["self_id"]
        token = request.POST["token"]

        if not token:
            return JsonResponse({"error": "Le token est requis"}, status=400)

        valid = verify_token(token)

        if not valid:
            return JsonResponse({"error": "Token Invalide"}, status=400)

        # Sauvegarde du chunk
        save_chunk(file_id, chunk_number, file)

        # Si c'est le dernier chunk, on fusionne et on crée l'objet MediaFileVideo
        if chunk_number == total_chunks - 1:
            file_name = request.POST["file_name"]
            file_path = merge_chunks(file_id, total_chunks, file_name)

            # Crée un objet MediaFileVideo et associe le fichier
            media_file = MediaFileVideo(file=file_path)
            media_file.self_id = self_id
            
            media_file.save()  # Sauvegarder l'objet dans la base de données

            # Extraire les métadonnées de la vidéo
            media_file.extract_metadata()

            # Optionnel : Segmenter la vidéo en HLS après avoir extrait les métadonnées
            media_file.segment_video()

            return JsonResponse({
                "message": "Upload terminé et vidéo traitée",
                "file_url": request.build_absolute_uri(f"/{media_file.file.url}"),
                "self_id": media_file.self_id
            })

        return JsonResponse({"message": "Chunk reçu", "chunk": chunk_number})

    return JsonResponse({"error": "Méthode non autorisée"}, status=400)


def get_hls_playlist(request, self_id):

    # token = request.POST["token"]

    # if not token:
    #     return JsonResponse({"error": "Le token est requis"}, status=400)

    # valid = verify_token(token)

    # if not valid:
    #     return JsonResponse({"error": "Token Invalide"}, status=400)

    # Récupérer l'objet MediaFileVideo en utilisant l'ID
    # video = get_object_or_404(MediaFileVideo, id=video_id)
    # Récupérer l'objet MediaFileVideo en utilisant l'ID de l'objet propriétaire
    video = MediaFileVideo.objects.filter(self_id=self_id).first()

    # Vérifier que le fichier HLS existe
    if not video.hls_playlist:
        return JsonResponse({"error": "Playlist HLS non trouvée"}, status=404)
    # Construire une URL absolue

    # hls_playlist_url = request.build_absolute_uri(video.hls_playlist)
    hls_playlist_url = request.build_absolute_uri(f"/{video.hls_playlist}")

    # Retourner le chemin relatif de la playlist
    return JsonResponse({"self_id": video.self_id, "playlist": hls_playlist_url})



@csrf_exempt 
def upload_img(request):
    if request.method == "POST":
        image_file = request.FILES["image_file"]
        self_id = request.POST["self_id"]

        token = request.POST["token"]

        if not token:
            return JsonResponse({"error": "Le token est requis"}, status=400)

        valid = verify_token(token)

        if not valid:
            return JsonResponse({"error": "Token Invalide"}, status=400)

        image_instance = MediaFileImage(file=image_file)
        image_instance.self_id = self_id
        image_instance.save()

        return JsonResponse({
            "id": image_instance.id,
            "thumbnail": image_instance.thumbnail.url, 
            "self_id": image_instance.self_id 
        }, status=201)

    return JsonResponse({"error": "Méthode non autorisée"}, status=400)


def get_image_thumbnail(request, self_id):

    # token = request.POST["token"]

    # if not token:
    #     return JsonResponse({"error": "Le token est requis"}, status=400)

    # valid = verify_token(token)

    # if not valid:
    #     return JsonResponse({"error": "Token Invalide"}, status=400)

    # image = get_object_or_404(MediaFileImage, id=image_id)
    # Récupérer l'objet MediaFileImage en utilisant l'ID de l'objet propriétaire
    image = MediaFileImage.objects.filter(self_id=self_id).first()

    complete_image = request.GET.get("complete_image", "false").lower()

    serializer = ImageSerializer(image)

    # Retourner le chemin relatif au thumnail

    if complete_image == "true" :
        return JsonResponse({
            "id": image.id,
            "image": request.build_absolute_uri(image.file.url),
            "self_id": image.self_id,
        }, status=200)
    else:
        return JsonResponse({
            "id": image.id,
            "thumbnail": request.build_absolute_uri(image.thumbnail.url),
            "self_id": image.self_id,
        }, status=200)
    
def get_pdf_url(request, self_id):

    # Récupérer l'objet MediaFileImage en utilisant l'ID de l'objet propriétaire
    pdf_instance = Document.objects.filter(self_id=self_id).first()

    return JsonResponse({
        "id": pdf_instance.id,
        "file_url": request.build_absolute_uri(pdf_instance.file.url),
        "self_id": pdf_instance.self_id,
    }, status=200)
    
# @csrf_exempt 
# @parser_classes([MultiPartParser])
# def upload_file(request):
#     serializer = DocumentSerializer(data=request.data)
#     if serializer.is_valid():
#         doc = serializer.save()
        # return JsonResponse({
        #     "id": doc.id,
        #     "file_url": request.build_absolute_uri(doc.file.url)
        # }, status=status.HTTP_201_CREATED)
#     return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_file(request):

    token = request.POST["token"]
    self_id = request.POST["self_id"]
    file = request.FILES["file"]

    if not token:
        return JsonResponse({"error": "Le token est requis"}, status=400)

    valid = verify_token(token)

    if not valid:
        return JsonResponse({"error": "Token Invalide"}, status=400)
    
    pdf_instance = Document(file=file)
    pdf_instance.self_id = self_id
    pdf_instance.save()

    return JsonResponse({
        "id": pdf_instance.id,
        "file_url": request.build_absolute_uri(pdf_instance.file.url),
        "self_id": pdf_instance.self_id,
    }, status=status.HTTP_201_CREATED)

    # serializer = DocumentSerializer(data=request.data)
    # if serializer.is_valid():
    #     doc = serializer.save()
    #     return JsonResponse({
    #         "id": doc.id,
    #         "file_url": request.build_absolute_uri(doc.file.url),
    #         "self_id": doc.self_id,
    #     }, status=status.HTTP_201_CREATED)
    #     # return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
    # return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt 
def delete_file(request, file_type, self_id):

    if file_type == "video":
        try:
            file_instance = MediaFileVideo.objects.get(self_id=self_id)
        except MediaFileVideo.DoesNotExist:
            return JsonResponse({"error": "Le fichier n'existe pas."}, status=404)
    
    if file_type == "image":
        try:
            file_instance = MediaFileImage.objects.get(self_id=self_id)
        except MediaFileImage.DoesNotExist:
            return JsonResponse({"error": "Le fichier n'existe pas."}, status=404)
    
    if file_type == "pdf":
        try:
            file_instance = Document.objects.get(self_id=self_id)
        except Document.DoesNotExist:
            return JsonResponse({"error": "Le fichier n'existe pas."}, status=404)

    file_path = os.path.join(settings.MEDIA_ROOT, file_instance.file.name)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            return JsonResponse({"error": f"Erreur lors de la suppression du fichier : {str(e)}"}, status=500)
    
    if file_type == "video":
        hls_file = file_instance.hls_playlist

        # Diviser le chemin en segments
        segments = hls_file.split("/")

        # Ignorer le premier segment ("media") et reconstruire le chemin
        folder_path_parent = "/".join(segments[1:])

        # print("folder_path_parent", folder_path_parent)

        file_path_hls = os.path.join(settings.MEDIA_ROOT, folder_path_parent)

        # print("file_path_hls", file_path_hls)

        # Extraire le chemin du dossier parent
        folder_path = os.path.dirname(file_path_hls)
        
        # print("folder_path", folder_path)

        if os.path.exists(folder_path):
            try:
                # Supprimer le dossier et tout son contenu
                shutil.rmtree(folder_path)
            except Exception as e:
                return JsonResponse({"error": f"Erreur lors de la suppression du hls : {str(e)} file_hls : {file_path_hls}"}, status=500)
    

    file_instance.delete()
    return JsonResponse({"message": "Le fichier a été supprimé avec succès."}, status=200)