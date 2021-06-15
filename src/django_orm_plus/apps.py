from django.apps import AppConfig

from ._config import config


def auto_add_mixin_to_model(model):
    from .mixins import ORMPlusManager, ORMPlusModelMixin, ORMPlusQuerySet

    if not config.auto_add_model_mixin:
        return

    if not issubclass(model, ORMPlusModelMixin):
        queryset_class = type(
            ORMPlusQuerySet.__name__,
            (ORMPlusQuerySet, model._default_manager._queryset_class)
            + model._default_manager._queryset_class.__bases__,
            {},
        )
        manager = type(
            ORMPlusManager.__name__,
            (ORMPlusManager, model._default_manager.__class__)
            + model._default_manager.__class__.__bases__,
            {
                "_queryset_class": queryset_class,
            },
        )()
        model._meta.local_managers = [
            m for m in model._meta.local_managers if m.name != "objects"
        ]
        model.__bases__ = (ORMPlusModelMixin,) + model.__bases__
        manager.contribute_to_class(model, "objects")


class DjangoORMPlusAppConfig(AppConfig):
    name = "django_orm_plus"

    def ready(self):
        from django.apps import apps

        for model in apps.get_models():
            auto_add_mixin_to_model(model)
