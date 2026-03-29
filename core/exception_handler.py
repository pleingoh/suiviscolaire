from django.utils.translation import gettext as _
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    if response.status_code == 401 and isinstance(response.data, dict) and response.data.get("detail"):
        response.data["detail"] = _("Informations d'authentification manquantes.")

    return response
