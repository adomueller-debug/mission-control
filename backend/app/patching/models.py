from dataclasses import dataclass


@dataclass
class Patch:
    path: str
    diff: str
