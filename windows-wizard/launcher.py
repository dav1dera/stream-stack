from __future__ import annotations

import json
import posixpath
import shlex
import time

import customtkinter as ctk

import app as base
from remote import RemoteError, SSHSession

# Make the base GUI instantiate the hardened transport implementation.
base.SSHSession = SSHSession


CREDENTIAL_KEYS = [
    ("NPM_ADMIN_EMAIL", "NPM admin email"),
    ("NPM_ADMIN_PASSWORD", "NPM admin password"),
    ("AIO_USER", "AIOStreams user"),
    ("AIO_PASSWORD", "AIOStreams password"),
    ("AIO_CONFIG_ACCESS_KEY", "AIOStreams config access key"),
    ("STREMTHRU_USER", "StremThru user"),
    ("STREMTHRU_PASSWORD", "StremThru password"),
    ("SEANIME_MAIN_PASSWORD", "Seanime password"),
    ("SEANIME_SHARED_PASSWORD", "Seanime Shared password"),
    ("MEDIAFLOW_PASSWORD", "MediaFlow password"),
    ("COMET_ADMIN_PASSWORD", "Comet admin password"),
    ("COMET_CONFIG_PASSWORD", "Comet config password"),
    ("COMET_PUBLIC_API_TOKEN", "Comet / CometNet API token"),
    ("POSTGRES_PASSWORD", "PostgreSQL shared password"),
    ("HEADSCALE_API_KEY", "Headscale API key"),
    ("JACKETT_API_KEY", "Jackett API key"),
]


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = value[1:-1]
        elif len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


