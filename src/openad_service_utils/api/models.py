from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any
from enum import Enum


class ServiceType(str, Enum):
    GET_PROTEIN_PROPERTY = "get_protein_property"
    GET_MOLECULE_PROPERTY = "get_molecule_property"
    GET_CRYSTAL_PROPERTY = "get_crystal_property"
    GENERATE_DATA = "generate_data"
    GET_RESULT = "get_result"


class Parameters(BaseModel):
    property_type: list[str] = Field(..., description="The type of property to be predicted.")
    subjects: Optional[list[str]] = Field(None, description="The subjects to be predicted.")
    max_samples: Optional[int] = Field(None, description="The maximum number of samples to generate for `generate_data` service.")

    class Config:
        extra = "allow"


class ServiceRequest(BaseModel):
    """
    Pydantic model for the service request body.
    """
    service_type: ServiceType = Field(..., description="The type of service to be called.")
    service_name: Optional[str] = Field(None, description="The name of the model to be used.")
    parameters: Optional[Parameters] = Field(None, description="An object containing the parameters for the model.")
    async_job: Optional[bool] = Field(False, description="Whether to run the job asynchronously.", alias="async")
    url: Optional[str] = Field(None, description="The job id to retrieve the results from.")

    @model_validator(mode='before')
    def check_service_type(cls, values):
        service_type = values.get('service_type')
        if service_type == ServiceType.GET_RESULT:
            if 'url' not in values:
                raise ValueError('url is required when service_type is get_result')
            # make other fields optional
            values['service_name'] = values.get('service_name')
            values['parameters'] = values.get('parameters')

        else:
            if 'service_name' not in values:
                raise ValueError('service_name is required')
            if 'parameters' not in values:
                raise ValueError('parameters is required')
        return values

    class Config:
        validate_by_name = True
