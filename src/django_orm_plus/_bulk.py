from django.db import transaction
from django.db.models import Q
from django.utils import timezone


def bulk_update_or_create(
    model, objects, lookup_fields, update_fields, batch_size=None
):
    """
    :param objects: List of objects to update or create
    :param lookup_fields: List of field names that uniquely identify a record
    :param update_fields: List of field names that need to be updated
    :param return_records: If the affected records should be returned
    :return:
    """
    if not objects:
        return [], []

    assert model == objects[0]._meta.model

    def lookup_objs(objs):
        lookup_filter = Q(pk__in=[])

        for obj in objs:
            lookup_query = {
                lookup_field: getattr(obj, lookup_field)
                for lookup_field in lookup_fields
            }
            lookup_filter |= Q(**lookup_query)
        return model.objects.filter(lookup_filter)

    def make_key(obj):
        return tuple(getattr(obj, lookup_field) for lookup_field in lookup_fields)

    obj_mapping = {make_key(obj): obj for obj in lookup_objs(objects)}
    objs_to_create = []
    objs_to_update = []
    auto_now_fields = [
        field.name for field in model._meta.fields if getattr(field, "auto_now", False)
    ]
    now = timezone.now()

    for obj in objects:
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

    with transaction.atomic(savepoint=False):
        if objs_to_create:
            model.objects.bulk_create(objs_to_create, batch_size=batch_size)
        if objs_to_update:
            model.objects.bulk_update(
                objs_to_update,
                fields=update_fields + auto_now_fields,
                batch_size=batch_size,
            )

    objs_updated = objs_to_update
    # need to re-fetch because not all db engines support returning PKs
    # on bulk_create
    objs_created = list(lookup_objs(objs_to_create))
    return objs_updated, objs_created
