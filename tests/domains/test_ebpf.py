from src.engine.domains.ebpf import (
    EBPFDeployment,
    EBPFDeploymentStatus,
    EBPFProgram,
    TargetMachine,
)


def test_ebpf_program_creation():
    program = EBPFProgram.create(
        name="Test Program", code="// BPF code", attach_to="eth0"
    )
    assert program.name == "Test Program"
    assert program.code == "// BPF code"
    assert program.attach_to == "eth0"
    assert isinstance(program.id, str)


def test_target_machine_creation():
    machine = TargetMachine.create(
        hostname="example.com", username="user", ssh_key_path="/path/to/key"
    )
    assert machine.hostname == "example.com"
    assert machine.username == "user"
    assert machine.ssh_key_path == "/path/to/key"
    assert isinstance(machine.id, str)


def test_ebpf_deployment_creation():
    program = EBPFProgram.create(
        name="Test Program", code="// BPF code", attach_to="eth0"
    )
    machine = TargetMachine.create(
        hostname="example.com", username="user", ssh_key_path="/path/to/key"
    )
    deployment = EBPFDeployment.create(
        reference="test-deployment",
        ebpf_program=program,
        target_machine=machine,
        namespace="default",
    )
    assert deployment.reference == "test-deployment"
    assert deployment.ebpf_program == program
    assert deployment.target_machine == machine
    assert deployment.namespace == "default"
    assert deployment.status == EBPFDeploymentStatus.PENDING
    assert isinstance(deployment.id, str)


def test_ebpf_deployment_deploy():
    program = EBPFProgram.create(
        name="Test Program", code="// BPF code", attach_to="eth0"
    )
    machine = TargetMachine.create(
        hostname="example.com", username="user", ssh_key_path="/path/to/key"
    )
    deployment = EBPFDeployment.create(
        reference="test-deployment",
        ebpf_program=program,
        target_machine=machine,
        namespace="default",
    )
    deployment.deploy()
    assert deployment.status == EBPFDeploymentStatus.DEPLOYED


def test_ebpf_deployment_fail():
    program = EBPFProgram.create(
        name="Test Program", code="// BPF code", attach_to="eth0"
    )
    machine = TargetMachine.create(
        hostname="example.com", username="user", ssh_key_path="/path/to/key"
    )
    deployment = EBPFDeployment.create(
        reference="test-deployment",
        ebpf_program=program,
        target_machine=machine,
        namespace="default",
    )
    deployment.fail()
    assert deployment.status == EBPFDeploymentStatus.FAILED
