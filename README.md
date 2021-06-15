## django-orm-plus
[![PyPI version](https://badge.fury.io/py/django-orm-plus.svg)](https://badge.fury.io/py/django-orm-plus)
![Python versions](https://img.shields.io/pypi/pyversions/django-orm-plus.svg?style=flat-square&label=Python%20Versions)

A collection of useful ORM features to make using the Django ORM convenient,
performant and safe

### Installation

```bash
pip install django-orm-plus
```
Then add `django_orm_plus` to `INSTALLED_APPS`

Now you must do one of the following:

1. Set `AUTO_ADD_MODEL_MIXIN` to `True` in `settings.py`:
    ```python
    DJANGO_ORM_PLUS = {
        "AUTO_ADD_MODEL_MIXIN": True,
    }
    ```

    This will automatically patch your models with `ORMPlusModelMixin`

2. Or, add the following model mixin to your models manually:
    ```python
    from django.db import models
    from django_orm_plus.mixins import ORMPlusModelMixin


    class MyModel(models.Model, ORMPlusModelMixin):
        name = models.CharField(max_length=10)
    ```

### Usage

This library has three important functions for use on Django QuerySets:
- `.strict()`
- `.fetch_related()`
- `.bulk_update_or_create()`

### strict
Strict mode makes sure your ORM queries are efficient and safe by not allowing
related objects to be loaded lazily, therefore `select_related`
or `prefetch_related` must be used if related objects are needed. This avoids
the [n+1 query problem](https://scoutapm.com/blog/django-and-the-n1-queries-problem).

Strict mode will also raise an error when a deferred field (`.defer()` or `.only()`)
is accessed.

You only need to add `.strict()` on your queryset wherever it's being used.
So for example in a DRF view:

```python
class UserList(generics.ListCreateAPIView):
    queryset = User.objects.all().strict()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
```

Now your queryset is strict-mode enabled and your view will error if any relations
are loaded for the user queryset eg. `users[0].profile` will error if `profile` is a foreign key.
To fix, change the query to also fetch the relation using either `select_related` or `prefetch_related`:

```python
queryset = User.objects.all().select_related("profile").strict()
```

### fetch_related
Combines both `select_related` and `prefetch_related`
to reduce the total number of queries for you automatically.

So instead of:
```python
queryset = (
    User.objects.all()
    .select_related("profile")
    .prefetch_related(
        "likes",
        Prefetch("books", queryset=Book.objects.all().select_related("author")),
    )
)
```

It's now simply:
```python
queryset = User.objects.all().fetch_related("profile", "likes", "books__author")
```

Of course, the two methods can be used together to get easy and safe queryset evaluation:
```python
queryset = User.objects.all().fetch_related("profile", "likes", "books__author").strict()
```

Since `select_related` does a join in SQL, `fetch_related` opts to use `select_related`
when possible, and in other cases will use `prefetch_related` which adds a single additional
query and does the join in Python.


### bulk_update_or_create
```python
updated, created = User.objects.bulk_update_or_create(
    [User(username="john123", first_name="Jonny"), User(username="jane_doe", first_name="Alexa")],
    lookup_fields=["username"],
    update_fields=["first_name"],
)
```

This will combine `bulk_update` and `bulk_create` and return the records that were
updated and created. `lookup_fields` is a list of field names that should uniquely
identify a record. This method takes `batch_size` as an optional parameter which defaults to 1000

## Configuration

You can set the following configuration object in `settings.py`:

```python
DJANGO_ORM_PLUS = {
    "AUTO_ADD_MODEL_MIXIN": False,
    "STRICT_MODE_GLOBAL_OVERRIDE": None,
}
```
`AUTO_ADD_MODEL_MIXIN` is a boolean flag that will auto-patch all the models
on load with `ORMPlusModelMixin`

`STRICT_MODE_GLOBAL_OVERRIDE` is a boolean flag that will enable or disable strict
mode without considering if `.strict()` is used. This can be useful if you want to
disable strict mode on production, or have all querysets use strict mode for local development.
