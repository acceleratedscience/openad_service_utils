"""       This library defines nested parameters
For each Service you wih to define place a Class of your Naming based on 
the below template then use it in the registration of the Function 
"""

from typing import List, Union, Dict, Any
from pydantic.v1 import Field
from openad_service_utils.common.properties.core import (
    PropertyPredictorParameters,
)
from openad_service_utils import SimplePredictor, PredictorTypes, DomainSubmodule, PropertyInfo


def get_property_list(propset: dict):
    """designed to build documentation for BMFMSM defived Examples
    e.g
    Property: <cmd>TRAINSET_CYP2D6</cmd>
    - Description: TRAINSET_CYP2D6
    - return type: float
    - Return value range: 0 to 1

    -Example: <cmd>get molecule property TRAINSET_CYP2D6 for CC(C)CC1=CC=C(C=C1)C(C)C(=O)O</cmd>

                result: 0

    """
    property_list = []
    for key, prop in propset.items():
        if prop["example"] == "":
            example = "N/A"
        else:
            example_return = prop["example"].split(",")[1].split(" ")
        if len(example_return) > 1:  # If example or / result is a range of results
            example_return = f"[ {','.join(example_return)} ] "
        else:
            example_return = example_return[0]
        example = f"""<cmd>get molecule property {prop['param_id']} for {prop['example'].split(',')[0]}</cmd>
        result: {example_return}"""

        help_element = f"""Property: <cmd>{prop['param_id']}</cmd>
- Description: {prop['display_name']} 
- return type: {prop['type']}
- Return value range: {prop['min_value'].split(',')[0]} to {prop['max_value'].split(',')[0]} 
-Example of command generating property {prop['param_id']}:    {example}
        """
        property_list.append(PropertyInfo(name=key, description=help_element))
    print(help_element)
    return property_list


class NestedParameters1(PropertyPredictorParameters):
    """Define you Parameter Template Here

    Parameters provided in the main class but not here will not be displayed to the OpenAD API..

    This is a great way to isolate Properties you do not want to expose to the user.

    """

    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "myproperty"
    algorithm_application: str = "MySimplePredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE

    available_properties: List[PropertyInfo] = [
        PropertyInfo(name="BACE", description=""),
        PropertyInfo(name="ESOL", description=""),
    ]
    temperature: int = Field(
        default=1,
        description="Algorithm temperature",
        example="0.5",
    )

    def set_parameters(self, algorithm_name, **kwargs):
        """sets the parameters when registering
        Available Properties to set
        - property_type
        - available_properties
        - algorithm_version
        """
        self.algorithm_name = algorithm_name

        for key, value in kwargs.items():
            if key == "property_type":
                self.property_type = value
            elif key == "available_properties":
                self.available_properties = value
            elif key == "algorithm_application":
                self.algorithm_application = value
            elif key == "algorithm_version":
                self.algorithm_version = value


class NestedParameters2(PropertyPredictorParameters):
    """Define you Parameter Template Here"""

    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "myproperty"
    algorithm_application: str = "MySimplePredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE

    available_properties: List[PropertyInfo] = [
        PropertyInfo(name="BACE", description=""),
        PropertyInfo(name="ESOL", description=""),
    ]

    def set_parameters(self, algorithm_name, **kwargs):
        """sets the parameters when registering
        Available Properties to set
        - property_type
        - available_properties
        - algorithm_version
        """
        self.algorithm_name = algorithm_name

        for key, value in kwargs.items():
            if key == "property_type":
                self.property_type = value
            elif key == "available_properties":
                self.available_properties = value
            elif key == "algorithm_application":
                self.algorithm_application = value
            elif key == "algorithm_version":
                self.algorithm_version = value


NESTED_DATA_SETS = {}

