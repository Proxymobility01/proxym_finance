import os
from django.utils import timezone
from django.core.files.storage import default_storage
from django.utils.text import slugify
from django.utils.timezone import now
from rest_framework import serializers

from .models import Garant

# ---- helper to save uploads to MEDIA_ROOT/subdir and return the relative path
def _save_upload(upload, subdir="garants"):
    base, ext = os.path.splitext(upload.name or "")
    filename = f"{slugify(base or 'file')}-{int(now().timestamp())}{ext.lower()}"
    path = os.path.join(subdir, filename)
    saved_path = default_storage.save(path, upload)
    return saved_path  # relative to MEDIA_ROOT


class GarantDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Garant
        fields = [
            "id", "nom", "prenom", "tel", "ville", "quartier", "profession",
            "photo", "plan_localisation", "cni_recto", "cni_verso",
            "justif_activite", "created", "updated"
        ]


class GarantCreateSerializer(serializers.Serializer):
    # text
    nom = serializers.CharField()
    prenom = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tel = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    ville = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    quartier = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    profession = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # files (optional)
    photo = serializers.FileField(required=False, allow_null=True)
    plan_localisation = serializers.FileField(required=False, allow_null=True)
    cni_recto = serializers.FileField(required=False, allow_null=True)
    cni_verso = serializers.FileField(required=False, allow_null=True)
    justif_activite = serializers.FileField(required=False, allow_null=True)

    def create(self, validated_data):
        # pull files
        file_fields = {}
        for key in ["photo", "plan_localisation", "cni_recto", "cni_verso", "justif_activite"]:
            upload = validated_data.pop(key, None)
            if upload:
                file_fields[key] = _save_upload(upload)

        now_ts = timezone.now()
        g = Garant.objects.create(
            created=now_ts,
            updated=now_ts,
            **validated_data,
            **file_fields
        )
        return g


class GarantUpdateSerializer(serializers.Serializer):
    # all optional for PATCH; for PUT you should send everything you care to keep
    nom = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    prenom = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tel = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    ville = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    quartier = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    profession = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # allow file replacement
    photo = serializers.FileField(required=False, allow_null=True)
    plan_localisation = serializers.FileField(required=False, allow_null=True)
    cni_recto = serializers.FileField(required=False, allow_null=True)
    cni_verso = serializers.FileField(required=False, allow_null=True)
    justif_activite = serializers.FileField(required=False, allow_null=True)

    def update(self, instance: Garant, validated_data):
        # file fields first (if provided)
        for key in ["photo", "plan_localisation", "cni_recto", "cni_verso", "justif_activite"]:
            upload = validated_data.pop(key, None)
            if upload is not None:
                setattr(instance, key, _save_upload(upload))

        # text fields
        for k, v in validated_data.items():
            setattr(instance, k, v)

        instance.updated = timezone.now()
        # persist only updated fields + updated timestamp
        # NOTE: for simplicity we update all model fields commonly used
        instance.save()
        return instance
