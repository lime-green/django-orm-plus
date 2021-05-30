from django.db import models

from ._fetch_related import fetch_related
from ._strict_mode import StrictModeManager, StrictModeModelMixin, StrictModeQuerySet


class FetchRelatedQuerySet(StrictModeQuerySet):
    def fetch_related(self, *fields):
        return fetch_related(self, fields)


class FetchRelatedManager(
    StrictModeManager, models.manager.BaseManager.from_queryset(FetchRelatedQuerySet)
):
    _queryset_class = FetchRelatedQuerySet


class FetchRelatedModelMixin(StrictModeModelMixin):
    objects = FetchRelatedManager()

    class Meta:
        abstract = True
