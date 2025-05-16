from rest_framework import serializers
from .models import MediaFileVideo, MediaFileImage, Document

class MediaFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFileVideo
        fields = "__all__"


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFileImage
        fields = ['id',  'thumbnail']


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'file', 'uploaded_at', 'self_id']

    def validate_file(self, value):
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Fichier trop lourd (max 10 Mo)")
        if not value.name.endswith('.pdf'):
            raise serializers.ValidationError("Le fichier doit être un PDF")
        return value
    
    def validate_self_id(self, value):
        if not value:
            raise serializers.ValidationError("l'id du proprietaire est requis")
        return value

