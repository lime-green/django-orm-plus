import pytest
from django_orm_autofetch import fetch_related, RelatedObjectNeedsExplicitFetch
from django_orm_autofetch._fetch_related import (
    AutoFetch,
    InvalidLookupError,
    normalize_lookups,
)

from app.models import Restaurant, UserFavorite

from .factories import UserFavoriteFactory


pytestmark = pytest.mark.django_db


class TestNormalizeLookups:
    def test_empty_case(self):
        assert normalize_lookups([])._autofetches == {}

    def test_removes_duplicates(self):
        assert normalize_lookups(["x", "x"])._autofetches == {0: [AutoFetch("x")]}

    def test_sorts_on_same_level(self):
        assert normalize_lookups(["y", "x"])._autofetches == {
            0: [AutoFetch("x"), AutoFetch("y")]
        }

    def test_multilevel(self):
        assert normalize_lookups(["y__a", "x"])._autofetches == {
            0: [AutoFetch("x"), AutoFetch("y")],
            1: [AutoFetch("y__a")],
        }

    def test_invalid_lookup(self):
        with pytest.raises(InvalidLookupError):
            assert normalize_lookups(["x__"])

    def test_iterates_in_order(self):
        assert list(normalize_lookups(["y__a", "x", "y__b"])) == [
            AutoFetch("x"),
            AutoFetch("y"),
            AutoFetch("y__a"),
            AutoFetch("y__b"),
        ]


class TestFetchRelated:
    @pytest.fixture(autouse=True)
    def create_base_objects(self):
        for i in range(0, 2):
            UserFavoriteFactory()

    def _assert_matches_and_runs(
        self, qs, expected_prefetches=None, expected_selects=None
    ):
        assert qs._prefetch_related_lookups == tuple(expected_prefetches or [])
        assert qs.query.select_related == (expected_selects or False)
        assert list(qs) is not None

    def test_prefetch__m2m(self):
        self._assert_matches_and_runs(
            fetch_related(Restaurant.objects.all(), ["pizzas"]), ["pizzas"]
        )

    def test_prefetch__reverse_fk(self):
        self._assert_matches_and_runs(
            fetch_related(Restaurant.objects.all(), ["userfavorite_set"]),
            ["userfavorite_set"],
        )

    def test_prefetch__multiple(self):
        self._assert_matches_and_runs(
            fetch_related(Restaurant.objects.all(), ["pizzas", "userfavorite_set"]),
            ["pizzas", "userfavorite_set"],
        )

    def test_prefetch__nested(self):
        self._assert_matches_and_runs(
            fetch_related(Restaurant.objects.all(), ["pizzas__toppings"]),
            ["pizzas", "pizzas__toppings"],
        )

    def test_select_related__fk(self):
        self._assert_matches_and_runs(
            fetch_related(Restaurant.objects.all(), ["location"]),
            expected_selects={"location": {}},
        )

    def test_select_related__o2o(self):
        self._assert_matches_and_runs(
            fetch_related(UserFavorite.objects.all(), ["user"]),
            expected_selects={"user": {}},
        )

    def test_prefetch_on_a_select_related_field(self):
        self._assert_matches_and_runs(
            fetch_related(
                Restaurant.objects.all(), ["best_pizza", "best_pizza__toppings"]
            ),
            expected_prefetches=["best_pizza__toppings"],
            expected_selects={"best_pizza": {}},
        )

    def test_select_related_on_a_prefetched_field(self):
        self._assert_matches_and_runs(
            fetch_related(
                Restaurant.objects.all(), ["userfavorite_set", "userfavorite_set__user"]
            ),
            expected_prefetches=["userfavorite_set"],
        )

    class TestWithStrictMode:
        def test_it_calls_both_without_error(self):
            assert (
                list(Restaurant.objects.all().fetch_related("best_pizza").strict())
                is not None
            )

        def test_it_errors_when_related_object_is_not_fetched(self):
            restaurants = Restaurant.objects.all().fetch_related("best_pizza").strict()
            assert restaurants[0].best_pizza is not None

            with pytest.raises(RelatedObjectNeedsExplicitFetch):
                restaurants[0].best_pizza.toppings.all()[0]