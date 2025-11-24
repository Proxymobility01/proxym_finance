import logging


from rest_framework import permissions, viewsets
from rest_framework.permissions import IsAuthenticated
from accounts.models import CustomUser
from accounts.serializers import UserLiteSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.select_related("role").all()
    serializer_class = UserLiteSerializer
    # authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]




class MeView(APIView):
    """
    Renvoie le profil de l'utilisateur local actuellement authentifié
    (identifié via le JWT de l'IdP).
    """
    permission_classes = [IsAuthenticated] # Seul un utilisateur connecté peut voir son profil

    def get(self, request):
        """
        Gère la requête GET.
        Le 'request.user' est fourni par votre "vigile" OIDCAuthentication.
        """
        # On utilise le même serializer que le UserViewSet
        serializer = UserLiteSerializer(request.user)
        return Response(serializer.data)
