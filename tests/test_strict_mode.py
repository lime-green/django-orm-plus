import pytest
from django.db.models import Sum, Prefetch
from django_orm_plus.exceptions import (
    QueryModifiedAfterFetch,
    RelatedAttributeNeedsExplicitFetch,
    RelatedObjectNeedsExplicitFetch,
)
from django.test import override_settings

from app.models import Location, Pizza, Topping, Restaurant, User, UserFavorite

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
    with pytest.raises(RelatedObjectNeedsExplicitFetch, match="Restaurant.location"):
        restaurants[0].location.city


def test_with_strict_mode_doesnt_error__fk_lookup():
    restaurants = Restaurant.objects.all().select_related("location").strict()
    assert restaurants[0].location.city is not None


def test_no_strict_mode_doesnt_error__m2m_lookup():
    restaurants = Restaurant.objects.all()
    assert restaurants[0].pizzas.all()[0] is not None


def test_with_strict_mode_errors__m2m_lookup():
    restaurants = Restaurant.objects.all().strict()
    with pytest.raises(RelatedObjectNeedsExplicitFetch, match="Restaurant.pizzas"):
        list(restaurants[0].pizzas.all())


def test_with_strict_mode_doesnt_error__m2m_lookup():
    restaurants = Restaurant.objects.all().prefetch_related("pizzas").strict()
    assert restaurants[0].pizzas.all()[0] is not None


def test_single_item_no_strict_mode_does_not_error__fk_lookup():
    assert Restaurant.objects.first().location is not None


def test_single_item_strict_mode_errors__fk_lookup():
    with pytest.raises(RelatedObjectNeedsExplicitFetch, match="Restaurant.location"):
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
    with pytest.raises(
        RelatedObjectNeedsExplicitFetch, match="Restaurant.userfavorite_set"
    ):
        restaurants[0].userfavorite_set.all()[0]


def test_with_strict_mode_does_not_error__reverse_lookup():
    restaurants = Restaurant.objects.all().strict().prefetch_related("userfavorite_set")
    assert restaurants[0].userfavorite_set.all()[0] is not None


def test_with_strict_mode_errors__reverse_lookup_then_fk_lookup():
    restaurants = Restaurant.objects.all().strict().prefetch_related("userfavorite_set")
    with pytest.raises(RelatedObjectNeedsExplicitFetch, match="UserFavorite.user"):
        restaurants[0].userfavorite_set.all()[0].user


def test_with_strict_mode_errors_when_additional_filtering_is_done():
    restaurants = Restaurant.objects.all().strict().prefetch_related("userfavorite_set")
    with pytest.raises(QueryModifiedAfterFetch, match="Restaurant.userfavorite_set"):
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
    with pytest.raises(QueryModifiedAfterFetch, match="Topping.pizza_set"):
        toppings[0].pizza_set.prefetch_related("restaurants").all()


def test_no_strict_mode_does_not_error__o2o_field_lookup():
    favorites = UserFavorite.objects.all()
    assert favorites[0].user is not None


def test_with_strict_mode_does_not_error__reverse_o2o():
    users = User.objects.all().select_related("userfavorite").strict()
    assert users[0].userfavorite is not None


def test_with_strict_mode_errors__reverse_o2o():
    users = User.objects.all().strict()
    with pytest.raises(RelatedObjectNeedsExplicitFetch, match="User.userfavorite"):
        assert users[0].userfavorite is not None


def test_with_strict_mode__prefetch_to_attr():
    toppings = (
        Topping.objects.all()
        .strict()
        .prefetch_related(Prefetch("pizza_set", to_attr="pizzas"))
    )
    assert toppings[0].pizzas[0] is not None
    with pytest.raises(RelatedObjectNeedsExplicitFetch, match="Topping.pizza_set"):
        toppings[0].pizza_set.all()[0]


def test_strict_mode_does_not_error__related_name_lookup():
    locations = Location.objects.all().strict().prefetch_related("restaurants")
    assert locations[0].restaurants.all()[0].id is not None


def test_strict_mode_errors__related_name_lookup():
    locations = Location.objects.all().strict()
    with pytest.raises(RelatedObjectNeedsExplicitFetch, match="Location.restaurants"):
        locations[0].restaurants.all()[0].id


def test_with_strict_mode_errors__o2o_field_lookup():
    favorites = UserFavorite.objects.all().strict()
    with pytest.raises(RelatedObjectNeedsExplicitFetch, match="UserFavorite.user"):
        favorites[0].user


def test_with_strict_mode_does_not_error__o2o_field_lookup_and_select_related():
    favorites = UserFavorite.objects.all().select_related("user").strict()
    assert favorites[0].user.id is not None


def test_with_strict_mode_does_not_error__o2o_field_lookup_and_prefetch_related():
    favorites = UserFavorite.objects.all().prefetch_related("user").strict()
    assert favorites[0].user.id is not None


