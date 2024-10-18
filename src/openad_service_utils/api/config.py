from pydantic.dataclasses import dataclass

@dataclass
class ServerConfig:
    AUTO_CLEAR_GPU_MEM: bool = True
    AUTO_GARABAGE_COLLECT: bool = True