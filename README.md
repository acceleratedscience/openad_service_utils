# OpenAD Model Wrapper, a library to onboard models to OpenAD toolkit

[![License MIT](https://img.shields.io/github/license/acceleratedscience/openad_service_utils)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Docs](https://img.shields.io/badge/website-live-brightgreen)](https://acceleratedscience.github.io/openad-docs/)  
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

## Install OpenAD model wrapper

Requirements:

- Linux or Macos  
- Python 3.10.10+ or 3.11  

Install the latest OpenAD model wrapper by tag:

```shell
pip install git+https://github.com/acceleratedscience/openad_service_utils.git@0.3.1
```

## Why use OpenAD model wrapper?

Here are the top reasons to use OpenAD Model Wrapper:

- You want to use your model to build workflows in OpenAD toolkit.
- You want to run inference on your model in a FastAPI service with a minimum of
new code required.
- You want to containerize your model in Kubernetes (e.g. OpenShift), Docker, Podman, etc.

OpenAD model wrapper simplifies building model containers, by following the
standard used by other models available in OpenAD model service.

## Simplest example: wrap one model at a time

For this example, we will wrap a protein solubility classifier using the MAMMAL
algorithm, an open source model [published on HuggingFace by BioMedical
Foundation Models (BMFM), IBM Research](https://huggingface.co/ibm-research/biomed.omics.bl.sm.ma-ted-458m.protein_solubility#usage).

This protein solubility predictor demonstrates the simplest case for wrapping a
model:

- One model is wrapped at a time; that is, one model per class. _Later we will show
how to wrap multiple models in a single class._
- The model code already manages any needed model files: it stores them on
HuggingFace Hub and downloads them locally when necessary.
_OpenAD can also manage model files, but that requires
[some additional setup](https://TODO_link_to_Setup_Cloud_Model_Storage)._

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

### Step 2. Divide the model code into three consecutive parts:

Part 1. Imports. _Also anything else that must run before model setup. Runs once per session._

Part 2. Model setup. _Includes loading the model, and tokenizer (if any). Runs once per session._

Part 3. Model inference. _Includes model input. Runs once per inference, possibly many times per session._  

![assets/model-code-simple-example-100-color.png?raw=true](assets/model-code-simple-example-100-color.png?raw=true)

### Step 3. Make a copy of implementation.py and rename it to suit the model

Make a copy of `openad_service_utils/examples/properties/implementation.py` .  
This will be your wrapped model. You can give it a descriptive name that
fits the model.

For the protein solubility example, we rename our wrapped model, `protein_solubility_implementation.py`

### Step 4. Copy model imports into the wrapped model imports

Copy the imports, part 1 of the model code, into the wrapped model, right
after this line:

```python
# Wrapping Step 1: Copy your model's imports here:
```

### Step 5v1. Customize the wrapped model class name and 5 attributes

After the imports, change the template **class name**, `MyPredictor`, to suit
the model. Leave its parent class unchanged: `SimplePredictor`

For our example, protein solubility, it looks like this:

```python
class ProteinSolubility(SimplePredictor):
```

Next, customize the values of the 5 required attributes:

**domain** is the general category of the model, expressed as an
instance of the class, `openad_service_utils.DomainSubmodule`. For properties,
that is usually one of these three:

- `DomainSubmodule("molecules")` for properties of SMILES strings, typically
small molecules.
- `DomainSubmodule("proteins")` for properties of proteins represented as FASTA strings.
- `DomainSubmodule("crystals")` for properties of materials as CIF files or
other 3D representation.

Our example, protein solubility, takes proteins as FASTA strings, so we chooose DomainSubmodule("proteins"):

```python
domain: DomainSubmodule = DomainSubmodule("proteins")
```

**algorithm_name (str)** is the name of the model or algorithms. For models that
are part of a group, this is the name of the base model or algorithms common to
the group, usually in lower case or snake case (like_this).

Our example, protein solubility, is finetuned from base model, 
[biomed.omics.bl.sm.ma-ted-458m](https://huggingface.co/ibm-research/biomed.omics.bl.sm.ma-ted-458m). This model is based on an architecture called MAMMAL. We use
the name "mammal", easy to remember and type.

```python
algorithm_name = "mammal"
```

**algorithm_application (str)** is the name of the task or use case for this
particular model instance, usually in lower case or snake case.

Our example is protein solubility, and this is also the name of the application
(use case or task) for this model instance. We put it in snake case:

```python
algorithm_application = "protein_solubility"
```

**algorithm_version (str)** is a version name for this model instance, or "v0"
by default.

Our example chooses the default, "v0":

```python
algorithm_version = "v0"
```

**property_type (PredictorTypes)** is an enum type for the main input type of
the model: PredictorTypes.MOLECULE | PredictorTypes.PROTEIN | PredictorTypes.CRYSTAL

Our example, protein solubility, takes a FASTA string for a protein:

```python
property_type = PredictorTypes.PROTEIN
```

### Step 5v2. (alternate version) Customize the wrapped model class name and 5 attributes

After the imports, change the template **class name**, `MyPredictor`, to suit
the model. Like most Python names, use PascalCase (LikeThis) for your class
name. Leave its parent class unchanged: `SimplePredictor` .

After the class name, customize the values of five required attributes:

**domain** is the general category of the model, expressed as an
instance of the class, `openad_service_utils.DomainSubmodule`.  For property
predictors, that is one of these three:  

- `DomainSubmodule("molecules")` for properties of SMILES strings, typically
small molecules.
- `DomainSubmodule("proteins")` for properties of proteins represented as FASTA
strings.
- `DomainSubmodule("crystals")` for properties of materials as CIF files or
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

- The **class name** is ProteinSolubility.
- **domain** is DomainSubmodule("proteins"), because the model takes protein
FASTA strings as input.
- **algorithm_name** is "mammal", because the model architecture is
called MAMMAL. (For what MAMMAL stands for, see the
[base model on GitHub](https://github.com/BiomedSciAI/biomed-multi-alignment).)
- **algorithm_application** is "protain_solubility", snake case
for the name of this model use case or task.
- **algorithm_version** is "v0", the default.
- **property_type** is PredictorTypes.PROTEIN, because the model input is
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

### Step 6. Copy model setup code into the setup method, using instance variables

After customizing required class attributes, we implement the setup method.  

- Copy model setup code into the `setup` method. (Model setup code is part 2
of the original model code.) This includes any code to download or load the
model, as well as the tokenizer, if any.
- Add 'self.' to variables to transform them into instance variables. The
variable `model`, say, becomes `self.model`, variable `tokenizer` becomes
`self.tokenizer`, and so on. Do this for any values needed later in the
`predict` method.

Model setup code in our protein solubility model looks like this:

```python
# Load Model
model = Mammal.from_pretrained("ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")
model.eval()

# Load Tokenizer
tokenizer_op = ModularTokenizerOp.from_pretrained("ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")
```

We copy this into our setup method and add `self.`, turning 3 mentions of
variables into instance variables:

```python
    def setup(self):
        """ ...
        """
        # Load Model
        self.model = Mammal.from_pretrained("ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")
        self.model.eval()

        # Load Tokenizer
        self.tokenizer_op = ModularTokenizerOp.from_pretrained("ibm/biomed.omics.bl.sm.ma-ted-458m.protein_solubility")
```




## Advanced

### Use your own private model not hosted on public OpenAD S3 bucket

To use your own private model cloud object store, set the following variables in the os host or python script to your private s3 buckets:

```python
import os
os.environ["OPENAD_S3_HOST"] = "s3.<region>.amazonaws.com"
os.environ["OPENAD_S3_ACCESS_KEY"] = ""
os.environ["OPENAD_S3_SECRET_KEY"] = ""
os.environ["OPENAD_S3_HOST_HUB"] = "s3.<region>.amazonaws.com"
os.environ["OPENAD_S3_ACCESS_KEY_HUB"] = ""
os.environ["OPENAD_S3_SECRET_KEY_HUB"] = ""
```

### Allow Asynchronous results
Set `ASYNC_ALLOW` to `True` to configure your inference service as ansynchronous.
With this enabled, each inference job is assigned a unique, random id using
UUID. The system stores the result for 3 days before it is deleted. The
inference user can request the result using the job id at any time in the 3 days.

```python
import os
os.environ["ASYNC_ALLOW"] = True 
```

Example:

```text
OpenAD:DEFAULT >>  pserve generate with MySimpleGenerator data for "{'<esol>': -3.2}"  sample 4 async
✔ Request Returned
{'id': '8c2cfb68-b037-11ef-9223-acde48001122'}
OpenAD:DEFAULT >>  get model service 'pserve' result '8c2cfb68-b037-11ef-9223-acde48001122'
job is still running
OpenAD:DEFAULT >>  get model service 'pserve' result '8c2cfb68-b037-11ef-9223-acde48001122'

  pred1    pred2
-------  -------
      1        2

Next up, you can run: result open/edit/copy/display/as dataframe/save [as '<filename.csv>']

```

## Experimental Settings
The following are Experimental or Advanced Settings that can be included as Environmental Variables

### AUTO_CLEAR_GPU_MEM
Clears the GPU memory for an Inference call  
    Default: `AUTO_CLEAR_GPU_MEM: bool = True`
### AUTO_GARABAGE_COLLECT
Calls the Garbage Collector after an Inference call  
    Default `AUTO_GARABAGE_COLLECT: bool = True`
### SERVE_MAX_WORKERS
Enables Multi-Processing of synchronous Calls, Defaults to 1 Thread for safety, depends on performance sizing whether you choose to use more than 1.  
    Default: `SERVE_MAX_WORKERS: int = -1`
### ENABLE_CACHE_RESULTS
Enables Caching of Results for command requests, this should only be activated for Deterministic Requests, no functions that use random seeds should this be activated for.<br>
    Default: `ENABLE_CACHE_RESULTS: bool = False`
### ASYNC_POOL_MAX
The Default value for Asynchronous requests is 1, this is so server capacity is managed to the minimum. It is up to the developer and Deployer of a service to set this higher than 1 based on benchmarking. <br>   
    Default `ASYNC_POOL_MAX: int = 1`


## Local Cache locations for models

### Generation Models location

`~/.openad_models / algorithms / algorithm_type / algorithm_name / algorithm_application / algorithm_version`

### Property Models location

`~/.openad_models / properties / domain / algorithm_name / algorithm_application / algorithm_version`
