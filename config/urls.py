"""
URL configuration for ecabinet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Interface d'administration Django par défaut
    path('admin/', admin.site.urls),     # Utilise la méthode sécurisée de récupération

    path("__reload__/", include("django_browser_reload.urls")),

    # 1. Page d'accueil / Dashboard principal
    path('', include('dashboard.urls')),
    
    # 2. Application Client
    path('clients/', include('client.urls')),
    
    # 3. Application Dossier
    path('dossiers/', include('dossier.urls')),
    
    # 4. Application Agenda
    path('agenda/', include('agenda.urls')),

    # 5. Application Facturation
    path('facturation/', include('facturation.urls')),
    
    # 5. Application Finance
    #path('facturation/', include('facturation.urls')),
    
    # 6. Application Documents / GED
    path('documents/', include('documents.urls')),
    
    # 7. Portail Extranet
    path('portail/', include('portal.urls')),

    # 2. Application Utilisateur
    #path('utilisateur/', include('authentication.urls')),
    path('utilisateur/', include('apps.authentication.urls')),
]
