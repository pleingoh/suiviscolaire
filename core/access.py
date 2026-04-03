from rest_framework.exceptions import PermissionDenied


def is_global_admin(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def get_user_school(user):
    return getattr(user, "school", None)


def ensure_user_school(user):
    school = get_user_school(user)
    if is_global_admin(user):
        return school
    if school is None:
        raise PermissionDenied("Aucune ecole n'est attribuee a cet utilisateur.")
    return school


def ensure_same_school(user, school):
    if is_global_admin(user):
        return
    user_school = ensure_user_school(user)
    if school != user_school:
        raise PermissionDenied("Acces refuse a une autre ecole.")
