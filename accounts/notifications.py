from django.conf import settings
from django.core.mail import send_mail


def has_real_email_delivery():
    return settings.EMAIL_BACKEND not in {
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
        "django.core.mail.backends.dummy.EmailBackend",
    }


def send_school_admin_welcome_email(*, school_name, recipient_email, full_name, password):
    subject = "Suivi scolaire"
    message = (
        f"Bonjour {full_name},\n\n"
        f'Votre compte administrateur pour l\'ecole "{school_name}" a ete cree avec succes. '
        f'Voici votre mot de passe initial "{password}". '
        "Nous vous recommandons de le modifier lors de votre premiere connexion.\n\n"
        "Suivi scolaire"
    )
    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=False,
    )
