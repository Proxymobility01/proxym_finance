from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import  IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Garant
from .serializers import (
    GarantCreateSerializer,
    GarantDetailSerializer,

)

def _abs_url(request, rel_path):
    if not rel_path:
        return None
    return request.build_absolute_uri(f"{settings.MEDIA_URL}{rel_path}")

class GarantListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
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