class Wizard(base.Wizard):
    def __init__(self) -> None:
        self.generated_credentials: dict[str, str] = {}
        self.credential_entries: list[ctk.CTkEntry] = []
        super().__init__()

    def _reconnect(self) -> None:
        self.session.close()
        self.connected = False
        time.sleep(0.8)
        self.ensure_connected(force=True)

    def _deploy_worker(self) -> None:
        def emit(line: str) -> None:
            self.events.put(("log", line))

        try:
            self.ensure_connected(force=True)
            remote_dir = self.session.resolve(self.var("REMOTE_DIR").get())

            self.events.put(("deploy_status", ("Verifica prerequisiti…", 0.08)))
            probe = self.session.capture(
                "command -v git >/dev/null 2>&1 || echo MISSING:git; "
                "command -v python3 >/dev/null 2>&1 || echo MISSING:python3; "
                "command -v docker >/dev/null 2>&1 || echo MISSING:docker; "
                "docker compose version >/dev/null 2>&1 || echo MISSING:compose"
            )
            missing_tools = [line.split(":", 1)[1] for line in probe.splitlines() if line.startswith("MISSING:")]
            if missing_tools:
                emit("Prerequisiti mancanti: " + ", ".join(missing_tools))
                if not self.bool_var("INSTALL_PREREQS").get():
                    raise RemoteError(
                        "Mancano prerequisiti sul server: " + ", ".join(missing_tools) +
                        ". Torna a Opzionali e abilita 'Installa prerequisiti', oppure installali manualmente."
                    )
                self.events.put(("deploy_status", ("Installazione prerequisiti…", 0.13)))
                install = r"""
set -e
apt-get update
apt-get install -y ca-certificates curl git python3
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != root ]; then
  usermod -aG docker "$SUDO_USER"
fi
""".strip()
                sudo_pw = self.var("SUDO_PASSWORD").get() or self.var("SSH_PASSWORD").get()
                code = self.session.stream(install, emit, timeout=1200, sudo_password=sudo_pw, use_sudo=True)
                if code != 0:
                    raise RemoteError("Installazione prerequisiti fallita")
                emit("Riapertura SSH per applicare l'eventuale membership nel gruppo docker…")
                self._reconnect()

            docker_access = self.session.capture(
                "if docker info >/dev/null 2>&1; then echo OK; else echo NO; fi"
            ).strip()
            if docker_access != "OK":
                if self.bool_var("INSTALL_PREREQS").get():
                    sudo_pw = self.var("SUDO_PASSWORD").get() or self.var("SSH_PASSWORD").get()
                    user = self.var("SSH_USER").get().strip()
                    emit(f"Aggiunta di {user} al gruppo docker…")
                    code = self.session.stream(
                        f"usermod -aG docker {shlex.quote(user)}",
                        emit,
                        timeout=60,
                        sudo_password=sudo_pw,
                        use_sudo=True,
                    )
                    if code == 0:
                        self._reconnect()
                        docker_access = self.session.capture(
                            "if docker info >/dev/null 2>&1; then echo OK; else echo NO; fi"
                        ).strip()
                if docker_access != "OK":
                    raise RemoteError(
                        "L'utente SSH non può accedere al daemon Docker. Aggiungilo al gruppo docker e riapri la sessione SSH."
                    )

            self.events.put(("deploy_status", ("Clone / aggiornamento repository…", 0.20)))
            parent = posixpath.dirname(remote_dir)
            clone_cmd = (
                f"mkdir -p {shlex.quote(parent)} && "
                f"if [ -d {shlex.quote(remote_dir)}/.git ]; then "
                f"git -C {shlex.quote(remote_dir)} pull --ff-only; "
                f"else git clone {shlex.quote(base.REPO_URL)} {shlex.quote(remote_dir)}; fi"
            )
            if self.session.stream(clone_cmd, emit, timeout=300) != 0:
                raise RemoteError("Clone/aggiornamento repository fallito")

            self.events.put(("deploy_status", ("Scrittura setup.env sicuro…", 0.28)))
            setup_path = posixpath.join(remote_dir, "setup.env")
            self.session.put_text(setup_path, self.setup_env_text(), 0o600)
            emit("setup.env scritto direttamente via SFTP con mode 0600")

            self.events.put(("deploy_status", ("Esecuzione setup Linux e NPM…", 0.38)))
            setup_cmd = (
                f"cd {shlex.quote(remote_dir)} && "
                "chmod +x setup.sh scripts/bootstrap.sh && ./setup.sh --non-interactive"
            )
            if self.session.stream(setup_cmd, emit, timeout=1800) != 0:
                raise RemoteError("setup.sh ha restituito un errore")

            # setup.sh writes generated local/runtime secrets back to setup.env.
            # Bring only the values needed by the final GUI into Windows memory.
            resolved = parse_env(self.session.read_text(setup_path))
            self.generated_credentials = {
                key: resolved.get(key, "")
                for key, _ in CREDENTIAL_KEYS
                if resolved.get(key, "")
            }

            if self.bool_var("START_FULL_STACK").get():
                self.events.put(("deploy_status", ("Avvio stack completo…", 0.78)))
                up_cmd = f"cd {shlex.quote(remote_dir)} && docker compose --profile all up -d"
                if self.session.stream(up_cmd, emit, timeout=1800) != 0:
                    raise RemoteError("Avvio dello stack fallito")

            self.events.put(("deploy_status", ("Verifica container…", 0.90)))
            status_cmd = f"cd {shlex.quote(remote_dir)} && docker compose --profile all ps"
            status = self.session.capture(status_cmd, timeout=120)
            emit(status.rstrip())
            self.events.put(("deploy_done", status))
        except Exception as exc:
            self.events.put(("deploy_error", str(exc)))

    def build_complete(self) -> None:
        super().build_complete()
        children = self.content_holder.winfo_children()
        if not children:
            return
        page = children[0]
        if not self.generated_credentials:
            return

        body = self.card(
            page,
            "Credenziali generate",
            "Questi valori sono stati letti dal setup.env remoto via SSH e restano solo nella memoria del wizard Windows.",
        )
        self.credential_entries = []
        row = 0
        for key, label in CREDENTIAL_KEYS:
            value = self.generated_credentials.get(key)
            if not value:
                continue
            ctk.CTkLabel(body, text=label, text_color="#D7E1F0", anchor="w").grid(
                row=row, column=0, sticky="w", pady=5
            )
            var = ctk.StringVar(value=value)
            entry = ctk.CTkEntry(
                body,
                textvariable=var,
                show="•",
                height=34,
                fg_color="#152238",
                border_color="#2B405E",
            )
            entry.grid(row=row, column=1, sticky="ew", padx=(10, 6), pady=5)
            self.credential_entries.append(entry)
            ctk.CTkButton(
                body,
                text="◉",
                width=34,
                height=30,
                fg_color="#1B2B44",
                command=lambda e=entry: e.configure(show="" if e.cget("show") else "•"),
            ).grid(row=row, column=2, padx=(0, 5))
            ctk.CTkButton(
                body,
                text="Copia",
                width=58,
                height=30,
                fg_color="#1B2B44",
                command=lambda v=value: self.copy_value(v),
            ).grid(row=row, column=3)
            row += 1

        ctk.CTkButton(
            page,
            text="Copia tutte le credenziali generate",
            fg_color=self.ACCENT,
            command=self.copy_all_credentials,
        ).pack(anchor="w", pady=(4, 16))

    def copy_value(self, value: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)

    def copy_all_credentials(self) -> None:
        lines: list[str] = []
        for key, label in CREDENTIAL_KEYS:
            value = self.generated_credentials.get(key)
            if value:
                lines.append(f"{label}: {value}")
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))


if __name__ == "__main__":
    wizard = Wizard()
    wizard.mainloop()
