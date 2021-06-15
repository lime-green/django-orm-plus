from contextlib import contextmanager

import pytest
from django.db.migrations.state import ModelState
from django.db.models import Model, QuerySet
from django.db.models.manager import BaseManager, Manager
from django.test import override_settings
from django_orm_plus.apps import auto_add_mixin_to_model
from django_orm_plus.mixins import ORMPlusQuerySet


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

    def test_does_not_patch_by_default(self, DummyModel):
        auto_add_mixin_to_model(DummyModel)

        assert not hasattr(DummyModel.objects, "bulk_update_or_create")
        assert not hasattr(DummyModel.objects, "fetch_related")
        assert not hasattr(DummyModel.objects, "strict")
        assert not hasattr(DummyModel.objects, "_strict_mode")
        assert not isinstance(DummyModel.objects.all(), ORMPlusQuerySet)

    def test_does_not_patch_when_config_value_is_false(self, DummyModel):
        with auto_patch(False):
            auto_add_mixin_to_model(DummyModel)

        assert not hasattr(DummyModel.objects, "bulk_update_or_create")
        assert not hasattr(DummyModel.objects, "fetch_related")
        assert not hasattr(DummyModel.objects, "strict")
        assert not hasattr(DummyModel.objects, "_strict_mode")
        assert not isinstance(DummyModel.objects.all(), ORMPlusQuerySet)

    def test_patches_when_config_value_is_true(self, DummyModel):
        with auto_patch(True):
            auto_add_mixin_to_model(DummyModel)

        assert hasattr(DummyModel.objects, "bulk_update_or_create")
        assert hasattr(DummyModel.objects, "fetch_related")
        assert hasattr(DummyModel.objects, "strict")
        assert hasattr(DummyModel.objects, "_strict_mode")
        assert isinstance(DummyModel.objects.all(), ORMPlusQuerySet)

    def test_preserves_custom_manager_and_queryset(
        self, DummyModelWithCustomManager, CustomManager, CustomQuerySet
    ):
        with auto_patch(True):
            auto_add_mixin_to_model(DummyModelWithCustomManager)

        assert hasattr(DummyModelWithCustomManager.objects, "bulk_update_or_create")
        assert hasattr(DummyModelWithCustomManager.objects, "fetch_related")
        assert hasattr(DummyModelWithCustomManager.objects, "strict")
        assert hasattr(DummyModelWithCustomManager.objects, "_strict_mode")
        assert isinstance(DummyModelWithCustomManager.objects, CustomManager)
        assert isinstance(DummyModelWithCustomManager.objects.all(), ORMPlusQuerySet)
        assert isinstance(DummyModelWithCustomManager.objects.all(), CustomQuerySet)

    def test_model_state_is_unchanged(self, DummyModelWithCustomManager, CustomManager):
        class MyModel(DummyModelWithCustomManager):
            another_manager = Manager()

            class Meta:
                app_label = "test"

        assert not hasattr(MyModel.objects, "bulk_update_or_create")
        no_patch_state = ModelState.from_model(MyModel)

        with auto_patch(True):
            auto_add_mixin_to_model(MyModel)
        assert hasattr(MyModel.objects, "bulk_update_or_create")

        patch_state = ModelState.from_model(MyModel)
        # We modify __bases__ with the mixin
        # but we don't really care since it doesn't cause a migration
        patch_state.bases = patch_state.bases[:-1]
        assert patch_state == no_patch_state
