"""
This module is an template example for wrapping a single predictor model for
OpenAD Model Service.

To wrap multiple models with one class, see multiapp example here:
openad_service_utils/examples/properties/simple_multi_application/implementation_multiapp.py
"""
import os
from typing import List, Any
from pydantic.v1 import Field
from openad_service_utils import (
    start_server,
    SimplePredictor,
    PredictorTypes,
    DomainSubmodule,
    PropertyInfo,
)

# -----------------------USER MODEL IMPORTS--------------------------------
from property_classifier_example import ClassificationModel


class MyPredictor(SimplePredictor):
    """Wrapped model sample class: use as a template to wrap a predictor model.
    
    `MyPredictor` is a placeholder. Replace it with a name tailored to the
    model being wrapped.

    Attributes:
        domain (DomainSubmodule("molecules" | "proteins" | "crystals")): type 
            of main model input, "molecules" for small molecules in SMILES
            format, "proteins" for macromolecules in FASTA format, "crystals"
            for materials in CIF, XYZ, or other materials science format.  
        algorithm_name (str): name of the parent model, pretrained model or
            model family.  
        algorithm_application (str): name of the finetuned model, task, or
            application.  
        property_type (PredictorTypes): PredictorTypes.MOLECULE | PredictorTypes.PROTEIN | PredictorTypes.CRYSTAL
    
        Example: For MoLFormer model finetuned on the ClinTox dataset,
            MoLFormer takes SMILES strings as input. Accordingly,      
            `domain` is DomainSubmodule("molecules");  
            `algorithm_name` is "molformer" or "MoLFormer", case-sensitive.  
            `algorithm_application` is "clintox" or "ClinTox", case-sensitive.
            property_type is PredictorTypes.MOLECULE

        Note: when storing model files in S3 cloud object store
        
    """

    # s3 path: domain / algorithm_name / algorithm_application / algorithm_version
    # necessary params
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "smi_ted"
    algorithm_application: str = "MyPredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE
    # OPTIONAL (available_properties). Use only if your class implements many models the user can choose from.
    available_properties: List[PropertyInfo] = [
        PropertyInfo(name="property1", description=""),
        PropertyInfo(name="property2", description=""),
    ]
    # user provided params for api / model inference
    batch_size: int = Field(description="Prediction batch size", default=128)
    workers: int = Field(description="Number of data loading workers", default=8)
    device: str = Field(description="Device to be used for inference", default="cpu")

    def setup(self):
        # setup your model
        self.model = None
        self.tokenizer = []
        print(">> model filepath: ", self.get_model_location())
        # -----------------------User Code goes in here------------------------
        self.model_path = os.path.join(self.get_model_location(), "model.ckpt")  # load model

    def predict(self, sample: Any):
        """run predictions on your model"""
        # -----------------------User Code goes in here------------------------
        if not self.model:
            self.model = ClassificationModel(
                model=self.algorithm_application, model_path=self.model_path, tokenizer=self.tokenizer
            )
            self.model.to(self.device)

        result = self.model.eval()
        # --------------------------------------------------------------------------
        return result


# register the function in global scope
MyPredictor.register(no_model=True)

if __name__ == "__main__":
    # start the server
    start_server(port=8080)
