from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Profile, DriverVerification
from .serializers import ProfileSerializer, DriverVerificationSerializer

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        if self.action == 'me':
            return Profile.objects.get_or_create(user=self.request.user)[0]
        return super().get_object()

    @action(detail=False, methods=['get', 'post', 'put'])
    def me(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        if request.method in ['POST', 'PUT']:
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def verification_status(self, request, pk=None):
        profile = self.get_object()
        verification, created = DriverVerification.objects.get_or_create(driver=profile)
        serializer = DriverVerificationSerializer(verification)
        return Response(serializer.data)
