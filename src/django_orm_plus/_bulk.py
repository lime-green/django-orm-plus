from django.db import transaction
from django.db.models import Q
from django.utils import timezone


DEFAULT_BATCH_SIZE = 1000


def _bulk_update_or_create_batch(qs, objects_batch, lookup_fields, update_fields):
    def make_key(obj):
        return tuple(getattr(obj, lookup_field) for lookup_field in lookup_fields)

    def lookup_objs(objs):
        lookup_filter = Q(pk__in=[])

        for obj in objs:
            lookup_query = {
                lookup_field: getattr(obj, lookup_field)
                for lookup_field in lookup_fields
            }
            lookup_filter |= Q(**lookup_query)
        return qs.filter(lookup_filter)

    objs_to_create = []
    objs_to_update = []
    auto_now_fields = [
        field.name
        for field in qs.model._meta.get_fields()
        if getattr(field, "auto_now", False)
    ]
    now = timezone.now()

    obj_mapping = {
        make_key(obj): obj for obj in lookup_objs(objects_batch).select_for_update()
    }

    for obj in objects_batch:
        key = make_key(obj)

        if key in obj_mapping:
            existing_obj = obj_mapping[key]
            if any(
                getattr(obj, update_field) != getattr(existing_obj, update_field)
                for update_field in update_fields
            ):
                for auto_now_field in auto_now_fields:
                    setattr(existing_obj, auto_now_field, now)
                for update_field in update_fields:
                    target_value = getattr(obj, update_field)
                    setattr(existing_obj, update_field, target_value)
                objs_to_update.append(existing_obj)
        else:
            objs_to_create.append(obj)

    if objs_to_create:
        qs.bulk_create(objs_to_create)
    if objs_to_update:
        qs.bulk_update(
            objs_to_update,
            fields=update_fields + auto_now_fields,
        )

    objects_updated = objs_to_update
    # need to re-fetch because not all db engines support returning PKs
    # on bulk_create
    objects_created = list(lookup_objs(objs_to_create))
    return objects_updated, objects_created


def _get_validated_fields(qs, fields):
    fields = [qs.model._meta.get_field(field) for field in fields]
    if any(not f.concrete or f.many_to_many for f in fields):
        raise ValueError("Only concrete fields are allowed")

    # we don't want to trigger any related object lookups
    # eg. instead of obj.related we use obj.related_id
    return [field.attname for field in fields]


def bulk_update_or_create(
    qs, objects, lookup_fields, update_fields, batch_size=DEFAULT_BATCH_SIZE
):
    """
    :param objects: List of objects to update or create
    :param lookup_fields: List of field names that uniquely identify a record
    :param update_fields: List of field names that need to be updated
    :param return_records: If the affected records should be returned
    :return:
    """
    objects = tuple(objects)

    if not objects:
        return [], []

    if batch_size is None:
        batch_size = DEFAULT_BATCH_SIZE

    objects_updated = []
    objects_created = []

    update_fields = _get_validated_fields(qs, update_fields)
    lookup_fields = _get_validated_fields(qs, lookup_fields)

    with transaction.atomic(using=qs.db, savepoint=False):
        for i in range(0, len(objects), batch_size):
            objects_batch = objects[i : i + batch_size]  # noqa
            objects_updated_batch, objects_created_batch = _bulk_update_or_create_batch(
                qs, objects_batch, lookup_fields, update_fields
            )
            objects_updated += objects_updated_batch
            objects_created += objects_created_batch

    return objects_updated, objects_created
