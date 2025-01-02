from django.contrib.auth.models import User
from PIL import Image
from faker import Faker
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from django.test import RequestFactory
import pytest


fake = Faker()
factory = RequestFactory()

@pytest.fixture
def user_object_fixture(client, db): # db to fikstura od pytest-django, zapewnia to co pytest.mark.db
    name = fake.name().split()
    user = User.objects.create(
        first_name=''.join(name[:-1]),
        last_name=name[-1],
    )
    return user


@pytest.fixture
def image_object_fixture():
    image = Image.new('RGB', (100, 100))
    image_io = BytesIO()
    image.save(image_io, format='JPEG')
    image_file = SimpleUploadedFile("test_image.jpg", image_io.getvalue())
    return image_file


@pytest.fixture
def feedback_request(user_object_fixture):
    request = factory.get('/feedback/create')
    request.user = user_object_fixture
    return request

def new_create_issue(data):
    return True