from django.conf import settings


DEFAULT_CONFIG = {
    "AUTO_ADD_MODEL_MIXIN": False,
    "STRICT_MODE_GLOBAL_OVERRIDE": None,
}


class Config:
    def __init__(self, default_config):
        self._default_config = default_config

    @property
    def auto_add_model_mixin(self):
        return self.get_setting("AUTO_ADD_MODEL_MIXIN")

    @property
    def strict_mode_global_override(self):
        return self.get_setting("STRICT_MODE_GLOBAL_OVERRIDE")

    @property
    def _user_config(self):
        return getattr(settings, "DJANGO_ORM_PLUS", {})

    def get_setting(self, item):
        try:
            return self._user_config[item]
        except KeyError:
            return self._default_config[item]


config = Config(DEFAULT_CONFIG)
