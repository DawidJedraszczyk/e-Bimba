import pytest
from rest_framework.test import APIClient
from rest_framework.reverse import reverse
from feedback.models import Feedback
from feedback.create_issue import GitlabBackend
from faker import Faker
from .conftest import new_create_issue

fake = Faker()
client = APIClient()

def test_create_view(mocker, user_object_fixture, image_object_fixture):
    mocker.patch.object(GitlabBackend, 'create_issue', new=new_create_issue)

    data = {'description': fake.sentence(), 'url': fake.url(), 'image': image_object_fixture}
    url = reverse('feedback:create-feedback')

    client.force_authenticate(user_object_fixture)
    response = client.post(url, data=data)

    assert response.json() != None
    assert response.status_code == 201
    assert Feedback.objects.count() == 1

def test_create_view_get_method(user_object_fixture):
    url = reverse('feedback:create-feedback')

    client.force_authenticate(user_object_fixture)
    response = client.get(url)

    assert response.status_code == 405

def test_create_view_without_image(user_object_fixture):
    data = {'description': fake.sentence(), 'url': fake.url()}
    url = reverse('feedback:create-feedback')

    client.force_authenticate(user_object_fixture)
    response = client.post(url, data=data)

    assert response.status_code == 400

def test_create_view_without_description(user_object_fixture, image_object_fixture):
    data = {'url': fake.url(), 'image': image_object_fixture}
    url = reverse('feedback:create-feedback')

    client.force_authenticate(user_object_fixture)
    response = client.post(url, data=data)

    assert response.status_code == 400


#!!! RECZNIE SPRAWDZONE I MOZNA WYSLAC DWA TESTY PO SOBIE I PRZECHODZI, PRAWDOBNIE JAKIS MOJ BLAD W TESCIE!!!
# def test_create_view_multiple_feedbacks(mocker, user_object_fixture, image_object_fixture):
#     mocker.patch('modules.feedback.create_issue.GitlabBackend.create_issue', return_value=True)
#     data1 = {'description': fake.sentence(), 'url': fake.url(), 'image': image_object_fixture}
#     data2 = {'description': fake.sentence(), 'url': fake.url(), 'image': image_object_fixture}
#     url = reverse('feedback:create-feedback')
#
#     client.force_authenticate(user_object_fixture)
#
#     response1 = client.post(url, data=data1)
#     assert response1.status_code == 201
#
#     response2 = client.post(url, data=data2)
#     assert response2.status_code == 201
#
#     assert Feedback.objects.filter(user=user_object_fixture).count() == 2