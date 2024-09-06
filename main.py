# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# import yaml
# import paramiko
# import tempfile

# app = FastAPI()

# class EBPFDeployment(BaseModel):
#     yaml_content: str

# @app.post("/deploy_ebpf")
# async def deploy_ebpf(deployment: EBPFDeployment):
#     try:
#         # Parse YAML
#         config = yaml.safe_load(deployment.yaml_content)

#         # Extract eBPF program and target machine details
#         ebpf_program = config['ebpf_program']
#         target_machine = config['target_machine']

#         # Create a temporary file for the eBPF program
#         with tempfile.NamedTemporaryFile(mode='w', suffix='.c') as temp_file:
#             temp_file.write(ebpf_program['code'])
#             temp_file.flush()

#             # Connect to the target machine via SSH
#             ssh = paramiko.SSHClient()
#             ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#             ssh.connect(
#                 hostname=target_machine['hostname'],
#                 username=target_machine['username'],
#                 key_filename=target_machine['ssh_key_path']
#             )

#             # Copy the eBPF program to the target machine
#             sftp = ssh.open_sftp()
#             remote_path = f"/tmp/{ebpf_program['name']}.c"
#             sftp.put(temp_file.name, remote_path)
#             sftp.close()

#             # Compile and load the eBPF program
#             stdin, stdout, stderr = ssh.exec_command(f"""
#                 clang -O2 -target bpf -c {remote_path} -o /tmp/{ebpf_program['name']}.o
#                 bpftool prog load /tmp/{ebpf_program['name']}.o /sys/fs/bpf/{ebpf_program['name']}
#                 bpftool prog attach {ebpf_program['name']} {ebpf_program['attach_to']}
#             """)

#             # Check for errors
#             if stderr.channel.recv_exit_status() != 0:
#                 raise Exception(f"Error deploying eBPF program: {stderr.read().decode()}")

#             ssh.close()

#         return {"message": "eBPF program deployed successfully"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
