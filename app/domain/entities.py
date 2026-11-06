from dataclasses import dataclass


@dataclass(frozen=True)
class Student:
    id: int
    full_name: str
    email: str
    password_hash: str
