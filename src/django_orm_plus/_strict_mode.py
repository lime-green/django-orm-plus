from contextlib import contextmanager

from django.db import models

from ._config import config
from ._util import get_fields_map_for_model


class StrictModeException(Exception):
    pass


class RelatedAttributeNeedsExplicitFetch(StrictModeException):
    def __init__(self, model_name, field_name):
        super().__init__(f"{model_name}.{field_name} must be explicitly fetched")


class RelatedObjectNeedsExplicitFetch(StrictModeException):
    def __init__(self, model_name, field_name):
        super().__init__(f"{model_name}.{field_name} must be explicitly fetched")


class QueryModifiedAfterFetch(StrictModeException):
    def __init__(self, model_name):
        super().__init__(
            f"The query for {model_name} was modified after the results were fetched"
        )


class StictModeContainer:
    def __init__(self):
        self.verify_queryset_is_prefetched = None
        self.prefetch_root = None
        self._is_prefetching = False
        self._strict_mode = False
        self._strict_mode_override = config.strict_mode_global_override

    def clone(self):
        return self.clone_to(self.__class__())

    def add_potential_prefetch_root(self, other):
        if not self.prefetch_root:
            self.prefetch_root = other

    def clone_to(self, other):
        other.verify_queryset_is_prefetched = self.verify_queryset_is_prefetched
        other.strict_mode = self.strict_mode
        other.prefetch_root = self.prefetch_root
        return other

    def enable_strict_mode(self):
        self.strict_mode = True

    def is_prefetching(self):
        if self.prefetch_root:
            return self.prefetch_root.is_prefetching()
        return self._is_prefetching

    @property
    def strict_mode(self):
        if self._strict_mode_override is not None:
            return self._strict_mode_override
        return self._strict_mode

    @strict_mode.setter
    def strict_mode(self, val):
        self._strict_mode = val

    @contextmanager
    def wrap_prefetch(self):
        self._is_prefetching = True

        try:
            yield
        finally:
            self._is_prefetching = False


class StrictModeIterable(models.query.ModelIterable):
    def __iter__(self):
        qs_strict_mode = getattr(self.queryset, "_strict_mode", None)

        for obj in super().__iter__():
            if qs_strict_mode and qs_strict_mode.strict_mode:
                obj._strict_mode = qs_strict_mode.clone()
                obj._strict_mode.add_potential_prefetch_root(qs_strict_mode)
            yield obj


class StrictModeQuerySet(models.QuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._strict_mode = StictModeContainer()
        self._iterable_class = StrictModeIterable

    def _prefetch_related_objects(self):
        with self._strict_mode.wrap_prefetch():
            super()._prefetch_related_objects()

    def _clone(self):
        if self._strict_mode.strict_mode and self._result_cache is not None:
            raise QueryModifiedAfterFetch(self.model.__name__)

        qs = super()._clone()
        self._strict_mode.clone_to(qs._strict_mode)
        return qs

    def strict(self):
        qs = self._chain()
        qs._strict_mode.enable_strict_mode()
        return qs

    def _fetch_all(self):
        if (
            self._strict_mode.strict_mode
            and self._strict_mode.verify_queryset_is_prefetched
        ):
            self._strict_mode.verify_queryset_is_prefetched()

        super()._fetch_all()


class StrictModeManager(models.manager.BaseManager.from_queryset(StrictModeQuerySet)):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._strict_mode = StictModeContainer()

    def get_queryset(self):
        qs = super().get_queryset()
        self._strict_mode.clone_to(qs._strict_mode)
        return qs

    def __getattribute__(self, item):
        """
        I really would like to figure out an alternative to this, this is
        essentially monkey-patching `get_prefetch_queryset` :(

        I could not figure out another way to pass the _strict_mode parameter
        to querysets that are provided via `Prefetch("x", queryset=...)`
        """
        ret = super().__getattribute__(item)

        if item == "get_prefetch_queryset" and self._strict_mode.strict_mode:

            def get_prefetch_queryset(instances, queryset=None):
                if (
                    queryset is not None
                    and hasattr(queryset, "_strict_mode")
                    and hasattr(instances[0], "_strict_mode")
                ):
                    qs = queryset._chain()
                    instances[0]._strict_mode.clone_to(qs._strict_mode)
                    return ret(instances, qs)
                return ret(instances, queryset)

            return get_prefetch_queryset
        return ret


class StrictModeModelMixin(models.Model):
    objects = StrictModeManager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._strict_mode = StictModeContainer()

    @classmethod
    def __get_fields(cls):
        if not hasattr(cls, "__get_fields_cache"):
            cls.__get_fields_cache = set(get_fields_map_for_model(cls._meta).keys())
        return cls.__get_fields_cache

    def __getattribute__(self, item):
        if (
            not item.startswith("_")
            and hasattr(self, "_strict_mode")
            and self._strict_mode.strict_mode
            and item in self.__get_fields()
        ):
            descriptor = getattr(self.__class__, item)

            if hasattr(descriptor, "field"):
                field = descriptor.field
            else:  # reverse one to one
                field = descriptor.related.field

            field_name = item

            if isinstance(descriptor, models.query_utils.DeferredAttribute):
                if (
                    field_name not in self.__dict__
                    and not descriptor._check_parent_chain(self)
                ):
                    raise RelatedAttributeNeedsExplicitFetch(
                        self.__class__.__name__,
                        field_name,
                    )
                return super().__getattribute__(item)

            if hasattr(descriptor, "is_cached"):
                if self._strict_mode.strict_mode:
                    if not descriptor.is_cached(self):
                        raise RelatedObjectNeedsExplicitFetch(
                            self.__class__.__name__,
                            field_name,
                        )
                    ret = super().__getattribute__(item)

                    if hasattr(ret, "_strict_mode"):
                        ret._strict_mode = self._strict_mode.clone()
                    return ret
            elif field.many_to_one or field.many_to_many:

                def check_is_prefetched():
                    # If the root queryset is prefetching, then the
                    # prefetched_objects_cache hasn't been built yet,
                    # and it needs to perform the necessary queries to do so
                    if self._strict_mode.is_prefetching():
                        return

                    if field_name not in getattr(self, "_prefetched_objects_cache", {}):
                        raise RelatedObjectNeedsExplicitFetch(
                            self.__class__.__name__,
                            field_name,
                        )

                ret = super().__getattribute__(item)

                if hasattr(ret, "_strict_mode"):
                    ret._strict_mode = self._strict_mode.clone()
                    ret._strict_mode.verify_queryset_is_prefetched = check_is_prefetched
                return ret
        return super().__getattribute__(item)

    class Meta:
        abstract = True
