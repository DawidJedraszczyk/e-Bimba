import pytest
from feedback.serializers import FeedbackSerializer
from faker import Faker
from django.test import RequestFactory


fake = Faker()
factory = RequestFactory()

def test_serializer_create(user_object_fixture, image_object_fixture, feedback_request):
    data = {'description': fake.sentence(), 'url': fake.url(), 'image': image_object_fixture}
    serializer = FeedbackSerializer(data=data, context={'request': feedback_request})
    serializer.is_valid()

    serialized_data = serializer.validated_data

    assert serializer.is_valid()
    assert user_object_fixture == serialized_data['user']
    assert image_object_fixture == serialized_data['image']
    assert data['url'] == serialized_data['url']
    assert data['description'] == serialized_data['description']

def test_serializer_create_without_description(user_object_fixture, image_object_fixture, feedback_request):
    feedback_data_without_description = {'description': None, 'url': fake.url(), 'image': image_object_fixture}

    serializer = FeedbackSerializer(data=feedback_data_without_description, context={'request': feedback_request})
    assert serializer.is_valid() == False

def test_serializer_create_without_image(user_object_fixture, feedback_request):
    feedback_data_without_image= {'description': fake.sentence(), 'url': fake.url(), 'image': None}

    serializer = FeedbackSerializer(data=feedback_data_without_image, context={'request': feedback_request})
    assert serializer.is_valid() == False

def test_serializer_create_without_url(user_object_fixture, image_object_fixture, feedback_request):
    feedback_data_without_url = {'description': fake.sentence(), 'url': None, 'image': image_object_fixture}

    serializer = FeedbackSerializer(data=feedback_data_without_url, context={'request': feedback_request})
    assert serializer.is_valid() == False

def test_serializer_create_without_user(user_object_fixture, image_object_fixture, feedback_request):
    feedback_data_without_user = {'description': fake.sentence(), 'url': fake.url(), 'image': image_object_fixture}

    request = factory.get('/feedback/create')
    request.user = None

    serializer = FeedbackSerializer(data=feedback_data_without_user, context={'request': request})
    assert serializer.is_valid() #Tutaj wychodzi True nie jestem pewien czy to dobrze