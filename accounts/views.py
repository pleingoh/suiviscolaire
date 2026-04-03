from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "full_name": user.full_name,
                "phone": user.phone,
                "email": user.email,
                "role": user.role.code if user.role else None,
                "school": user.school_id,
                "school_id": user.school_id,
                "school_name": user.school.name if user.school else None,
                "is_global_admin": user.is_global_admin,
                "is_school_admin": user.is_school_admin,
            }
        )
