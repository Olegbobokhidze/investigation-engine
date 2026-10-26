from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base for every request and response body: snake_case in Python, camelCase in JSON.

    `from_attributes` lets a response be built straight from an ORM object.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class ErrorDetail(ApiModel):
    code: str
    message: str
