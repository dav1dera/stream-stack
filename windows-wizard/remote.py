from __future__ import annotations

import base64
import hashlib
import posixpath
import shlex
import time
from typing import Callable

import paramiko


class RemoteError(RuntimeError):
    pass


class SSHSession:
    """Small SSH/SFTP wrapper used by the Windows GUI.

    The GUI owns the lifecycle. Commands are never executed locally on Windows.
    """

    def __init__(self) -> None:
        self.client: paramiko.SSHClient | None = None
        self.home = ""
        self.fingerprint = ""

    def connect(
        self,
        host: str,
        port: int,
        username: str,
        password: str = "",
        key_path: str = "",
        key_passphrase: str = "",
    ) -> None:
        self.close()
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs: dict[str, object] = {
            "hostname": host,
            "port": port,
            "username": username,
            "timeout": 10,
            "banner_timeout": 10,
            "auth_timeout": 15,
            "look_for_keys": not bool(key_path or password),
            "allow_agent": True,
        }
        if password:
            kwargs["password"] = password
        if key_path:
            kwargs["key_filename"] = key_path
            if key_passphrase:
                kwargs["passphrase"] = key_passphrase
        client.connect(**kwargs)
        transport = client.get_transport()
        if not transport or not transport.is_active():
            client.close()
            raise RemoteError("SSH transport is not active")
        key = transport.get_remote_server_key()
        digest = hashlib.sha256(key.asbytes()).digest()
        self.fingerprint = "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")
        self.client = client
        self.home = self.capture("printf '%s' \"$HOME\"").strip()

    def close(self) -> None:
        if self.client:
            self.client.close()
        self.client = None
        self.home = ""
        self.fingerprint = ""

    def _require(self) -> paramiko.SSHClient:
        if not self.client:
            raise RemoteError("Not connected")
        return self.client

    def capture(self, command: str, timeout: int = 60) -> str:
        client = self._require()
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        code = stdout.channel.recv_exit_status()
        if code != 0:
            raise RemoteError(err.strip() or out.strip() or f"Command failed ({code}): {command}")
        return out

    def stream(
        self,
        command: str,
        emit: Callable[[str], None],
        timeout: int = 3600,
        sudo_password: str = "",
        use_sudo: bool = False,
    ) -> int:
        client = self._require()
        if use_sudo:
            if sudo_password:
                wrapped = f"sudo -S -p '' bash -lc {shlex.quote(command)}"
            else:
                wrapped = f"sudo -n bash -lc {shlex.quote(command)}"
        else:
            wrapped = command

        transport = client.get_transport()
        if not transport:
            raise RemoteError("SSH transport is unavailable")
        chan = transport.open_session(timeout=15)
        chan.get_pty(width=180, height=45)
        chan.exec_command(wrapped)
        if use_sudo and sudo_password:
            chan.send(sudo_password + "\n")

        started = time.time()
        buffer = b""
        while True:
            if chan.recv_ready():
                buffer += chan.recv(65535)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    emit(line.decode("utf-8", "replace").rstrip("\r"))
            if chan.recv_stderr_ready():
                data = chan.recv_stderr(65535).decode("utf-8", "replace")
                for line in data.splitlines():
                    emit(line)
            if chan.exit_status_ready():
                while chan.recv_ready():
                    buffer += chan.recv(65535)
                if buffer:
                    emit(buffer.decode("utf-8", "replace").rstrip())
                return chan.recv_exit_status()
            if time.time() - started > timeout:
                chan.close()
                raise RemoteError(f"Remote command timed out after {timeout}s")
            time.sleep(0.05)

    def resolve(self, path: str) -> str:
        path = path.strip()
        if path == "~":
            return self.home
        if path.startswith("~/"):
            return posixpath.join(self.home, path[2:])
        if not path.startswith("/"):
            return posixpath.join(self.home, path)
        return path

    def put_text(self, remote_path: str, text: str, mode: int = 0o600) -> None:
        client = self._require()
        path = self.resolve(remote_path)
        folder = posixpath.dirname(path)
        self.capture(f"mkdir -p {shlex.quote(folder)}")
        temp = path + ".tmp-stream-stack-wizard"
        sftp = client.open_sftp()
        try:
            with sftp.file(temp, "wb") as handle:
                handle.write(text.encode("utf-8"))
                handle.flush()
            sftp.chmod(temp, mode)
            try:
                sftp.rename(temp, path)
            except OSError:
                try:
                    sftp.remove(path)
                except OSError:
                    pass
                sftp.rename(temp, path)
            sftp.chmod(path, mode)
        finally:
            sftp.close()

    def read_text(self, remote_path: str) -> str:
        client = self._require()
        path = self.resolve(remote_path)
        sftp = client.open_sftp()
        try:
            with sftp.file(path, "rb") as handle:
                data = handle.read()
        finally:
            sftp.close()
        if isinstance(data, str):
            return data
        return data.decode("utf-8", "replace")
