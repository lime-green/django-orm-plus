import factory

from app.models import Pizza, Topping, Location, Restaurant, User, UserFavorite


class ToppingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Topping

    name = factory.Faker("name")


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    city = factory.Faker("address")


class PizzaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pizza

    name = factory.Faker("name")

    @factory.post_generation
    def toppings(self, *args, **kwargs):
        self.toppings.set(
            [
                ToppingFactory(),
                ToppingFactory(),
                ToppingFactory(),
            ]
        )


class RestaurantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Restaurant

    location = factory.SubFactory(LocationFactory)
    best_pizza = factory.SubFactory(PizzaFactory)

    @factory.post_generation
    def pizzas(self, *args, **kwargs):
        pizzas = [
            PizzaFactory(),
            PizzaFactory(),
            PizzaFactory(),
        ]
        self.pizzas.set(pizzas)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("name")


class UserFavoriteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserFavorite

    restaurant = factory.SubFactory(RestaurantFactory)
    user = factory.SubFactory(UserFactory)
