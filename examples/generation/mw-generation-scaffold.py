###  Model wrapper scaffold for generative models
###  --------------------------------------------
###  https://github.com/acceleratedscience/openad_service_utils

###  Checklist:
###  ----------
###  [ ] Copy this file and rename it app.py (or alternative name)
###  [ ] Rename the MySimpleGenerator class as desired, then:
###      [ ] - Add docstring description
###      [ ] - Configure registry parameters
###      [ ] - Define model parameters in [ZONE B]
###  [ ] Store your model checkpoints and files at the path compiled by self.get_model_location() – see setup()
###  [ ] Set NO_MODEL to True if needed (see comments below)
###  [ ] Insert model imports in [ZONE A]
###  [ ] Insert model instantiation code in [ZONE C]
###  [ ] Insert model execution code in [ZONE D]
###  [ ] Remove or replace all ### comments

###  Testing:
###  --------
###  - Run `python app.py`
###  - See API docs at http://localhost:8080/docs

# Main imports
from typing import List, Any, Dict, Optional, Iterator, TypeVar
from pydantic.v1 import Field
from openad_service_utils import SimpleGenerator, start_server

# Model imports
### -----------------------------------------
### ZONE A: INSERT MODEL IMPORTS HERE
### - - - - - - - - - - - - - - - - - - - - -
### Example:
###     from mammal.model import Mammal
### -----------------------------------------

# Set this to True when you're wrapping something that's not an actual model.
# Eg. if you're simply returning a dataset for testing or otherwise
# --> This skips the step where we ensure the model artifacts are available to run
NO_MODEL = False


# Register the algorithm with the config that returns your model implementation
class MySimpleGenerator(SimpleGenerator):
    """
    <model implementation description>
    """  ### <-- Update

    # Registry parameters to fetch model from S3
    # - - -
    # S3 path: algorithm_type / algorithm_name / algorithm_application / algorithm_version
    # Run self.get_model_location() to see the compiled path
    algorithm_type: str = "conditional_generation"  ### <-- Update
    algorithm_name: str = "MyGeneratorAlgorithm"  ### <-- Update
    algorithm_application: str = "MySimpleGenerator"  ### <-- Update
    algorithm_version: str = "v0"  ### <-- Update

    # User-provided parameters for API / model inference
    ### -----------------------------------------
    ### ZONE B: DEFINE MODEL PARAMETERS HERE
    ### - - - - - - - - - - - - - - - - - - - - -
    ### Examples:
    ###   batch_size: int = Field(description="Prediction batch size", default=128)
    ###   temperature: float = Field(description="Temperature", default=0.7)
    ###   lchain: list = Field(description="L chain sequence", default=None)
    ###   hchain: list = Field(description="H chain sequence", default=None)
    ###   default_sample_size: int = Field(
    ###       description="default_sample_size, if 0 and no sample defined in the command,then return full dataset from one call of the generator",
    ###       default=0,
    ###   )
    ### -----------------------------------------

    def setup(self):
        ### -----------------------------------------
        ### ZONE C: INSERT MODEL INSTANTIATION HERE
        ### - - - - - - - - - - - - - - - - - - - - -
        ### Example:
        ###   self.model_path = self.get_model_location()
        ###   self.model = MyModel(self.model_path)
        ### -----------------------------------------

        print(">> Model filepath: ", self.get_model_location())

    # Override target description in this case we put we make the target a list
    def get_target_description(self) -> Optional[Dict[str, str]]:
        """
        Get description of the target for generation.
        If not included, this will default to a dictionary string.
        """

        return {
            "title": "TITLE GOES HERE",  ### <-- Update
            "type": "List / String / Integer / Float / ...",  ### <-- Update
            "description": "DESCRIPTION GOES HERE",  ### <-- Update
        }

    def predict(self, targets: List) -> List[Any]:
        """
        Generation logic for the model.

        Returns:
            List[Any]: ...
        """

        ### -----------------------------------------
        ### ZONE D: INSERT MODEL EXECUTION HERE
        ### - - - - - - - - - - - - - - - - - - - - -
        ### Example:
        ###   results = []
        ###   for target in targets:
        ###       for lchain in self.lchain:
        ###           for hchain in self.hchain:
        ###               results.append(
        ###                   {
        ###                       "lchain": lchain,
        ###                       "hchain": hchain,
        ###                       "antigen": target,
        ###                       "score": random.uniform(0.01, 1),
        ###                   }
        ###               )
        ###   return results
        ### -----------------------------------------

        print("\n-------------")
        print("Targets:")
        print(targets)


# Start the server
if __name__ == "__main__":
    start_server(port=8080)
