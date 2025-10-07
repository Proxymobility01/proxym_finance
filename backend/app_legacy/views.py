# app_legacy/views.py
from rest_framework.permissions import  IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import fetch_association_summary, fetch_all_association_summaries


class AssociationSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request, pk: int):
        data = fetch_association_summary(pk)
        if not data:
            return Response({"detail": "Association not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(data, status=status.HTTP_200_OK)


class AssociationSummaryListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        data = fetch_all_association_summaries()
        return Response(data, status=status.HTTP_200_OK)
