from django.db import models

from ._bulk import bulk_update_or_create as bulk_update_or_create_
from ._fetch_related import fetch_related
from ._strict_mode import StrictModeManager, StrictModeModelMixin, StrictModeQuerySet


class ORMPlusQuerySet(StrictModeQuerySet):
    def fetch_related(self, *fields):
        return fetch_related(self, fields)

    def bulk_update_or_create(
        self, objs, lookup_fields, update_fields, batch_size=None
    ):
        if objs:
            assert self.model == objs[0]._meta.model

        return bulk_update_or_create_(
            self, objs, lookup_fields, update_fields, batch_size
        )

    bulk_update_or_create.alters_data = True


class ORMPlusManager(
    models.manager.BaseManager.from_queryset(ORMPlusQuerySet), StrictModeManager
):
    pass


class ORMPlusModelMixin(StrictModeModelMixin):
    objects = ORMPlusManager()

    class Meta:
        abstract = True
