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

# Wrapping Step 1: Copy the model's imports here:
import torch
from fuse.data.tokenizers.modular_tokenizer.op import ModularTokenizerOp

from mammal.examples.protein_solubility.task import ProteinSolubilityTask
from mammal.keys import CLS_PRED, SCORES
from mammal.model import Mammal

NO_MODEL = True


class ProteinSolubility(SimplePredictor):
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

    domain: DomainSubmodule = DomainSubmodule("properties")
    algorithm_name: str = "mammal"
    algorithm_application: str = "solubility"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.PROTEIN

    # User-provided params for the api or for model inference:
    # Removed sample params

    def setup(self):
        """Model setup. Loads the model and tokenizer, if any. Runs once.

        To wrap a model, copy and modify the standalone model setup and load
        code here. Remember to change variables to instance variables, so they
        can be used in the `predict` method.
        """
        # Load model
        self.model = Mammal.from_pretrained(
            "ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")
        self.model.eval()

        # Load Tokenizer
        self.tokenizer_op = ModularTokenizerOp.from_pretrained(
            "ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")

    def predict(self, sample: Any = "NLMKRCTRGFRKLGKCTTLEEEKCKTLYPRGQCTCSDSKMNTHSCDCKSC"
            ):
        """Run inference code. Use instance variables for values from setup.
        """
        # Begin copied, adapted model inference code---------------------------
        # convert to MAMMAL style
        sample_dict = {"protein_seq": sample}  # Rename protein_seq -> sample
        sample_dict = ProteinSolubilityTask.data_preprocessing(
            sample_dict=sample_dict,
            protein_sequence_key="protein_seq",
            tokenizer_op=self.tokenizer_op,  # Rewrite tokenizer_op -> self.tokenizer_op
            device=self.model.device,  # -> self.model
        )

        # running in generate mode
        batch_dict = self.model.generate(  # model -> self.model
            [sample_dict],
            output_scores=True,
            return_dict_in_generate=True,
            max_new_tokens=5,
        )

        # Post-process the model's output
        result = ProteinSolubilityTask.process_model_output(  # Rename ans to result
            tokenizer_op=self.tokenizer_op,  # -> self.tokenizer_op
            decoder_output=batch_dict[CLS_PRED][0],
            decoder_output_scores=batch_dict[SCORES][0],
        )

        # Print prediction
        # TODO: Consider removing or replacing with logging.
        print(f"{result=}")  # ans -> result

        print(f'{result["not_normalized_scores"].shape=}')
        print(f'{len(result["not_normalized_scores"].shape)=}')
        print(f'{result["normalized_scores"].shape=}')
        if isinstance(result["not_normalized_scores"], torch.Tensor):
            result["not_normalized_scores"] = result["not_normalized_scores"].item()

        if isinstance(result["normalized_scores"], torch.Tensor):
            result["normalized_scores"] = result["normalized_scores"].item()

        # End copied, adapted model inference code------------------------------
        return result


# Register the wrapped-model class in global scope
ProteinSolubility.register(no_model=NO_MODEL)

if __name__ == "__main__":
    # Start the server so openad model service can connect:
    # `openad model `
    start_server(port=8080)
