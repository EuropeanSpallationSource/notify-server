import factory
from app import models


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.User
        sqlalchemy_session_persistence = "commit"

    username = factory.Faker("user_name")


class ServiceFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Service
        sqlalchemy_session_persistence = "commit"

    category = factory.Faker("sentence", nb_words=2)
    color = factory.Faker("color")
    owner = factory.Faker("name")


class NotificationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Notification
        sqlalchemy_session_persistence = "commit"

    title = factory.Faker("sentence", nb_words=4)
    subtitle = factory.Faker("sentence", nb_words=6)
    url = factory.Faker("url")
    service = factory.SubFactory(ServiceFactory)
