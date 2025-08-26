# from engine.entities.models import EBPFDeployment, TargetMachine
# from engine.helpers.ssh import SSHClient
# from engine.controllers.injector import InjectorController


# class ConnectorController:
#     def __init__(self, deployment: EBPFDeployment):
#         self.deployment = deployment

#     def _connect_to_machine(self, machine: TargetMachine):
#         ssh_client = SSHClient(machine.hostname, machine.username, machine.ssh_key_path)
#         ssh_client.connect()

#         return ssh_client

#     def run(self):
#         code = self.deployment.program.code
#         for machine in self.deployment.machines:
#             client = self._connect_to_machine(machine)
#             InjectorController(client, self.deployment).run()
#             client.close()

#         return self.deployment
