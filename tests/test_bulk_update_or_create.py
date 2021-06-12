import pytest

from app.models import Location, Restaurant

from .factories import UserFavoriteFactory


pytestmark = pytest.mark.django_db


class TestBulkUpdateOrCreate:
    @pytest.fixture(autouse=True)
    def create_base_objects(self):
        for i in range(0, 2):
            UserFavoriteFactory()

    def test_create(self, django_assert_num_queries):
        location = Location.objects.create(city="Toronto")

        with django_assert_num_queries(3):
            updated, created = Restaurant.objects.bulk_update_or_create(
                [Restaurant(location_id=location.id, best_pizza_id=1)],
                lookup_fields=["location_id"],
                update_fields=["best_pizza_id"],
            )

        assert not updated
        assert len(created) == 1
        assert created[0].pk is not None
        assert created[0].location_id == location.id
        assert created[0].created_at is not None

    def test_update(self, django_assert_num_queries):
        restaurant = Restaurant.objects.first()

        with django_assert_num_queries(2):
            updated, created = Restaurant.objects.bulk_update_or_create(
                [Restaurant(id=1, location_id=2)],
                lookup_fields=["id"],
                update_fields=["location_id"],
            )

        assert not created
        assert len(updated) == 1
        assert updated[0].pk == restaurant.pk
        assert updated[0].location_id != restaurant.location_id
        assert updated[0].updated_at != restaurant.updated_at

    def test_update_same_as_original(self, django_assert_num_queries):
        restaurant = Restaurant.objects.first()
        original_location_id = restaurant.location_id
        original_updated_at = restaurant.updated_at

        with django_assert_num_queries(1):
            updated, created = Restaurant.objects.bulk_update_or_create(
                [Restaurant(id=1, location_id=original_location_id)],
                lookup_fields=["id"],
                update_fields=["location_id"],
            )
            assert not created
            assert not updated

        restaurant.refresh_from_db()
        assert restaurant.updated_at == original_updated_at
