## django-orm-plus

A collection of useful ORM features to make using the Django ORM convenient,
performant and safe

### Installation

```bash
pip install django-orm-plus
```

Now add the following model mixin to your models, eg:

```python
from django.db import models
from django_orm_plus import ORMPlusModelMixin


class MyModel(ORMPlusModelMixin):
    name = models.CharField(max_length=10)
```

### Usage

This library has two important functions for use on Django QuerySets:
- `.strict()`
- `.autofetch()`

### strict
Strict mode makes sure your ORM queries are efficient and safe by not allowing
related objects to be loaded lazily, therefore `select_related`
or `prefetch_related` must be used if related objects are needed. This avoids
the [n+1 query problem](https://scoutapm.com/blog/django-and-the-n1-queries-problem).

Strict mode will also raise an error when a deferred field (`.defer()` or `.only()`)
is accessed.

You only need to add `.strict()` to the end of your queryset wherever it's being used.
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

### autofetch
Autofetch combines the two of `select_related` and `prefetch_related`
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


## Configuration

You can set the following configuration object:

```python
DJANGO_ORM_PLUS = {
    "STRICT_MODE_GLOBAL_OVERRIDE": None,
}
```

`STRICT_MODE_GLOBAL_OVERRIDE` is a boolean flag that will enable or disable strict
mode without considering if `.strict()` is used. This can be useful if you want to
disable strict mode on production, or have all querysets use strict mode for local development.
