from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ParametersDict(BaseModel):
    property_type: List[str]
    subjects: List[str]

    class Config:
        extra = "allow"  # Allow extra fields
        json_schema_extra = {
            "example": {
                "property_type": ["property1", "property2"],
                "subjects": ["CCO"],
                "model_param_1": "",  # Example of an additional dynamic input
                "model_param_2": ""  # Example of an additional dynamic input
            }
        }

class ServiceInput(BaseModel):
    service_type: str = Field(..., description="PredictorTypes value if using SimplePredictor else generate_data")
    service_name: str = Field(..., description="see valid name in GET/service route")
    parameters: ParametersDict = Field(..., description="see valid params in GET/service route")
    sample_size: Optional[int] = Field(default=10, description="samples to retrieve. runs model as many times as it can to get number of samples.")
