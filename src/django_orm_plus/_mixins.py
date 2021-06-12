from django.db import models

from ._bulk import bulk_update_or_create
from ._fetch_related import fetch_related
from ._strict_mode import StrictModeManager, StrictModeModelMixin, StrictModeQuerySet


class ORMPlusQuerySet(StrictModeQuerySet):
    def fetch_related(self, *fields):
        return fetch_related(self, fields)

    def bulk_update_or_create(
        self, objs, lookup_fields, update_fields, batch_size=None
    ):
        return bulk_update_or_create(
            self.model, objs, lookup_fields, update_fields, batch_size
        )


class ORMPlusManager(
    StrictModeManager, models.manager.BaseManager.from_queryset(ORMPlusQuerySet)
):
    _queryset_class = ORMPlusQuerySet


class ORMPlusModelMixin(StrictModeModelMixin):
    objects = ORMPlusManager()

    class Meta:
        abstract = True
