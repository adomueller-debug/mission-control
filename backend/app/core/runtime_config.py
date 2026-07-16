from dataclasses import dataclass


@dataclass
class RuntimeConfig:
    model: str = "qwen2.5:7b"
    temperature: float = 0.2
    max_iterations: int = 5
    max_retries: int = 3
    timeout: int = 300


runtime_config = RuntimeConfig()
