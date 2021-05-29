from contextlib import contextmanager

from django.db import models
from django.utils.functional import cached_property


class RelatedObjectNeedsExplicitFetch(Exception):
    def __init__(self, model_name, field_name):
        super().__init__(f"{model_name}.{field_name} must be explicitly fetched")


class QueryModifiedAfterFetch(Exception):
    def __init__(self, model_name):
        super().__init__(
            f"The query for {model_name} was modified after the results were fetched"
        )


class AutoFetchContainer:
    def __init__(self):
        self.verify_queryset_is_prefetched = None
        self.root = None
        self._is_prefetching = False
        self.strict_mode = False

    def clone(self):
        return self.clone_to(self.__class__())

    def add_potential_root(self, other):
        if not self.root:
            self.root = other

    def clone_to(self, other):
        other.verify_queryset_is_prefetched = self.verify_queryset_is_prefetched
        other.strict_mode = self.strict_mode
        other.root = self.root
        return other

    def enable_strict_mode(self):
        self.strict_mode = True

    def is_prefetching(self):
        if self.root:
            return self.root.is_prefetching()
        return self._is_prefetching

    @contextmanager
    def wrap_prefetch(self):
        self._is_prefetching = True

        try:
            yield
        finally:
            self._is_prefetching = False


class StrictModeIterable(models.query.ModelIterable):
    def __iter__(self):
        qs_autofetch = getattr(self.queryset, "_autofetch", None)

        for obj in super().__iter__():
            if qs_autofetch and qs_autofetch.strict_mode:
                obj._autofetch = qs_autofetch.clone()
                obj._autofetch.add_potential_root(qs_autofetch)
            yield obj


class StrictModeQuerySet(models.QuerySet):
    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)

        self._autofetch = AutoFetchContainer()
        self._iterable_class = StrictModeIterable

    def _prefetch_related_objects(self):
        with self._autofetch.wrap_prefetch():
            super()._prefetch_related_objects()

    def _clone(self):
        if self._autofetch.strict_mode and self._result_cache is not None:
            raise QueryModifiedAfterFetch(self.model.__name__)

        qs = super()._clone()
        self._autofetch.clone_to(qs._autofetch)
        return qs

    def strict(self):
        qs = self._chain()
        qs._autofetch.enable_strict_mode()
        return qs

    def _fetch_all(self):
        if (
            self._autofetch.strict_mode
            and self._autofetch.verify_queryset_is_prefetched
        ):
            self._autofetch.verify_queryset_is_prefetched()

        super()._fetch_all()


class StrictModeManager(models.manager.BaseManager.from_queryset(StrictModeQuerySet)):
    def __init__(self):
        super().__init__()
        self._autofetch = AutoFetchContainer()

    def get_queryset(self):
        qs = super().get_queryset()
        self._autofetch.clone_to(qs._autofetch)
        return qs


class StrictModeModelMixin(models.Model):
    objects = StrictModeManager()

    @cached_property
    def __get_fields(self):
        return {
            field.get_accessor_name()
            if hasattr(field, "get_accessor_name")
            else field.name
            for field in self._meta.get_fields()
        }

    def __getattribute__(self, item):
        if (
            not item.startswith("_")
            and hasattr(self, "_autofetch")
            and self._autofetch.strict_mode
            and item in self.__get_fields
        ):
            descriptor = getattr(self.__class__, item)

            if isinstance(descriptor, models.query_utils.DeferredAttribute):
                return super().__getattribute__(item)

            field = descriptor.field
            field_name = item

            if hasattr(descriptor, "is_cached"):
                if self._autofetch.strict_mode:
                    if not descriptor.is_cached(self):
                        raise RelatedObjectNeedsExplicitFetch(
                            self.__class__.__name__,
                            field_name,
                        )
                    ret = super().__getattribute__(item)
                    ret._autofetch = self._autofetch.clone()
                    ret._autofetch.add_potential_root(self._autofetch)
                    return ret
            elif field.many_to_one or field.many_to_many:

                def check_is_prefetched():
                    # If the root queryset is prefetching, then the
                    # prefetched_objects_cache hasn't been built yet,
                    # and it needs to perform the necessary queries to do so
                    if self._autofetch.is_prefetching():
                        return

                    if field_name not in getattr(self, "_prefetched_objects_cache", {}):
                        raise RelatedObjectNeedsExplicitFetch(
                            self.__class__.__name__,
                            field_name,
                        )

                ret = super().__getattribute__(item)
                ret._autofetch = self._autofetch.clone()
                ret._autofetch.add_potential_root(self._autofetch)
                ret._autofetch.verify_queryset_is_prefetched = check_is_prefetched
                return ret
        return super().__getattribute__(item)

    class Meta:
        abstract = True
