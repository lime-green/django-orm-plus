class StrictModeException(Exception):
    pass


class RelatedAttributeNeedsExplicitFetch(StrictModeException):
    def __init__(self, model_name, field_name):
        super().__init__(f"{model_name}.{field_name} must be explicitly fetched")


class RelatedObjectNeedsExplicitFetch(StrictModeException):
    def __init__(self, model_name, field_name):
        super().__init__(f"{model_name}.{field_name} must be explicitly fetched")


class QueryModifiedAfterFetch(StrictModeException):
    def __init__(self, model_name, field_name):
        super().__init__(
            f"The query for {model_name}.{field_name} was modified after the results were fetched"  # noqa
        )


class InvalidLookupError(ValueError):
    pass
