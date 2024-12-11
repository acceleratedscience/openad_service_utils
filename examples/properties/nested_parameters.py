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
    algorithm_name: str = "smi_ted"
    algorithm_application: str = "qm8-e1-cam"
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
        "description": "QM8 E1-CAM: S0 -> S1 (first excited singlet state) transition energy computed at the level of theory, LR-TDCAM-B3LYP/def2TZVP",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.14",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-e1-cc2": {
        "param_id": "qm8-e1-cc2",
        "display_name": "qm8-e1-cc2",
        "description": "QM8 E1-CC2: S0 -> S1 (first excited singlet state) transition energy computed at the level of theory, RI-CC2/def2TZVP",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.14",
        "min_value": "-inf",
        "max_value": "inf",
    },
    # We know PBE0 is LR-TDPBE0/, but which PBE0? LR-TDPBE0/def2SVP? or LR-TDPBE0/def2TZVP?
    "qm8-e1-pbe0": {
        "param_id": "qm8-e1-pbe0",
        "display_name": "qm8-e1-pbe0",
        "description": "QM8 E1-PBE0: S0 -> S1 (first excited singlet state) transition energy computed at the level of theory, LR-TDPBE0/def2??VP", 
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.13",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-e2-cam": {
        "param_id": "qm8-e2-cam",
        "display_name": "qm8-e2-cam",
        "description": "QM8 E2-CAM: S0 -> S2 (second excited singlet state) transition energy computed at the level of theory, LR-TDCAM-B3LYP/def2TZV",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.14",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-e2-cc2": {
        "param_id": "qm8-e2-cc2",
        "display_name": "qm8-e2-cc2",
        "description": "QM8 E2-CC2: S0 -> S2 (second excited singlet state) transition energy computed at the level of theory, RI-CC2/def2TZVP",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.14",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-e2-pbe0": {
        "param_id": "qm8-e2-pbe0",
        "display_name": "qm8-e2-pbe0",
        "description": "QM8 E2-PBE0: S0 -> S2 (second excited singlet state) transition energy computed at the level of theory, LR-TDPBE0/def2??VP",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.13",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-f1-cam": {
        "param_id": "qm8-f1-cam",
        "display_name": "qm8-f1-cam",
        "description": "QM8 f2-CAM: S0 -> S1 (first excited singlet state) oscillator strength computed at the level of theory, LR-TDCAM-B3LYP/def2TZV",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.0022",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-f1-cc2": {
        "param_id": "qm8-f1-cc2",
        "display_name": "qm8-f1-cc2",
        "description": "QM8 f1-CC2: S0 -> S1 (first excited singlet state) oscillator strength computed at the level of theory, RI-CC2/def2TZVP",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.035",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-f1-pbe0": {
        "param_id": "qm8-f1-pbe0",
        "display_name": "qm8-f1-pbe0",
        "description": "QM8 f1-PBE0: S0 -> S1 (first excited singlet state) oscillator strength computed at the level of theory, LR-TDPBE0/def2??VP",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.0015",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-f2-cam": {
        "param_id": "qm8-f2-cam",
        "display_name": "qm8-f2-cam",
        "description": "QM8 f2-CAM: S0 -> S2 (second excited singlet state) oscillator strength computed at the level of theory, LR-TDCAM-B3LYP/def2TZV",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.0022",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-f2-cc2": {
        "param_id": "qm8-f2-cc2",
        "display_name": "qm8-f2-cc2",
        "description": "QM8 f2-CC2: S0 -> S2 (second excited singlet state) oscillator strength computed at the level of theory, RI-CC2/def2TZVP",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.035",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm8-f2-pbe0": {
        "param_id": "qm8-f2-pbe0",
        "display_name": "qm8-f2-pbe0",
        "description": "QM8 f2-PBE0: S0 -> S2 (second excited singlet state) oscillator strength computed at the level of theory, LR-TDPBE0/def2??VP",
        "type": "float",
        "example": "C[N]C1=C[N]C=NN1,0.0015",
        "min_value": "-inf",
        "max_value": "inf",
    },
}


NESTED_DATA_SETS["QM8"] = QM8

# Descriptions mostly from QM9 deepchem docs:
# https://deepchem.readthedocs.io/en/latest/api_reference/moleculenet.html#qm9-datasets
QM9 = {
    "qm9-alpha": {
        "param_id": "qm9-alpha",
        "display_name": "qm9-alpha",
        "description": "QM9 alpha: Isotropic polarizability (unit: Bohr^3)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,69.78",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-cv": {
        "param_id": "qm9-cv",
        "display_name": "qm9-cv",
        "description": "QM9 cv: Heat capacity at constant volume at 298.15K (unit: cal/(mol*K))",
        "type": "float",
        "example": "CN=C1NN=CN=C1,25.27",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-g298": {
        "param_id": "qm9-g298",
        "display_name": "qm9-g298",
        "description": "QM9 g298: Gibbs free energy at 298.15K (unit: Hartree)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,-374.928683",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-gap": {
        "param_id": "qm9-gap",
        "display_name": "qm9-gap",
        "description": "QM9 gap: Gap between HOMO and LUMO (unit: Hartree)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,0.1524",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-h298": {
        "param_id": "qm9-h298",
        "display_name": "qm9-h298",
        "description": "QM9 h298: Enthalpy at 298.15K (unit: Hartree)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,-374.889629",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-lumo": {
        "param_id": "qm9-lumo",
        "display_name": "qm9-lumo",
        "description": "QM9 lumo: Lowest unoccupied molecular orbital energy (unit: Hartree)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,-0.0712",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-homo": {
        "param_id": "qm9-homo",
        "display_name": "qm9-homo",
        "description": "QM9 homo: Highest occupied molecular orbital energy (unit: Hartree)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,-0.2235",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-mu": {
        "param_id": "qm9-mu",
        "display_name": "qm9-mu",
        "description": "QM9 mu: Dipole moment (unit: D)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,1.8376",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-r2": {
        "param_id": "qm9-r2",
        "display_name": "qm9-r2",
        "description": "QM9 r2: Electronic spatial extent (unit: Bohr^2)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,910.0644",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-u0": {
        "param_id": "qm9-u0",
        "display_name": "qm9-u0",
        "description": "QM9 u0: Internal energy at 0K (unit: Hartree)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,-374.897497",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-u298": {
        "param_id": "qm9-u298",
        "display_name": "qm9-u298",
        "description": "QM9 u298: Internal energy at 298.15K (unit: Hartree)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,-374.890574",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "qm9-zpve": {
        "param_id": "qm9-zpve",
        "display_name": "qm9-zpve",
        "description": "QM9 zpve: Zero point vibrational energy (unit: Hartree)",
        "type": "float",
        "example": "CN=C1NN=CN=C1,0.109182",
        "min_value": "-inf",
        "max_value": "inf",
    },
}
NESTED_DATA_SETS["QM9"] = QM9


molecule_net = {
    "bace": {
        "param_id": "bace",
        "display_name": "bace",
        "description": "MoleculeNet BACE: Inhibition of human beta secretase 1",
        "type": "float",
        "example": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O,0",
        "min_value": "0",
        "max_value": "1",
    },
    "bbbp": {
        "param_id": "bbbp",
        "display_name": "bbbp",
        "description": "MoleculeNe BBBP: Blood brain barrier penetration",
        "type": "float",
        "example": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O,0",
        "min_value": "0",
        "max_value": "1",
    },
    "clintox": {
        "param_id": "clintox",
        "display_name": "clintox",
        "description": "MoleculeNet ClinTox: Toxicity data of FDA-approved drugs and those that fail clinical trials",
        "type": "float",
        "example": "[N+](=O)([O-])[O-],1 0",
        "min_value": "0,0",
        "max_value": "1,1",
    },
    "esol": {
        "param_id": "esol",
        "display_name": "esol",
        "description": "MoleculeNet ESOL: Delaney water solubility data for organics",
        "type": "float",
        "example": "OCC3OC(OCC2OC(OC(C#N)c1ccccc1)C(O)C(O)C2O)C(O)C(O)C3O,-0.77",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "freesolv": {
        "param_id": "freesolv",
        "display_name": "freesolv",
        "description": "MoleculeNet FreeSolv: Hydration free energy",
        "type": "float",
        "example": "CN(C)C(=O)c1ccc(cc1)OC,-11.01",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "hiv": {
        "param_id": "hiv",
        "display_name": "hiv",
        "description": "MoleculeNe HIV: Inhibition of HIV viral replication",
        "type": "float",
        "example": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O,0",
        "min_value": "0",
        "max_value": "1",
    },
    # FIXME: What is iupac trained on, what does it return?
    "iupac": {
        "param_id": "iupac",
        "display_name": "iupac",
        "description": "MoleculeNet: IUPAC",
        "type": "float",
        "example": "Cn1c(CN2CCN(CC2)c3ccc(Cl)cc3)nc4ccccc14,<need result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    # FIXME: What is LD50 trained on; what does it return? LD50 is time to death for toxicity modeling, but what dataset?
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
        "description": "MoleculeNet Lipophilicity: Octonol/water distribution coeffficient",
        "type": "float",
        "example": "Cn1c(CN2CCN(CC2)c3ccc(Cl)cc3)nc4ccccc14,3.54",
        "min_value": "-inf",
        "max_value": "inf",
    },
    # FIXME: What is logkow trained on? logKow generally is or the octanol-water 
    # partition coefficient, is a unitless value that indicates how likely an 
    # organic compound is to be absorbed by soil and living organisms
    "logkow": {
        "param_id": "logkow",
        "display_name": "logkow",
        "description": "MoleculeNet: ",
        "type": "float",
        "example": "Cn1c(CN2CCN(CC2)c3ccc(Cl)cc3)nc4ccccc14,<need result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    # FIXME: What is multi_regression trained on?
    "multi_regression": {
        "param_id": "multi_regression",
        "display_name": "multi_regression",
        "description": "MoleculeNet:",
        "type": "float",
        "example": "Cn1c(CN2CCN(CC2)c3ccc(Cl)cc3)nc4ccccc14,<need result>",
        "min_value": "-inf",
        "max_value": "inf",
    },
    "sider": {
        "param_id": "sider",
        "display_name": "sider",
        "description": "MoleculeNet SIDER classifier: Side Effect Resource. Market drugs and their adverse drug reactions/side effects",
        "type": "float",
        "example": "C(CNCCNCCNCCN)N,1 1 0 0 1 1 1 0 0 0 0 1 0 0 0 0 1 0 0 1 1 0 0 1 1 1 0",
        "min_value": "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
        "max_value": "1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1",
    },
    "tox21": {
        "param_id": "tox21",
        "display_name": "tox21",
        "description": "MoleculeNet Tox21 classifier: Toxicity measurements on 12 different targets",
        "type": "float",
        "example": "CCOc1ccc2nc(S(N)(=O)=O)sc2c1,0 0 1 -1 -1 0 0 1 0 0 0 0",
        "min_value": "0,0,0,0,0,0,0,0,0,0,0,0",
        "max_value": "1,1,1,1,1,1,1,1,1,1,1,1",
    },
}
NESTED_DATA_SETS["molecule_net"] = molecule_net
