def get_fields_map_for_model(model_meta):
    return {
        field.get_accessor_name()
        if hasattr(field, "get_accessor_name")
        else field.name: field
        for field in model_meta.get_fields()
    }


def cmp(x, y):
    return (x > y) - (x < y)
