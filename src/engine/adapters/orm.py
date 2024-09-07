from sqlalchemy import Column, Integer, String, Table
from sqlalchemy.orm import registry

from engine.domains import EBPFProgram

mapper_registry = registry()

ebpf_programs = Table(
    "ebpf_program",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255)),
    Column("code", String),
    Column("attach_to", String(255)),
)


def start_mappers():
    mapper_registry.map_imperatively(EBPFProgram, ebpf_programs)
