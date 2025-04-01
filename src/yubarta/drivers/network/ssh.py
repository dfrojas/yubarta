import paramiko


class SSHClient:
    def __init__(
        self,
        host: str,
        username: str,
        ssh_key_path: str,
        port: int = 22,
        timeout: int = 10,
    ):
        self.host = host
        self.username = username
        self.ssh_key_path = ssh_key_path
        self.port = port
        self.timeout = timeout

    def connect(self):
        self.client = paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey.from_private_key_file(str(self.ssh_key_path))

        self.client.connect(
            hostname=self.host,
            username=self.username,
            pkey=private_key,
            port=self.port,
            timeout=self.timeout,
        )

    def exec_command(self, command: str) -> tuple[str, str, str]:
        try:
            _stdin, _stdout, _stderr = self.client.exec_command(command)
            exit_code = _stdin.channel.recv_exit_status()
            return (
                exit_code,
                _stdout.read().decode("utf-8"),
                _stderr.read().decode("utf-8"),
            )
        except Exception as e:
            return -1, "", str(e)
        # finally:
        #     self.close()

    def close(self):
        if self.client:
            self.client.close()
            self.client = None
