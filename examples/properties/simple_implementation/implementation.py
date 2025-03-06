"""Example template for wrapping a single predictor model for OpenAD Model Service.

To wrap multiple models with one class, see multiapp example here:
openad_service_utils/examples/properties/simple_multi_application/implementation_multiapp.py
"""
import os
from typing import Any
from pydantic.v1 import Field
from openad_service_utils import (
    start_server,
    SimplePredictor,
    PredictorTypes,
    DomainSubmodule,
)

# Wrapping Step 1: Copy your model's imports here.
# - And delete this placeholder import
from property_classifier_example import ClassificationModel


class MyPredictor(SimplePredictor):
    """Wrapped model sample class: use as a template to wrap a predictor model.
    
    Class name `MyPredictor` is a placeholder. Replace it with a name tailored
    to the model being wrapped.

    Attributes:
        domain (DomainSubmodule("molecules" | "proteins" | "crystals")): type 
            of main model input, "molecules" for small molecules in SMILES
            format, "proteins" for macromolecules in FASTA format, "crystals"
            for materials in CIF, XYZ, or other materials science format.  
        algorithm_name (str): name of the parent model, pretrained model or
            model family.  
        algorithm_application (str): name of the finetuned model, task, or
            application.  
        algorithm_version (str): version name of this model instance. Defaults
            to "v0".  
        property_type (PredictorTypes):  
            PredictorTypes.MOLECULE | PredictorTypes.PROTEIN | PredictorTypes.CRYSTAL
    
    Example: For MoLFormer model finetuned on the ClinTox dataset,
        MoLFormer takes SMILES strings as input. Accordingly,      
        `domain` is DomainSubmodule("molecules");  
        `algorithm_name` is "molformer", case-sensitive.  
        `algorithm_application` is "clintox", case-sensitive.
        `algorithm_version` is the version name of this mode; we use the
            default, "v0".
        property_type is PredictorTypes.MOLECULE;
        the S3 path when `NO_MODEL` is `False` is  
        "molecules/molformer/clintox/v0" 

    Note: When storing model files in S3 cloud object store (`NO_MODEL`
        is `False`), this is the S3 path:  
        `domain`/`algorithm_name`/`algorithm_application`/`algorithm_version`   
    """
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "smi_ted"
    algorithm_application: str = "MyPredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE

    # User provided params for api / model inference
    batch_size: int = Field(description="Prediction batch size", default=128)
    workers: int = Field(description="Number of data loading workers", default=8)
    device: str = Field(description="Device to be used for inference", default="cpu")

    def setup(self):
        """Model setup. Loads the model and tokenizer, if any. Runs once.

        To wrap a model, copy and modify the standalone model setup and load
        code here. Remember to change variables to instance variables, so they
        can be used in the `predict` method.
        """
        self.model = None
        self.tokenizer = []
        print(">> model filepath: ", self.get_model_location())

        self.model_path = os.path.join(self.get_model_location(), "model.ckpt")  # load model

    def predict(self, sample: Any):
        """run predictions on your model"""
        # -----------------------User Code goes in here------------------------
        if not self.model:
            self.model = ClassificationModel(
                model=self.algorithm_application, model_path=self.model_path, tokenizer=self.tokenizer
            )
            self.model.to(self.device)

        result = ???  # FIXME: Use something besides eval(). In PyTorch, this does NOT evaluate a model on input.
                           # FIXME: model.eval() is void (returns nothing), and has the side effect of turning off randomness (dropout, etc) in the model.
        # --------------------------------------------------------------------------
        return result


# Register the class in global scope
MyPredictor.register(no_model=True)

if __name__ == "__main__":
    # Start the server
    start_server(port=8080)
