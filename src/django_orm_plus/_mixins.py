from django.db import models

from ._fetch_related import fetch_related
from ._strict_mode import StrictModeManager, StrictModeModelMixin, StrictModeQuerySet


class ORMPlusQuerySet(StrictModeQuerySet):
    def fetch_related(self, *fields):
        return fetch_related(self, fields)


class ORMPlusManager(
    StrictModeManager, models.manager.BaseManager.from_queryset(ORMPlusQuerySet)
):
    _queryset_class = ORMPlusQuerySet


class ORMPlusModelMixin(StrictModeModelMixin):
    objects = ORMPlusManager()

    class Meta:
        abstract = True
