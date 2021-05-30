from functools import cmp_to_key
from typing import List

from django.db import models
from django.db.models.constants import LOOKUP_SEP

from ._util import cmp, get_fields_map_for_model


class InvalidLookupError(ValueError):
    pass


class AutoFetch:
    """
    Container to help manage autofetching
    """

    def __init__(self, lookup):
        self.lookup = lookup
        self.lookup_split = lookup.split(LOOKUP_SEP)

    def validate(self):
        for lookup in self.lookup_split:
            if not lookup:
                raise InvalidLookupError(f"Lookup is invalid: {self.lookup}")

    @property
    def depth(self):
        return len(self.lookup_split) - 1

    @staticmethod
    def compare(this, other):
        if this.depth != other.depth:
            return cmp(this.depth, other.depth)

        for this_lookup, other_lookup in zip(this.lookup_split, other.lookup_split):
            if this_lookup != other_lookup:
                return cmp(this_lookup, other_lookup)
        return 0

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
            autofetches_at_depth.sort(key=cmp_to_key(AutoFetch.compare))

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

        if i < len(lookup.lookup_split):
            curr_meta = field.related_model._meta
    return field


def add_lookup_for_field(qs: models.QuerySet, lookup_path: str, field: models.Field):
    if field.one_to_one or field.many_to_one:
        return qs.select_related(lookup_path)
    if field.one_to_many or field.many_to_many:
        return qs.prefetch_related(lookup_path)
    return qs


def fetch_related(qs: models.QuerySet, attrs: List):
    if not attrs:
        return qs

    lookups = normalize_lookups(attrs)

    for lookup in lookups:
        field = get_field_for_lookup(lookup, qs.model._meta)
        qs = add_lookup_for_field(qs, lookup.lookup, field)

    return qs
