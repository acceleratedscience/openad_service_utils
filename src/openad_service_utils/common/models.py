from pydantic.v1 import BaseModel, Field

class FileResponse(BaseModel):
    """A special response class for returning downloadable files."""
    file_path: str = Field(..., description="The relative path to the file within the secure sandbox directory.")