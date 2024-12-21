from engine.entities.models import EBPFDeployment, TargetMachine
from engine.helpers.ssh import SSHClient


class DeploymentController:
    def __init__(self, deployment: EBPFDeployment):
        self.deployment = deployment

    def _connect_to_machine(self, machine: TargetMachine):
        ssh_client = SSHClient(machine.hostname, machine.username, machine.ssh_key_path)
        ssh_client.connect()

        return ssh_client

    def run(self):
        for machine in self.deployment.machines:
            client = self._connect_to_machine(machine)
            print(client.exec_command("ls -la")[1])  # Excute the deployment using the step by step class
        return self.deployment
