import pytest
from django.core.exceptions import FieldDoesNotExist

from app.models import Location, Pizza, Restaurant

from .factories import UserFavoriteFactory


pytestmark = pytest.mark.django_db


class TestBulkUpdateOrCreate:
    @pytest.fixture(autouse=True)
    def create_base_objects(self):
        for i in range(0, 2):
            UserFavoriteFactory()

    def test_create(self, django_assert_num_queries):
        location = Location.objects.create(city="Toronto")
        pizza = Pizza.objects.create(name="Margherita")

        with django_assert_num_queries(3):
            updated, created = Restaurant.objects.bulk_update_or_create(
                [Restaurant(location_id=location.id, best_pizza_id=pizza.id)],
                lookup_fields=["location_id"],
                update_fields=["best_pizza_id"],
            )

        assert not updated
        assert len(created) == 1
        assert created[0].pk is not None
        assert created[0].location_id == location.id
        assert created[0].created_at is not None
        assert created[0].best_pizza == pizza

    def test_update(self, django_assert_num_queries):
        restaurant = Restaurant.objects.first()
        location = Location.objects.create(city="Toronto")

        with django_assert_num_queries(2):
            updated, created = Restaurant.objects.bulk_update_or_create(
                [Restaurant(id=restaurant.id, location_id=location.id)],
                lookup_fields=["id"],
                update_fields=["location_id"],
            )

        assert not created
        assert len(updated) == 1
        assert updated[0].pk == restaurant.pk
        assert updated[0].location_id != restaurant.location_id
        assert updated[0].location == location
        assert updated[0].updated_at != restaurant.updated_at

    def test_update_same_as_original(self, django_assert_num_queries):
        restaurant = Restaurant.objects.first()
        original_location_id = restaurant.location_id
        original_updated_at = restaurant.updated_at

        with django_assert_num_queries(1):
            updated, created = Restaurant.objects.bulk_update_or_create(
                [Restaurant(id=restaurant.id, location_id=original_location_id)],
                lookup_fields=["id"],
                update_fields=["location_id"],
            )
            assert not created
            assert not updated

        restaurant.refresh_from_db()
        assert restaurant.updated_at == original_updated_at

    def test_many_creates_and_updates(self, django_assert_num_queries):
        existing_restaurants = list(Restaurant.objects.all())
        new_restaurant_id = existing_restaurants[-1].id + 1
        assert len(existing_restaurants) > 1

        for i, restaurant in enumerate(existing_restaurants):
            restaurant.location = Location.objects.create(
                city=f"updated-restaurant-{i}"
            )
            restaurant.best_pizza = Pizza.objects.create(name=f"updated-restaurant-{i}")

        new_restaurants = [
            Restaurant(
                id=i,
                location=Location.objects.create(city=f"new-restaurant-{i}"),
                best_pizza=Pizza.objects.create(name=f"new-restaurant-{i}"),
            )
            for i in range(new_restaurant_id, new_restaurant_id + 10)
        ]

        with django_assert_num_queries(4):
            updated, created = Restaurant.objects.bulk_update_or_create(
                existing_restaurants + new_restaurants,
                lookup_fields=["id"],
                update_fields=["location", "best_pizza"],
            )

            assert len(updated) == len(existing_restaurants)
            assert len(created) == len(new_restaurants)

    @pytest.mark.parametrize(
        "lookup_fields,update_fields",
        [
            [["id"], ["pizzas"]],
            [["id", "pizzas"], ["location_id"]],
        ],
    )
    def test_errors_if_m2m_field_is_given(self, lookup_fields, update_fields):
        restaurant = Restaurant.objects.first()

        with pytest.raises(ValueError):
            Restaurant.objects.bulk_update_or_create(
                [Restaurant(id=restaurant.id)],
                lookup_fields=lookup_fields,
                update_fields=update_fields,
            )

    @pytest.mark.parametrize(
        "lookup_fields,update_fields",
        [
            [["id"], ["non_existent"]],
            [["id", "non_existent"], ["location_id"]],
        ],
    )
    def test_errors_if_non_existent_field_is_given(self, lookup_fields, update_fields):
        restaurant = Restaurant.objects.first()

        with pytest.raises(FieldDoesNotExist):
            Restaurant.objects.bulk_update_or_create(
                [Restaurant(id=restaurant.id)],
                lookup_fields=lookup_fields,
                update_fields=update_fields,
            )

    @pytest.mark.parametrize(
        "lookup_fields,update_fields",
        [
            [["id"], ["userfavorite"]],
            [["id", "userfavorite"], ["location_id"]],
        ],
    )
    def test_errors_if_non_concrete_field_is_given(self, lookup_fields, update_fields):
        restaurant = Restaurant.objects.first()

        with pytest.raises(ValueError):
            Restaurant.objects.bulk_update_or_create(
                [Restaurant(id=restaurant.id)],
                lookup_fields=lookup_fields,
                update_fields=update_fields,
            )
