from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Garant
from .serializers import (
    GarantCreateSerializer,
    GarantDetailSerializer,
    GarantUpdateSerializer,
)

def _abs_url(request, rel_path):
    if not rel_path:
        return None
    return request.build_absolute_uri(f"{settings.MEDIA_URL}{rel_path}")

class GarantListCreateView(generics.ListCreateAPIView):
    queryset = Garant.objects.all().order_by("-created")
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # accept files & JSON

    def get_serializer_class(self):
        return GarantCreateSerializer if self.request.method == "POST" else GarantDetailSerializer

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        garant = ser.save()

        return Response({
            "id": garant.id,
            "nom": garant.nom,
            "prenom": garant.prenom,
            "tel": garant.tel,
            "ville": garant.ville,
            "quartier": garant.quartier,
            "profession": garant.profession,
            "photo": garant.photo,
            "photo_url": _abs_url(request, garant.photo),
            "plan_localisation": garant.plan_localisation,
            "plan_localisation_url": _abs_url(request, garant.plan_localisation),
            "cni_recto": garant.cni_recto,
            "cni_recto_url": _abs_url(request, garant.cni_recto),
            "cni_verso": garant.cni_verso,
            "cni_verso_url": _abs_url(request, garant.cni_verso),
            "justif_activite": garant.justif_activite,
            "justif_activite_url": _abs_url(request, garant.justif_activite),
            "created": garant.created,
            "updated": garant.updated,
        }, status=status.HTTP_201_CREATED)


class GarantDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Garant.objects.all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # enable file updates in PATCH/PUT

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return GarantUpdateSerializer
        return GarantDetailSerializer

    # optional: return file absolute URLs on GET retrieve
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = GarantDetailSerializer(instance).data
        data.update({
            "photo_url": _abs_url(request, instance.photo),
            "plan_localisation_url": _abs_url(request, instance.plan_localisation),
            "cni_recto_url": _abs_url(request, instance.cni_recto),
            "cni_verso_url": _abs_url(request, instance.cni_verso),
            "justif_activite_url": _abs_url(request, instance.justif_activite),
        })
        return Response(data)
