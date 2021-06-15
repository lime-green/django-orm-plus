from django.db import models

from ._config import config
from .exceptions import (
    RelatedAttributeNeedsExplicitFetch,
    RelatedObjectNeedsExplicitFetch,
    QueryModifiedAfterFetch,
)
from ._util import get_fields_map_for_model


class StrictModeContainer:
    def __init__(self):
        self.is_for_prefetch = False
        self._is_child = False

        self._parent_cls_name = None
        self._parent_field_name = None

        self._strict_mode = False
        self._strict_mode_override = config.strict_mode_global_override

    def clone(self, **kwargs):
        return self.clone_to(self.__class__(), **kwargs)

    def clone_to(
        self, other, parent_cls_name=None, parent_field_name=None, is_child=None
    ):
        other.strict_mode = self.strict_mode
        other._parent_cls_name = parent_cls_name or self._parent_cls_name
        other._parent_field_name = parent_field_name or self._parent_field_name
        other._is_child = is_child if is_child is not None else self._is_child
        other.is_for_prefetch = self.is_for_prefetch
        return other

    def enable_strict_mode(self):
        self.strict_mode = True

    def verify_query_modification(self, queryset):
        if not self.strict_mode:
            return

        if queryset._prefetch_done and self._is_child:
            raise QueryModifiedAfterFetch(
                self._parent_cls_name, self._parent_field_name
            )

    def verify_prefetch(self, queryset):
        if not self.strict_mode:
            return

        if (
            queryset._result_cache is None
            and self._is_child
            and not self.is_for_prefetch
        ):
            raise RelatedObjectNeedsExplicitFetch(
                self._parent_cls_name, self._parent_field_name
            )

    @property
    def strict_mode(self):
        if self._strict_mode_override is not None:
            return self._strict_mode_override
        return self._strict_mode

    @strict_mode.setter
    def strict_mode(self, val):
        self._strict_mode = val


class StrictModeIterable(models.query.ModelIterable):
    def __iter__(self):
        qs_strict_mode = getattr(self.queryset, "_strict_mode", None)

        for obj in super().__iter__():
            if qs_strict_mode and qs_strict_mode.strict_mode:
                obj._strict_mode = qs_strict_mode.clone(is_child=True)
            yield obj


class StrictModeQuerySet(models.QuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._strict_mode = StrictModeContainer()
        self._iterable_class = StrictModeIterable

    def _clone(self):
        self._strict_mode.verify_query_modification(self)
        qs = super()._clone()
        self._strict_mode.clone_to(qs._strict_mode)
        return qs

    def strict(self):
        qs = self._chain()
        qs._strict_mode.enable_strict_mode()
        return qs

    def _fetch_all(self):
        self._strict_mode.verify_prefetch(self)
        super()._fetch_all()


class StrictModeManager(models.manager.BaseManager.from_queryset(StrictModeQuerySet)):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._strict_mode = StrictModeContainer()

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
                if queryset is None:
                    queryset = self.get_queryset()

                if hasattr(queryset, "_strict_mode") and hasattr(
                    instances[0], "_strict_mode"
                ):
                    instances[0]._strict_mode.clone_to(queryset._strict_mode)
                    queryset._strict_mode.is_for_prefetch = True
                    return ret(instances, queryset)
                return ret(instances, queryset)

            return get_prefetch_queryset
        return ret


class StrictModeModelMixin(models.Model):
    objects = StrictModeManager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._strict_mode = StrictModeContainer()

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

            cls_name = self.__class__.__name__
            field_name = item

            if isinstance(descriptor, models.query_utils.DeferredAttribute):
                if (
                    field_name not in self.__dict__
                    and not descriptor._check_parent_chain(self)
                ):
                    raise RelatedAttributeNeedsExplicitFetch(
                        cls_name,
                        field_name,
                    )
                return super().__getattribute__(item)

            if hasattr(descriptor, "is_cached"):
                if self._strict_mode.strict_mode:
                    if not descriptor.is_cached(self):
                        raise RelatedObjectNeedsExplicitFetch(
                            cls_name,
                            field_name,
                        )
                    ret = super().__getattribute__(item)

                    if hasattr(ret, "_strict_mode"):
                        ret._strict_mode = self._strict_mode.clone(
                            parent_cls_name=cls_name,
                            parent_field_name=field_name,
                            is_child=True,
                        )
                    return ret
            elif field.many_to_one or field.many_to_many:
                ret = super().__getattribute__(item)

                if hasattr(ret, "_strict_mode"):
                    ret._strict_mode = self._strict_mode.clone(
                        parent_cls_name=cls_name,
                        parent_field_name=field_name,
                        is_child=True,
                    )
                return ret
        return super().__getattribute__(item)

    class Meta:
        abstract = True
