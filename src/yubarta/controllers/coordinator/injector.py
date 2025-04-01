# from engine.entities.models import EBPFDeployment
# from engine.helpers.ssh import SSHClient
# from pathlib import Path


# class InjectorController:
#     def __init__(self, client: SSHClient, deployment: EBPFDeployment):
#         self.client = client
#         self.deployment = deployment
#         home_dir = self.client.exec_command("echo $HOME")[1].strip()
#         self.program_dir = f"{home_dir}/yubarta_ebpf_programs"

#     def _create_program_dir(self):
#         self.client.exec_command(f"mkdir -p {self.program_dir}")

#     def _store_program(self):
#         local_program_path = self.deployment.program.code
#         remote_program_path = f"{self.program_dir}/{self.deployment.program.name}.py"

#         sftp = self.client.client.open_sftp()  # REMINDER: Why client.client?
#         sftp.put(local_program_path, remote_program_path)
#         sftp.close()  # REMINDER: We have to close here as well?

#         return remote_program_path

#     def run(self):
#         self._create_program_dir()
#         if self.deployment.program.code.endswith(".py"):
#             program_path = self._store_program()
#             command = self.client.exec_command(f"python3 {program_path}")
#             print(f"Exit code: {command[0]}")
#             print(f"Stdout: {command[1]}")
#             print(f"Stderr: {command[2]}")
#         else:
#             command = self.client.exec_command(self.deployment.program.code)
#             print(f"Exit code: {command[0]}")
#             print(f"Stdout: {command[1]}")
#             print(f"Stderr: {command[2]}")
