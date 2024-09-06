import tempfile

import paramiko

from ..adapters import unit_of_work
from ..domain import model


def create_deployment(
    reference: str,
    ebpf_program: model.EBPFProgram,
    target_machine: model.TargetMachine,
    namespace: str,
    uow: unit_of_work.AbstractUnitOfWork,
) -> model.EBPFDeployment:
    with uow:
        deployment = model.EBPFDeployment(
            reference=reference,
            ebpf_program=ebpf_program,
            target_machine=target_machine,
            namespace=namespace,
        )
        uow.deployments.add(deployment)
        uow.commit()

        # Deploy eBPF program to target machine
        deploy_ebpf_program(deployment)

        return deployment


def get_deployment(
    reference: str, uow: unit_of_work.AbstractUnitOfWork
) -> model.EBPFDeployment:
    with uow:
        return uow.deployments.get(reference)


def list_deployments(
    uow: unit_of_work.AbstractUnitOfWork,
) -> list[model.EBPFDeployment]:
    with uow:
        return uow.deployments.list()


def deploy_ebpf_program(deployment: model.EBPFDeployment):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".c") as temp_file:
        temp_file.write(deployment.ebpf_program.code)
        temp_file.flush()

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=deployment.target_machine.hostname,
            username=deployment.target_machine.username,
            key_filename=deployment.target_machine.ssh_key_path,
        )

        sftp = ssh.open_sftp()
        remote_path = f"/tmp/{deployment.ebpf_program.name}.c"
        sftp.put(temp_file.name, remote_path)
        sftp.close()

        stdin, stdout, stderr = ssh.exec_command(f"""
            clang -O2 -target bpf -c {remote_path} -o /tmp/{deployment.ebpf_program.name}.o
            bpftool prog load /tmp/{deployment.ebpf_program.name}.o /sys/fs/bpf/{deployment.ebpf_program.name}
            bpftool prog attach {deployment.ebpf_program.name} {deployment.ebpf_program.attach_to}
        """)

        if stderr.channel.recv_exit_status() != 0:
            raise Exception(f"Error deploying eBPF program: {stderr.read().decode()}")

        ssh.close()

    deployment.status = "Deployed"
