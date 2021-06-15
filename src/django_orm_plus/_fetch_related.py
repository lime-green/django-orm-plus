from functools import cmp_to_key
from typing import List

from django.db import models
from django.db.models.constants import LOOKUP_SEP

from .exceptions import InvalidLookupError
from ._util import cmp, get_fields_map_for_model


class AutoFetch:
    """
    Container to help manage autofetching
    """

    def __init__(self, lookup):
        self.lookup = lookup
        self.lookup_split = lookup.split(LOOKUP_SEP)
        self.depth = len(self.lookup_split) - 1

    def validate(self):
        for lookup in self.lookup_split:
            if not lookup:
                raise InvalidLookupError(f"Lookup is invalid: {self.lookup}")

    def compare(self, other):
        if self.depth != other.depth:
            return cmp(self.depth, other.depth)

        for self_lookup, other_lookup in zip(self.lookup_split, other.lookup_split):
            if self_lookup != other_lookup:
                return cmp(self_lookup, other_lookup)
        return 0

    compare_key = cmp_to_key(compare)

    def __eq__(self, other):
        return self.lookup == other.lookup

    def __hash__(self):
        return hash(self.lookup)

    def __repr__(self):
        return f'{self.__class__.__name__} "{self.lookup}"'


class AutoFetchList:
    """
    List of AutoFetch objects
    """

    def __init__(self):
        self._autofetches = {}

    def add_autofetch(self, autofetch: AutoFetch):
        autofetches_at_depth = self._autofetches.setdefault(autofetch.depth, [])

        if autofetch not in autofetches_at_depth:
            autofetches_at_depth.append(autofetch)
            autofetches_at_depth.sort(key=AutoFetch.compare_key)

    def __iter__(self):
        for i in sorted(self._autofetches.keys()):
            yield from self._autofetches[i]

    def __repr__(self):
        return f"{self.__class__.__name__} {self._autofetches}"


def normalize_lookups(lookups_) -> AutoFetchList:
    lookups = set(lookups_)

    # De-compose each lookup and add the component parts as lookups
    for lookup in lookups_:
        lookup_parts = lookup.split(LOOKUP_SEP)
        for i in range(0, len(lookup_parts)):
            lookups.add(LOOKUP_SEP.join(lookup_parts[0 : i + 1]))  # noqa

    autofetch_list = AutoFetchList()
    for lookup in lookups:
        autofetch = AutoFetch(lookup)
        autofetch.validate()
        autofetch_list.add_autofetch(autofetch)
    return autofetch_list


def get_field_for_lookup(lookup: AutoFetch, base_model_meta):
    curr_meta = base_model_meta

    for i, lookup_part in enumerate(lookup.lookup_split, start=1):
        field = get_fields_map_for_model(curr_meta)[lookup_part]
        descriptor = getattr(curr_meta.model, lookup_part)

        if i < len(lookup.lookup_split):
            curr_meta = field.related_model._meta
    return field, descriptor


class QuerySetFetchBuilder:
    def __init__(self, qs):
        self._prefetch_map = {}
        self._qs = qs
        self._model_meta = qs.model._meta

    def _get_prefetch_map_info(self, lookup: AutoFetch):
        lookup_parts = lookup.lookup_split[:-1]
        lookup_full_path = lookup.lookup

        for i in reversed(range(0, len(lookup_parts))):
            prefetch_through = LOOKUP_SEP.join(lookup_parts[: i + 1])
            prefetch_to = LOOKUP_SEP.join(lookup.lookup_split[i + 1 :])  # noqa

            if prefetch_through in self._prefetch_map:
                return prefetch_through, prefetch_to
        return None, lookup_full_path

    def _add_fetch_for_field(self, lookup: AutoFetch, field: models.Field, descriptor):
        prefetch_through, prefetch_to = self._get_prefetch_map_info(lookup)

        def add_fetch_to_qs(qs):
            if field.one_to_one or field.many_to_one:
                return qs.select_related(prefetch_to)
            if field.one_to_many or field.many_to_many:
                if getattr(descriptor, "reverse", True):
                    prefetch_qs = descriptor.rel.related_model.objects.all()
                else:
                    prefetch_qs = descriptor.rel.model.objects.all()

                prefetch = models.Prefetch(prefetch_to, queryset=prefetch_qs)
                self._prefetch_map[lookup.lookup] = prefetch
                return qs.prefetch_related(prefetch)
            return qs

        if prefetch_through is None:
            # we haven't added a prefetch for the parent queryset
            self._qs = add_fetch_to_qs(self._qs)
        else:
            # we have added a prefetch for the parent queryset, so perform
            # any additional fetches on that object instead
            prefetch = self._prefetch_map[prefetch_through]
            prefetch.queryset = add_fetch_to_qs(
                prefetch.queryset,
            )

    def add_lookup(self, lookup: AutoFetch):
        field, descriptor = get_field_for_lookup(lookup, self._model_meta)
        self._add_fetch_for_field(lookup, field, descriptor)

    def get_qs(self):
        return self._qs


def fetch_related(qs: models.QuerySet, attrs: List):
    if not attrs:
        return qs

    lookups = normalize_lookups(attrs)
    builder = QuerySetFetchBuilder(qs)

    for lookup in lookups:
        builder.add_lookup(lookup)

    qs = builder.get_qs()
    return qs
