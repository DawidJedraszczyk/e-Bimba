from django.conf import settings

def feedback_on(request):
    return {
        'FEEDBACK_ON': settings.FEEDBACK_ON,
    }