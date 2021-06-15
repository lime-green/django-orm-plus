from contextlib import contextmanager

import pytest
from django.db.migrations.state import ModelState
from django.db.models import Model, QuerySet
from django.db.models.manager import BaseManager, Manager
from django.test import override_settings
from django_orm_plus.apps import auto_add_mixin_to_model
from django_orm_plus.mixins import ORMPlusModelMixin, ORMPlusQuerySet


pytestmark = pytest.mark.django_db


@contextmanager
def auto_patch(val):
    with override_settings(DJANGO_ORM_PLUS={"AUTO_ADD_MODEL_MIXIN": val}):
        yield


class TestAutoPatch:
    @pytest.fixture(scope="function")
    def DummyModel(self):
        class DummyModel(Model):
            class Meta:
                app_label = "test"

        return DummyModel

    @pytest.fixture(scope="function")
    def CustomQuerySet(self):
        class CustomQuerySet(QuerySet):
            pass

        return CustomQuerySet

    @pytest.fixture(scope="function")
    def CustomManager(self, CustomQuerySet):
        class CustomManager(BaseManager.from_queryset(CustomQuerySet)):
            pass

        return CustomManager

    @pytest.fixture(scope="function")
    def DummyModelWithCustomManager(self, CustomManager):
        class DummyModelWithCustomManager(Model):
            objects = CustomManager()

            class Meta:
                app_label = "test"

        return DummyModelWithCustomManager

    def _assert_model_not_patched(self, model):
        assert not hasattr(model.objects, "bulk_update_or_create")
        assert not hasattr(model.objects, "fetch_related")
        assert not hasattr(model.objects, "strict")
        assert not hasattr(model.objects, "_strict_mode")
        assert not isinstance(model.objects.all(), ORMPlusQuerySet)
        assert not hasattr(model(), "_strict_mode")
        assert ORMPlusModelMixin not in model.__bases__

    def _assert_model_is_patched(self, model):
        assert hasattr(model.objects, "bulk_update_or_create")
        assert hasattr(model.objects, "fetch_related")
        assert hasattr(model.objects, "strict")
        assert hasattr(model.objects, "_strict_mode")
        assert isinstance(model.objects.all(), ORMPlusQuerySet)
        assert hasattr(model(), "_strict_mode")
        assert model.__bases__[0] is ORMPlusModelMixin

    def test_does_not_patch_by_default(self, DummyModel):
        auto_add_mixin_to_model(DummyModel)

        self._assert_model_not_patched(DummyModel)

    def test_does_not_patch_when_config_value_is_false(self, DummyModel):
        with auto_patch(False):
            auto_add_mixin_to_model(DummyModel)

        self._assert_model_not_patched(DummyModel)

    def test_patches_when_config_value_is_true(self, DummyModel):
        with auto_patch(True):
            auto_add_mixin_to_model(DummyModel)

        self._assert_model_is_patched(DummyModel)

    def test_preserves_custom_manager_and_queryset(
        self, DummyModelWithCustomManager, CustomManager, CustomQuerySet
    ):
        with auto_patch(True):
            auto_add_mixin_to_model(DummyModelWithCustomManager)

        self._assert_model_is_patched(DummyModelWithCustomManager)
        assert isinstance(DummyModelWithCustomManager.objects, CustomManager)
        assert isinstance(DummyModelWithCustomManager.objects.all(), CustomQuerySet)

    def test_does_nothing_if_mixin_already_added(self, DummyModel):
        class MyModel(ORMPlusModelMixin, DummyModel):
            class Meta:
                app_label = "test"

        self._assert_model_is_patched(MyModel)
        state_before = ModelState.from_model(MyModel)

        with auto_patch(True):
            auto_add_mixin_to_model(MyModel)

        self._assert_model_is_patched(MyModel)
        state_after = ModelState.from_model(MyModel)

        assert state_after == state_before

    def test_model_state_is_unchanged(self, DummyModelWithCustomManager, CustomManager):
        class MyModel(DummyModelWithCustomManager):
            another_manager = Manager()

            class Meta:
                app_label = "test"

        self._assert_model_not_patched(MyModel)
        no_patch_state = ModelState.from_model(MyModel)

        with auto_patch(True):
            auto_add_mixin_to_model(MyModel)
        self._assert_model_is_patched(MyModel)

        patch_state = ModelState.from_model(MyModel)
        # We modify __bases__ with the mixin
        # but we don't really care since it doesn't cause a migration
        patch_state.bases = patch_state.bases[:-1]
        assert patch_state == no_patch_state
