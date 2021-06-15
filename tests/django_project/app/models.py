from django.db import models
from django.contrib.auth.models import AbstractUser

from django_orm_plus.mixins import ORMPlusModelMixin


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Profile(BaseModel):
    pass


class User(BaseModel, ORMPlusModelMixin, AbstractUser):
    profile = models.OneToOneField(Profile, null=True, on_delete=models.PROTECT)


class Topping(BaseModel, ORMPlusModelMixin):
    name = models.CharField(max_length=30)


class Pizza(BaseModel, ORMPlusModelMixin):
    name = models.CharField(max_length=50)
    toppings = models.ManyToManyField(Topping)


class Location(BaseModel, ORMPlusModelMixin):
    city = models.CharField(max_length=128)


class Restaurant(BaseModel, ORMPlusModelMixin):
    pizzas = models.ManyToManyField(Pizza, related_name="restaurants")
    best_pizza = models.ForeignKey(
        Pizza, related_name="championed_by", on_delete=models.CASCADE
    )
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="restaurants"
    )


class UserFavorite(BaseModel, ORMPlusModelMixin):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
