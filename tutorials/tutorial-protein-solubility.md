## Simplest model-wrapping example: IBM Research biomedical omics protein solubility

For this example, we will wrap a protein solubility classifier using the MAMMAL
algorithm, an open source model [published on HuggingFace by BioMedical
Foundation Models (BMFM), IBM Research](https://huggingface.co/ibm-research/biomed.omics.bl.sm.ma-ted-458m.protein_solubility#usage).

This protein solubility predictor demonstrates the simplest case for wrapping a
model:

-   One model is wrapped at a time; that is, one model per class. _Later we will show
    how to wrap multiple models in a single class._
-   The model code already manages any needed model files: it stores them on
    HuggingFace Hub and downloads them locally when necessary.
    _OpenAD can also manage model files, but that requires
    some additional setup._

### Step 1: Start with the simplest code to run the model

To start wrapping the model, select the simplest code needed to run the model.
For this protein solubility classifier, let's use the code block [in the Usage section of biomed.omics...protein_solubility](https://huggingface.co/ibm-research/biomed.omics.bl.sm.ma-ted-458m.protein_solubility#usage):

```python
import os

from fuse.data.tokenizers.modular_tokenizer.op import ModularTokenizerOp

from mammal.examples.protein_solubility.task import ProteinSolubilityTask
from mammal.keys import CLS_PRED, SCORES
from mammal.model import Mammal

# Load Model
model = Mammal.from_pretrained("ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")
model.eval()

# Load Tokenizer
tokenizer_op = ModularTokenizerOp.from_pretrained("ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")

# convert to MAMMAL style
sample_dict = {"protein_seq": protein_seq}
sample_dict = ProteinSolubilityTask.data_preprocessing(
    sample_dict=sample_dict,
    protein_sequence_key="protein_seq",
    tokenizer_op=tokenizer_op,
    device=model.device,
)

# running in generate mode
batch_dict = model.generate(
    [sample_dict],
    output_scores=True,
    return_dict_in_generate=True,
    max_new_tokens=5,
)

# Post-process the model's output
ans = ProteinSolubilityTask.process_model_output(
    tokenizer_op=tokenizer_op,
    decoder_output=batch_dict[CLS_PRED][0],
    decoder_output_scores=batch_dict[SCORES][0],
)

# Print prediction
print(f"{ans=}")
```

### Step 2. Divide the model code into three consecutive parts

Divide the model code from step 1 into three consecutive parts. We will describe
how to copy each part into the wrapped model, with a few small changes.

Part 1. Imports. _Also anything else that must run before model setup. Runs once per session._

Part 2. Model setup. _Includes loading the model, and tokenizer (if any). Runs once per session._

Part 3. Model inference. _Includes model input. Runs once per inference, possibly many times per session._

![assets/model-code-simple-example-100-color.png?raw=true](assets/model-code-simple-example-100-color.png?raw=true)

### Step 3. Make a copy of implementation.py and rename it to suit the model

Make a copy of `openad_service_utils/examples/properties/implementation.py` .  
This will be your wrapped model. Give it a descriptive name that
suits the model.

For the protein solubility example, we rename our wrapped model, `protein_solubility_implementation.py`

### Step 4. Copy model imports into the wrapped model imports

Copy the imports, part 1 of the model code, into the wrapped model, right
after this line:

```python
# Wrapping Step 1: Copy the wrapped model's imports here:
```

After copying protein solubility imports into the wrapped model, here is the
wrapped model's imports. Notice the wrapper template, implementation.py, already
had `import os`, so we don't copy that.

```python
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
from fuse.data.tokenizers.modular_tokenizer.op import ModularTokenizerOp

from mammal.examples.protein_solubility.task import ProteinSolubilityTask
from mammal.keys import CLS_PRED, SCORES
from mammal.model import Mammal
```

### Step 5. Customize the wrapped model class name and 5 attributes

After the imports, change the template **class name**, `MyPredictor`, to suit
the model. Like most Python names, use PascalCase (LikeThis) for your class
name. Leave its parent class unchanged: `SimplePredictor`.

After the class name, customize the values of five required attributes:

**domain** is the general category of the model, expressed as an
instance of the class, `openad_service_utils.DomainSubmodule`. For property
predictors, that is one of these three:

-   `DomainSubmodule("molecules")` for properties of SMILES strings, typically
    small molecules.
-   `DomainSubmodule("proteins")` for properties of proteins represented as FASTA
    strings.
-   `DomainSubmodule("crystals")` for properties of materials as CIF files or
    other 3D representation.

**algorithm_name (str)** is the name of the model or algorithms. For models that
are part of a group, this is the name of the base model or algorithms common to
the group, usually in lower case or snake case (like_this).

**algorithm_application (str)** is the name of the task or use case for this
particular model instance, usually in lower case or snake case.

**algorithm_version (str)** is a version name for this model instance, or "v0"
by default.

**property_type (PredictorTypes)** is an enum type for the main input type of
the model: PredictorTypes.MOLECULE | PredictorTypes.PROTEIN | PredictorTypes.CRYSTAL

#### Customize MyPredictor for our protein solubility model

Back to our concrete example, wrapping a protein solubility predictor. Let's
complete step 5 by customizing MyPredictor for protein solubility.

-   The **class name** is ProteinSolubility.
-   **domain** is DomainSubmodule("proteins"), because the model takes protein
    FASTA strings as input.
-   **algorithm_name** is "mammal", because the model architecture is
    called MAMMAL. (For what MAMMAL stands for, see the
    [base model on GitHub](https://github.com/BiomedSciAI/biomed-multi-alignment).)
-   **algorithm_application** is "protein_solubility", snake case
    for the name of this model use case or task.
-   **algorithm_version** is "v0", the default.
-   **property_type** is PredictorTypes.PROTEIN, because the model input is
    a protein FASTA string.

Here is the top of our new, customized class, ProteinSolubility, in code:

```python
class ProteinSolubility(SimplePredictor):
    """...
    """
    domain: DomainSubmodule = DomainSubmodule("proteins")
    algorithm_name = "mammal"
    algorithm_application = "protein_solubility"
    algorithm_version = "v0"
    property_type = PredictorTypes.PROTEIN
```

### Step 6. Copy model setup code into the setup method; use instance variables

After customizing required class attributes, implement the setup method.

-   Copy model setup code into the `setup` method. (Model setup code is part 2
    of the original model code.) This includes any code to download or load the
    model, as well as the tokenizer, if any.
-   Add 'self.' to variables to transform them into instance variables. The
    variable `model`, say, becomes `self.model`, variable `tokenizer` becomes
    `self.tokenizer`, and so on. Do this for any values needed later in the
    `predict` method.

MAMMAL protein solubility model setup code looks like this:

```python
# Load Model
model = Mammal.from_pretrained("ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")
model.eval()

# Load Tokenizer
tokenizer_op = ModularTokenizerOp.from_pretrained("ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")
```

We copy this into our setup method and add `self.`, turning 3 mentions of
variables into instance variables:

```py
    def setup(self):
        """Model setup. Loads the model and tokenizer, if any. Runs once....
        """
        # Load Model
        self.model = Mammal.from_pretrained(
            "ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")
        self.model.eval()

        # Load Tokenizer
        self.tokenizer_op = ModularTokenizerOp.from_pretrained(
            "ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")
```

### Step 7. Copy model inference code into the predict method

Copy model inference code into the predict method, just as in the setup
method. Convert variables into instance variables by prefixing with `self.`

Here is part 3, inference code from protein solubility model.

**Main input** The main input is the variable `protein_seq`. This input occurs
in the first non-comment line of code, _and only there._

-   We mark all occurrences of `model` and `tokenizer_op` for us to convert to
    instance variables.

```py
# convert to MAMMAL style
sample_dict = {"protein_seq": protein_seq}  # <-- main input variable
sample_dict = ProteinSolubilityTask.data_preprocessing(
    sample_dict=sample_dict,
    protein_sequence_key="protein_seq",
    tokenizer_op=tokenizer_op,  # tokenizer_op (RHS only) -> self.tokenizer_op
    device=model.device,  # -> self.model
)

# running in generate mode
batch_dict = model.generate(  # -> self.model
    [sample_dict],
    output_scores=True,
    return_dict_in_generate=True,
    max_new_tokens=5,
)

# Post-process the model's output
ans = ProteinSolubilityTask.process_model_output(
    tokenizer_op=tokenizer_op,  # -> self.tokenizer_op
    decoder_output=batch_dict[CLS_PRED][0],
    decoder_output_scores=batch_dict[SCORES][0],
)

# Print prediction
print(f"{ans=}")
```

In the wrapped-model template `predict` method, the main input parameter is
`sample`. In the first line of model code, we rename protein_seq to `sample`,
so that it matches the input argument.

```py
    def predict(self, sample: Any):
        """Run inference code. Use instance variables for values from setup.
        """
        # Begin copied, adapted model inference code----------------------------
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

        # End copied, adapted model inference code------------------------------
        return result
```