def test_with_strict_mode_does_not_error_for_annotation():
    restaurants = Restaurant.objects.strict().annotate(sum=Sum("id"))
    assert restaurants[0].sum is not None


def test_model_without_strict_mode_has_flag_set_to_false():
    restaurants = Restaurant.objects.all()
    assert not restaurants[0]._strict_mode.strict_mode


def test_model_with_strict_mode_has_strict_mode_attribute():
    restaurants = Restaurant.objects.all().strict()
    assert restaurants[0]._strict_mode.strict_mode


def test_strict_works_from_the_manager_and_queryset():
    assert Restaurant.objects.strict()[0]._strict_mode.strict_mode
    assert Restaurant.objects.all().strict()[0]._strict_mode.strict_mode


def test_strict_mode_errors_if_deferred_field_is_accessed__only():
    toppings = Topping.objects.all().only("id").strict()
    with pytest.raises(RelatedAttributeNeedsExplicitFetch, match="Topping.name"):
        toppings[0].name


def test_strict_mode_errors_if_deferred_field_is_accessed__defer():
    toppings = Topping.objects.all().defer("name").strict()
    with pytest.raises(RelatedAttributeNeedsExplicitFetch):
        toppings[0].name


def test_strict_mode_does_not_error_if_deferred_field_is_not_accessed__only():
    toppings = Topping.objects.all().only("id").strict()
    assert toppings[0].id is not None


def test_strict_mode_does_not_error_if_deferred_field_is_not_accessed__defer():
    toppings = Topping.objects.all().defer("name").strict()
    assert toppings[0].id is not None


def test_strict_mode_errors_nested_deferred_field_accessed():
    toppings = Topping.objects.all().prefetch_related(
        Prefetch("pizza_set", queryset=Pizza.objects.strict().only("id"))
    )

    with pytest.raises(RelatedAttributeNeedsExplicitFetch, match="Pizza.name"):
        toppings[0].pizza_set.all()[0].name


def test_strict_mode_is_propagated_to_child_prefetch_querysets():
    toppings = (
        Topping.objects.all()
        .strict()
        .prefetch_related(
            Prefetch("pizza_set", queryset=Pizza.objects.all().only("id"))
        )
    )

    with pytest.raises(RelatedAttributeNeedsExplicitFetch, match="Pizza.name"):
        toppings[0].pizza_set.all()[0].name


def test_strict_mode_does_not_propagate_to_non_strict_mode_relation():
    assert not hasattr(
        User.objects.strict().all().select_related("profile")[0].profile, "_autofetch"
    )


def test_strict_mode_does_not_error__global_override_false():
    with pytest.raises(RelatedObjectNeedsExplicitFetch, match="Restaurant.location"):
        restaurants = Restaurant.objects.all().strict()
        restaurants[0].location.city

    with override_settings(DJANGO_ORM_PLUS={"STRICT_MODE_GLOBAL_OVERRIDE": False}):
        restaurants = Restaurant.objects.all().strict()
        assert restaurants[0].location.city is not None


def test_no_strict_mode_still_errors__global_override_true():
    with override_settings(DJANGO_ORM_PLUS={"STRICT_MODE_GLOBAL_OVERRIDE": True}):
        with pytest.raises(
            RelatedObjectNeedsExplicitFetch, match="Restaurant.location"
        ):
            restaurants = Restaurant.objects.all()
            restaurants[0].location.city


def test_strict_mode_base_queryset_can_be_reused_but_children_cannot():
    restaurants = Restaurant.objects.all().strict().prefetch_related("pizzas")

    for restaurant in restaurants:
        assert list(restaurant.pizzas.all()) is not None

    assert restaurants.all() is not restaurants
    pizzas = restaurants[0].pizzas.all()

    with pytest.raises(QueryModifiedAfterFetch, match="Restaurant.pizzas"):
        pizzas.all()

    assert restaurants.all() is not restaurants


@pytest.mark.parametrize("strict_mode_enabled", [True, False])
def test_expected_number_of_queries_are_made(
    strict_mode_enabled, django_assert_num_queries
):
    with django_assert_num_queries(0):
        restaurants = (
            Restaurant.objects.all()
            .select_related("location")
            .prefetch_related("pizzas", "pizzas__toppings", "userfavorite_set")
        )
        if strict_mode_enabled:
            restaurants = restaurants.strict()

    with django_assert_num_queries(4):  # 1 query + 3 prefetches
        list(restaurants)

    with django_assert_num_queries(0):
        for restaurant in restaurants:
            assert restaurant.location.city is not None

            for pizza in restaurant.pizzas.all():
                assert pizza.id is not None

                for topping in pizza.toppings.all():
                    assert topping.id is not None

                assert restaurant.userfavorite_set.all() is not None
