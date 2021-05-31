from django.db import models
from django.contrib.auth.models import AbstractUser

from django_orm_plus import ORMPlusModelMixin


class User(ORMPlusModelMixin, AbstractUser):
    pass


class Topping(ORMPlusModelMixin):
    name = models.CharField(max_length=30)


class Pizza(ORMPlusModelMixin):
    name = models.CharField(max_length=50)
    toppings = models.ManyToManyField(Topping)


class Location(ORMPlusModelMixin):
    city = models.CharField(max_length=128)


class Restaurant(ORMPlusModelMixin):
    pizzas = models.ManyToManyField(Pizza, related_name="restaurants")
    best_pizza = models.ForeignKey(
        Pizza, related_name="championed_by", on_delete=models.CASCADE
    )
    location = models.ForeignKey(Location, on_delete=models.CASCADE)


class UserFavorite(ORMPlusModelMixin):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
