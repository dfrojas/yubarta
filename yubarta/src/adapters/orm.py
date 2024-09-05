from sqlalchemy import Table, MetaData, Column, String, Integer, ForeignKey
from sqlalchemy.orm import mapper, relationship
from ..domain import model

metadata = MetaData()

ebpf_programs = Table(
    "ebpf_programs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255)),
    Column("code", String),
    Column("attach_to", String(255)),
)

target_machines = Table(
    "target_machines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("hostname", String(255)),
    Column("username", String(255)),
    Column("ssh_key_path", String(255)),
)

ebpf_deployments = Table(
    "ebpf_deployments",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reference", String(255), unique=True),
    Column("ebpf_program_id", ForeignKey("ebpf_programs.id")),
    Column("target_machine_id", ForeignKey("target_machines.id")),
    Column("namespace", String(255)),
    Column("status", String(50)),
)

def start_mappers():
    mapper(model.EBPFProgram, ebpf_programs)
    mapper(model.TargetMachine, target_machines)
    mapper(model.EBPFDeployment, ebpf_deployments, properties={
        "ebpf_program": relationship(model.EBPFProgram),
        "target_machine": relationship(model.TargetMachine),
    })