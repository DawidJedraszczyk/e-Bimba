from .serializers import FeedbackSerializer
from rest_framework.generics import CreateAPIView
from .models import Feedback


class FeedbackCreateApiView(CreateAPIView):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer