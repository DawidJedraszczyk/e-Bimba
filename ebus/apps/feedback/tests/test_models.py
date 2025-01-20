import pytest
from feedback.models import Feedback
from faker import Faker
from django.core.exceptions import ValidationError
from feedback.create_issue import GitlabBackend
from .conftest import new_create_issue

fake = Faker()

@pytest.fixture
def feedback_object_fixture(mocker, db, user_object_fixture, image_object_fixture): # db to fikstura od pytest-django, zapewnia to co pytest.mark.db
    mocker.patch.object(GitlabBackend, 'create_issue', new=new_create_issue)

    feedback = Feedback.objects.create(
        publication_datetime=fake.date_time(),
        description=fake.sentence(),
        image= image_object_fixture,
        url=fake.url(),
        user= user_object_fixture,
    )
    return feedback

def test_create_feedback(feedback_object_fixture):
    feedback = feedback_object_fixture
    assert Feedback.objects.count() == 1
    assert isinstance(feedback, Feedback)
    assert feedback.processed

def test_process(mocker, feedback_object_fixture):
    mocker.patch.object(GitlabBackend, 'create_issue', new=new_create_issue)

    success = feedback_object_fixture.process()
    assert success
    assert feedback_object_fixture.processed

def test_creating_without_description(feedback_object_fixture):
    feedback_object_fixture.description = None
    with pytest.raises(ValidationError):
        feedback_object_fixture.full_clean()

def test_creating_without_image(feedback_object_fixture):
    feedback_object_fixture.image = None
    with pytest.raises(ValidationError):
        feedback_object_fixture.full_clean()