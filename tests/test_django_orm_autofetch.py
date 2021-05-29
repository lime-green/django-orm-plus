import pytest
from django.db.models import Prefetch
from django_orm_autofetch import (
    QueryModifiedAfterFetch,
    RelatedObjectNeedsExplicitFetch,
)

from app.models import Topping, Restaurant, UserFavorite

from .factories import UserFavoriteFactory


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def create_base_objects():
    for i in range(0, 2):
        UserFavoriteFactory()


def test_no_strict_mode_doesnt_error__fk_lookup():
    restaurants = Restaurant.objects.all()
    assert restaurants[0].location.city is not None


def test_with_strict_mode_errors__fk_lookup():
    restaurants = Restaurant.objects.all().strict()
    with pytest.raises(RelatedObjectNeedsExplicitFetch):
        restaurants[0].location.city


def test_with_strict_mode_doesnt_error__fk_lookup():
    restaurants = Restaurant.objects.all().select_related("location").strict()
    assert restaurants[0].location.city is not None


def test_no_strict_mode_doesnt_error__m2m_lookup():
    restaurants = Restaurant.objects.all()
    assert restaurants[0].pizzas.all()[0] is not None


def test_with_strict_mode_errors__m2m_lookup():
    restaurants = Restaurant.objects.all().strict()
    with pytest.raises(RelatedObjectNeedsExplicitFetch):
        list(restaurants[0].pizzas.all())


def test_with_strict_mode_doesnt_error__m2m_lookup():
    restaurants = Restaurant.objects.all().prefetch_related("pizzas").strict()
    assert restaurants[0].pizzas.all()[0] is not None


def test_single_item_no_strict_mode_does_not_error__fk_lookup():
    assert Restaurant.objects.first().location is not None


def test_single_item_strict_mode_errors__fk_lookup():
    with pytest.raises(RelatedObjectNeedsExplicitFetch):
        Restaurant.objects.strict().first().location


def test_single_item_strict_mode_does_not_error__fk_lookup():
    assert (
        Restaurant.objects.select_related("location").strict().first().location
        is not None
    )


def test_no_strict_mode__reverse_lookup_then_fk_lookup():
    restaurants = Restaurant.objects.all()
    assert restaurants[0].userfavorite_set.all()[0].user.id is not None


def test_with_strict_mode_errors__reverse_lookup():
    restaurants = Restaurant.objects.all().strict()
    with pytest.raises(RelatedObjectNeedsExplicitFetch):
        restaurants[0].userfavorite_set.all()[0]


def test_with_strict_mode_does_not_error__reverse_lookup():
    restaurants = Restaurant.objects.all().strict().prefetch_related("userfavorite_set")
    assert restaurants[0].userfavorite_set.all()[0] is not None


def test_with_strict_mode_errors__reverse_lookup_then_fk_lookup():
    restaurants = Restaurant.objects.all().strict().prefetch_related("userfavorite_set")
    with pytest.raises(RelatedObjectNeedsExplicitFetch):
        restaurants[0].userfavorite_set.all()[0].user


def test_with_strict_mode_errors_when_additional_filtering_is_done():
    restaurants = Restaurant.objects.all().strict().prefetch_related("userfavorite_set")
    with pytest.raises(QueryModifiedAfterFetch):
        restaurants[0].userfavorite_set.filter(restaurant_id=1)[0].id


def test_with_strict_mode_does_not_error__reverse_lookup_then_fk_lookup():
    restaurants = (
        Restaurant.objects.all()
        .strict()
        .prefetch_related(
            Prefetch(
                "userfavorite_set",
                queryset=UserFavorite.objects.all().select_related("user"),
            )
        )
    )
    assert restaurants[0].userfavorite_set.all()[0].user is not None


def test_no_strict_mode_does_not_error__fk_lookup_then_reverse_lookup():
    favorites = UserFavorite.objects.all()
    assert favorites[0].restaurant.userfavorite_set.all()[0] is not None


def test_with_strict_mode_does_not_error__fk_lookup_then_reverse_lookup():
    favorites = (
        UserFavorite.objects.select_related("restaurant")
        .prefetch_related("restaurant__userfavorite_set")
        .all()
        .strict()
    )
    assert favorites[0].restaurant.userfavorite_set.exists()


def test_with_strict_mode_does_not_error__nested_prefetch():
    toppings = (
        Topping.objects.all()
        .strict()
        .prefetch_related("pizza_set__championed_by__location")
    )
    assert toppings[0].pizza_set.all()[0].championed_by.all()[0].location.id is not None


def test_with_strict_mode_errors__no_prefetch_on_nested_relation():
    toppings = Topping.objects.all().strict().prefetch_related("pizza_set")
    with pytest.raises(QueryModifiedAfterFetch):
        toppings[0].pizza_set.prefetch_related("restaurants").all()


def test_no_strict_mode_does_not_error__o2o_field_lookup():
    favorites = UserFavorite.objects.all()
    assert favorites[0].user is not None


def test_with_strict_mode__prefetch_to_attr():
    toppings = (
        Topping.objects.all()
        .strict()
        .prefetch_related(Prefetch("pizza_set", to_attr="pizzas"))
    )
    assert toppings[0].pizzas[0] is not None
    with pytest.raises(RelatedObjectNeedsExplicitFetch):
        toppings[0].pizza_set.all()[0]


def test_with_strict_mode_errors__o2o_field_lookup():
    favorites = UserFavorite.objects.all().strict()
    with pytest.raises(RelatedObjectNeedsExplicitFetch):
        favorites[0].user


def test_with_strict_mode_does_not_error__o2o_field_lookup_and_select_related():
    favorites = UserFavorite.objects.all().select_related("user").strict()
    assert favorites[0].user.id is not None


def test_with_strict_mode_does_not_error__o2o_field_lookup_and_prefetch_related():
    favorites = UserFavorite.objects.all().prefetch_related("user").strict()
    assert favorites[0].user.id is not None


def test_bare_model_does_not_have_autofetch_attribute():
    assert not hasattr(Restaurant(), "_autofetch")


def test_model_without_strict_mode_does_not_have_autofetch_attribute():
    restaurants = Restaurant.objects.all()
    assert not hasattr(restaurants[0], "_autofetch")


def test_model_with_strict_mode_has_autofetch_attribute():
    restaurants = Restaurant.objects.all().strict()
    assert hasattr(restaurants[0], "_autofetch")
    assert restaurants[0]._autofetch.strict_mode


def test_strict_works_from_the_manager_and_queryset():
    assert Restaurant.objects.strict()[0]._autofetch.strict_mode
    assert Restaurant.objects.all().strict()[0]._autofetch.strict_mode
