from django.db import models
from django.contrib.auth.models import User

from django_orm_autofetch import StrictModeModelMixin


class Topping(StrictModeModelMixin):
    name = models.CharField(max_length=30)


class Pizza(StrictModeModelMixin):
    name = models.CharField(max_length=50)
    toppings = models.ManyToManyField(Topping)


class Location(StrictModeModelMixin):
    city = models.CharField(max_length=128)


class Restaurant(StrictModeModelMixin):
    pizzas = models.ManyToManyField(Pizza, related_name="restaurants")
    best_pizza = models.ForeignKey(
        Pizza, related_name="championed_by", on_delete=models.CASCADE
    )
    location = models.ForeignKey(Location, on_delete=models.CASCADE)


class UserFavorite(StrictModeModelMixin):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
