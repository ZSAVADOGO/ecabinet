# apps/core/middleware.py
from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404
from django.http import JsonResponse

URLS_EXEMPTEES = {
    'authentication:connexion',
    'authentication:mot_de_passe_oublie',
}
#PREFIXES_EXEMPTES = ('/static/', '/media/', '/admin/login/')
# apps/core/middleware.py
PREFIXES_EXEMPTES = ('/static/', '/media/', '/admin/login/', '/__reload__/')


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            chemin = request.path

            if not chemin.startswith(PREFIXES_EXEMPTES):
                nom_url = None
                try:
                    match = resolve(chemin)
                    nom_url = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
                except Resolver404:
                    pass

                if nom_url not in URLS_EXEMPTEES:
                    # Les appels AJAX/API doivent recevoir du JSON, pas une redirection HTML
                    # (sinon envoyerFormulaire()/chargerListe() plantent en tentant de parser
                    # une page de connexion comme si c'était du JSON).
                    if '/api/' in chemin:
                        return JsonResponse({"erreur": "Authentification requise."}, status=401)
                    return redirect(f"{reverse('authentication:connexion')}?next={chemin}")

        return self.get_response(request)