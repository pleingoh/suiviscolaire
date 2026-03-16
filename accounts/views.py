from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "full_name": user.full_name,
            "phone": user.phone,
            "email": user.email,
            "role": user.role.code if user.role else None
        })
