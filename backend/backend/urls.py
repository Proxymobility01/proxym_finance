
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/auth/", include('accounts.urls')),
    path("api/", include("garant.urls")),
    path("api/", include("contrat_chauffeur.urls")),
    path("api/", include("app_legacy.urls")),
    path("api/", include("paiement_lease.urls")),  
    path("api/", include("conge.urls")),
]



# DEV ONLY: serve uploaded files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)