QM8 = {
    "qm8-e1-cam": {
        "param_id": "qm8-e1-cam",
        "display_name": "qm8-e1-cam",
        "description": "MoleculeNet: Dataset used in a study on modeling quantum mechanical calculations of electronic spectra and excited state energy of small molecules",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-e1-cc2": {
        "param_id": "qm8-e1-cc2",
        "display_name": "qm8-e1-cc2",
        "description": "MoleculeNet: Dataset used in a study on modeling quantum mechanical calculations of electronic spectra and excited state energy of small molecules",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-e1-pbe0": {
        "param_id": "qm8-e1-pbe0",
        "display_name": "qm8-e1-pbe0",
        "description": "MoleculeNet: Dataset used in a study on modeling quantum mechanical calculations of electronic spectra and excited state energy of small molecules",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-e2-cam": {
        "param_id": "qm8-e2-cam",
        "display_name": "qm8-e2-cam",
        "description": "MoleculeNet: Dataset used in a study on modeling quantum mechanical calculations of electronic spectra and excited state energy of small molecules",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-e2-cc2": {
        "param_id": "qm8-e2-cc2",
        "display_name": "qm8-e2-cc2",
        "description": "MoleculeNet: Dataset used in a study on modeling quantum mechanical calculations of electronic spectra and excited state energy of small molecules",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-e2-pbe0": {
        "param_id": "qm8-e2-pbe0",
        "display_name": "qm8-e2-pbe0",
        "description": "MoleculeNet: Dataset used in a study on modeling quantum mechanical calculations of electronic spectra and excited state energy of small molecules",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-f2-cam": {
        "param_id": "qm8-e1-cam",
        "display_name": "qm8-f2-cam",
        "description": "MoleculeNet: Dataset used in a study on modeling quantum mechanical calculations of electronic spectra and excited state energy of small molecules",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-f2-cc2": {
        "param_id": "qm8-f2-cc2",
        "display_name": "qm8-f2-cc2",
        "description": "MoleculeNet: Dataset used in a study on modeling quantum mechanical calculations of electronic spectra and excited state energy of small molecules",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-f2-pbe0": {
        "param_id": "qm8-f2-pbe0",
        "display_name": "qm8-f2-pbe0",
        "description": "MoleculeNet: Dataset used in a study on modeling quantum mechanical calculations of electronic spectra and excited state energy of small molecules",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
}


NESTED_DATA_SETS["QM8"] = QM8
QM9 = {
    "qm9-alpha": {
        "param_id": "qm9-alpha",
        "display_name": "qm9-alpha",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-cv": {
        "param_id": "qm9-cv",
        "display_name": "qm9-cv",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-298": {
        "param_id": "qm9-298",
        "display_name": "qm9-298",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-gap": {
        "param_id": "qm9-gap",
        "display_name": "qm9-gap",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-h298": {
        "param_id": "qm9-h298",
        "display_name": "qm9-h298",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-lumo": {
        "param_id": "qm9-lumo",
        "display_name": "qm9-lumo",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-homo": {
        "param_id": "qm9-homo",
        "display_name": "qm9-homo",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-mu": {
        "param_id": "qm9-mu",
        "display_name": "qm9-mu",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-r2": {
        "param_id": "qm9-r2",
        "display_name": "qm9-r2",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-u0": {
        "param_id": "qm9-u0",
        "display_name": "qm9-u0",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-u298": {
        "param_id": "qm9-u298",
        "display_name": "qm9-u298",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-zpve": {
        "param_id": "qm9-zpve",
        "display_name": "qm9-zpve",
        "description": "MoleculeNet: Dataset that provides geometric/energetic/electronic and thermodynamic properties for a subset of GDB-17 database",
        "type": "float",
        "example": "Cc1cccc(N2CCN(C(=O)C34CC5CC(CC(C5)C3)C4)CC2)c1C, <need_result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
}
NESTED_DATA_SETS["QM9"] = QM9
molecule_net = {
    "bace": {
        "param_id": "bace",
        "display_name": "bace",
        "description": "MoleculeNet: Inhibition of human beta secretase 1",
        "type": "float",
        "example": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O,0",
        "min_value": "0",
        "max_value": "1",
    },
    "bbbp": {
        "param_id": "bbbp",
        "display_name": "bbbp",
        "description": "MoleculeNet: Blood brain barrier penetration",
        "type": "float",
        "example": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O,0",
        "min_value": "0",
        "max_value": "1",
    },
    "clintox": {
        "param_id": "clintox",
        "display_name": "clintox",
        "description": "MoleculeNet: Toxicity data of FDA-approved drugs and those that fail clinical trials",
        "type": "float",
        "example": "[N+](=O)([O-])[O-],1 0",
        "min_value": "0,0",
        "max_value": "1,1",
    },
    "esol": {
        "param_id": "esol",
        "display_name": "esol",
        "description": "MoleculeNet: Water solubility data for organics",
        "type": "float",
        "example": "OCC3OC(OCC2OC(OC(C#N)c1ccccc1)C(O)C(O)C2O)C(O)C(O)C3O,-0.77",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "freesolv": {
        "param_id": "freesolv",
        "display_name": "freesolv",
        "description": "MoleculeNet: Hydration free energy",
        "type": "float",
        "example": "CN(C)C(=O)c1ccc(cc1)OC,-11.01",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "hiv": {
        "param_id": "hiv",
        "display_name": "hiv",
        "description": "MoleculeNet: Inhibition of HIV viral replication",
        "type": "float",
        "example": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O,0",
        "min_value": "0",
        "max_value": "1",
    },
    "iupac": {
        "param_id": "iupac",
        "display_name": "iupac",
        "description": "MoleculeNet:t",
        "type": "float",
        "example": "Cn1c(CN2CCN(CC2)c3ccc(Cl)cc3)nc4ccccc14,<need result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "ld50": {
        "param_id": "ld50",
        "display_name": "ld50",
        "description": "MoleculeNet: ",
        "type": "float",
        "example": "Cn1c(CN2CCN(CC2)c3ccc(Cl)cc3)nc4ccccc14,<need result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "lipo": {
        "param_id": "lipo",
        "display_name": "lipo",
        "description": "MoleculeNet: Octonol/water distribution coeffficient",
        "type": "float",
        "example": "Cn1c(CN2CCN(CC2)c3ccc(Cl)cc3)nc4ccccc14,3.54",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "logkow": {
        "param_id": "logkow",
        "display_name": "logkow",
        "description": "MoleculeNet: ",
        "type": "float",
        "example": "Cn1c(CN2CCN(CC2)c3ccc(Cl)cc3)nc4ccccc14,<need result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "multi_regression": {
        "param_id": "multi_regression",
        "display_name": "multi_regression",
        "description": "MoleculeNet:t",
        "type": "float",
        "example": "Cn1c(CN2CCN(CC2)c3ccc(Cl)cc3)nc4ccccc14,<need result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "sider": {
        "param_id": "sider",
        "display_name": "sider",
        "description": "MoleculeNet: Side Effect Resource.  Market drugs and their adverse drug reactions/side effects",
        "type": "float",
        "example": "C(CNCCNCCNCCN)N,1 1 0 0 1 1 1 0 0 0 0 1 0 0 0 0 1 0 0 1 1 0 0 1 1 1 0",
        "min_value": "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "max_value": "1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1",
    },
    "tox21": {
        "param_id": "tox21",
        "display_name": "tox21",
        "description": "MoleculeNet: Toxicity against set of targets",
        "type": "float",
        "example": "CCOc1ccc2nc(S(N)(=O)=O)sc2c1,0 0 1 -1 -1 0 0 1 0 0 0 0",
        "min_value": "0,0,0,0,0,0,0,0,0,0,0,0",
        "max_value": "1,1,1,1,1,1,1,1,1,1,1,1",
    },
}
NESTED_DATA_SETS["molecule_net"] = molecule_net
