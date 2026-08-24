from __future__ import annotations

import base64
import ipaddress
import json
import os
import posixpath
import queue
import re
import shlex
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk
import paramiko

APP_TITLE = "Stream Stack Setup Wizard"
APP_VERSION = "1.0.0"
REPO_URL = "https://github.com/dav1dera/stream-stack.git"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


@dataclass
class FieldSpec:
    key: str
    label: str
    placeholder: str = ""
    secret: bool = False
    required: bool = False
    default: str = ""
    help_text: str = ""


class RemoteError(RuntimeError):
    pass


class SSHSession:
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
        digest = key.get_fingerprint()
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
    ) -> int:
        client = self._require()
        if sudo_password:
            wrapped = f"sudo -S -p '' bash -lc {shlex.quote(command)}"
        else:
            wrapped = command
        transport = client.get_transport()
        if not transport:
            raise RemoteError("SSH transport is unavailable")
        chan = transport.open_session(timeout=15)
        chan.get_pty(width=160, height=40)
        chan.exec_command(wrapped)
        if sudo_password:
            chan.send(sudo_password + "\n")
        started = time.time()
        buffer = b""
        while True:
            if chan.recv_ready():
                buffer += chan.recv(65535)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    emit(line.decode("utf-8", "replace"))
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
        return path

    def put_text(self, remote_path: str, text: str, mode: int = 0o600) -> None:
        client = self._require()
        path = self.resolve(remote_path)
        folder = posixpath.dirname(path)
        self.capture(f"mkdir -p {shlex.quote(folder)}")
        temp = path + ".tmp-stream-stack-wizard"
        sftp = client.open_sftp()
        try:
            with sftp.file(temp, "w") as handle:
                handle.write(text)
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


class Wizard(ctk.CTk):
    ACCENT = "#6C5CE7"
    SUCCESS = "#22C55E"
    WARNING = "#F59E0B"
    DANGER = "#EF4444"

    HOST_FIELDS = [
        ("AIOSTREAMS_HOST", "AIOStreams", "aiostreams"),
        ("AIOMETADATA_HOST", "AIOMetadata", "aiometadata"),
        ("MEDIAFLOW_HOST", "MediaFlow", "mfp"),
        ("HEADSCALE_HOST", "Headscale + Headplane", "headscale"),
        ("STREAMVIX_HOST", "StreamViX", "streamv"),
        ("SEANIME_HOST", "Seanime", "seanime"),
        ("SEANIME_SHARED_HOST", "Seanime Shared", "shared-seanime"),
        ("COMETNET_HOST", "CometNet", "cometnet"),
        ("STREMTHRU_HOST", "StremThru", "stremthru"),
        ("PORTAINER_HOST", "Portainer", "portainer"),
        ("JACKETTIO_HOST", "Jackettio (optional future)", "jackettio"),
    ]

    SECRET_KEYS = {
        "SSH_PASSWORD", "SSH_KEY_PASSPHRASE", "SUDO_PASSWORD",
        "CLOUDFLARE_API_TOKEN", "WIREGUARD_PRIVATE_KEY", "TMDB_API_KEY",
        "TMDB_ACCESS_TOKEN", "TVDB_API_KEY", "TORBOX_API_KEY",
        "GOOGLE_OAUTH_CLIENT_SECRET", "NPM_ADMIN_PASSWORD", "AIO_PASSWORD",
        "AIO_CONFIG_ACCESS_KEY", "STREMTHRU_PASSWORD", "SEANIME_MAIN_PASSWORD",
        "SEANIME_SHARED_PASSWORD", "MDBLIST_API_KEY", "GEMINI_API_KEY",
        "ANILIST_CLIENT_SECRET", "TRAKT_CLIENT_SECRET", "GITHUB_TOKEN",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1500x900")
        self.minsize(1220, 760)
        self.configure(fg_color="#08111F")

        self.vars: dict[str, ctk.StringVar] = {}
        self.bool_vars: dict[str, ctk.BooleanVar] = {}
        self.entries: dict[str, ctk.CTkEntry] = {}
        self.page = 0
        self.session = SSHSession()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.deploying = False
        self.connected = False

        self.steps = [
            ("Benvenuto", self.build_welcome),
            ("Server SSH", self.build_server),
            ("Rete & Domini", self.build_network),
            ("VPN & Proxy", self.build_vpn),
            ("API & Servizi", self.build_apis),
            ("OAuth & Login", self.build_auth),
            ("Opzionali", self.build_optional),
            ("Riepilogo", self.build_review),
            ("Installazione", self.build_deploy),
            ("Completato", self.build_complete),
        ]

        self._init_defaults()
        self._build_shell()
        self.show_page(0)
        self.after(100, self.poll_events)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _init_defaults(self) -> None:
        defaults = {
            "SSH_PORT": "22",
            "REMOTE_DIR": "~/stream-stack",
            "TIMEZONE": "Europe/Rome",
            "AIO_USER": "admin",
            "STREMTHRU_USER": "admin",
            "HEADSCALE_USER": "admin",
        }
        for key, value in defaults.items():
            self.var(key).set(value)
        for key, value in {
            "USE_STANDARD_HOSTS": True,
            "AUTO_RUNTIME_KEYS": True,
            "AUTO_CONFIGURE_NPM": True,
            "INSTALL_PREREQS": False,
            "START_FULL_STACK": True,
        }.items():
            self.bool_var(key).set(value)

    def var(self, key: str) -> ctk.StringVar:
        if key not in self.vars:
            self.vars[key] = ctk.StringVar(value="")
        return self.vars[key]

    def bool_var(self, key: str) -> ctk.BooleanVar:
        if key not in self.bool_vars:
            self.bool_vars[key] = ctk.BooleanVar(value=False)
        return self.bool_vars[key]

    def _build_shell(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0, fg_color="#0D192A")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(
            self.sidebar,
            text="◆  Stream Stack",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#E7EEFF",
        )
        logo.pack(anchor="w", padx=28, pady=(32, 2))
        ctk.CTkLabel(
            self.sidebar,
            text="Setup Wizard",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#A99BFF",
        ).pack(anchor="w", padx=55, pady=(0, 28))

        ctk.CTkLabel(self.sidebar, text="PROGRESSO", text_color="#9FB0CA", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=28)
        self.progress = ctk.CTkProgressBar(self.sidebar, height=8, progress_color=self.ACCENT)
        self.progress.pack(fill="x", padx=28, pady=(10, 6))
        self.progress_label = ctk.CTkLabel(self.sidebar, text="", text_color="#9FB0CA")
        self.progress_label.pack(anchor="w", padx=28, pady=(0, 18))

        self.step_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.step_frame.pack(fill="both", expand=True, padx=16)
        self.step_buttons: list[ctk.CTkButton] = []
        for idx, (label, _) in enumerate(self.steps):
            btn = ctk.CTkButton(
                self.step_frame,
                text=f"{idx + 1}   {label}",
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#16253B",
                text_color="#AFC0D9",
                command=lambda i=idx: self.jump_to(i),
            )
            btn.pack(fill="x", pady=2)
            self.step_buttons.append(btn)

        self.sidebar_status = ctk.CTkLabel(self.sidebar, text="SSH: non connesso", text_color="#8091AA")
        self.sidebar_status.pack(anchor="w", padx=28, pady=(4, 22))

        self.main = ctk.CTkFrame(self, fg_color="#08111F", corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self.header = ctk.CTkFrame(self.main, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=34, pady=(28, 12))
        self.header.grid_columnconfigure(0, weight=1)
        self.step_kicker = ctk.CTkLabel(self.header, text="", text_color="#9A8CFF", font=ctk.CTkFont(size=13, weight="bold"))
        self.step_kicker.grid(row=0, column=0, sticky="w")
        self.page_title = ctk.CTkLabel(self.header, text="", text_color="#EDF3FF", font=ctk.CTkFont(size=30, weight="bold"))
        self.page_title.grid(row=1, column=0, sticky="w", pady=(3, 0))
        self.page_subtitle = ctk.CTkLabel(self.header, text="", text_color="#9FB0CA", font=ctk.CTkFont(size=14))
        self.page_subtitle.grid(row=2, column=0, sticky="w", pady=(4, 0))

        self.content_holder = ctk.CTkFrame(self.main, fg_color="transparent")
        self.content_holder.grid(row=1, column=0, sticky="nsew", padx=34)
        self.content_holder.grid_columnconfigure(0, weight=1)
        self.content_holder.grid_rowconfigure(0, weight=1)

        self.footer = ctk.CTkFrame(self.main, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew", padx=34, pady=20)
        self.footer.grid_columnconfigure(1, weight=1)
        self.back_btn = ctk.CTkButton(self.footer, text="‹  Indietro", width=120, fg_color="#152239", hover_color="#20324F", command=self.back)
        self.back_btn.grid(row=0, column=0, sticky="w")
        self.next_btn = ctk.CTkButton(self.footer, text="Avanti  ›", width=130, fg_color=self.ACCENT, hover_color="#5A4DD3", command=self.next)
        self.next_btn.grid(row=0, column=2, sticky="e")

    def jump_to(self, index: int) -> None:
        if self.deploying:
            return
        if index <= self.page or index <= 7:
            self.show_page(index)

    def show_page(self, index: int) -> None:
        self.page = max(0, min(index, len(self.steps) - 1))
        for child in self.content_holder.winfo_children():
            child.destroy()
        self.entries = {}
        label, builder = self.steps[self.page]
        self.step_kicker.configure(text=f"Passo {self.page + 1} di {len(self.steps)}")
        self.page_title.configure(text=label)
        subtitles = {
            0: "Configura il tuo server Docker da Windows senza installare una GUI su Ubuntu.",
            1: "Connessione sicura al server Ubuntu via SSH.",
            2: "IP, subnet e nomi pubblici dei servizi.",
            3: "Tunnel Mullvad/WireGuard usato da Gluetun.",
            4: "Credenziali esterne necessarie allo stack.",
            5: "OAuth, account applicativi e Nginx Proxy Manager.",
            6: "Integrazioni non obbligatorie e opzioni di deployment.",
            7: "Controlla i valori prima di modificare il server.",
            8: "Configurazione remota, NPM e avvio dello stack.",
            9: "Stato finale e collegamenti utili.",
        }
        self.page_subtitle.configure(text=subtitles[self.page])
        builder()
        fraction = self.page / max(1, len(self.steps) - 1)
        self.progress.set(fraction)
        self.progress_label.configure(text=f"{self.page + 1} / {len(self.steps)}   {int(fraction * 100)}%")
        for idx, btn in enumerate(self.step_buttons):
            if idx == self.page:
                btn.configure(fg_color="#2B2B63", text_color="#FFFFFF")
            elif idx < self.page:
                btn.configure(fg_color="transparent", text_color="#6EE7A8")
            else:
                btn.configure(fg_color="transparent", text_color="#AFC0D9")
        self.back_btn.configure(state="disabled" if self.page == 0 or self.deploying else "normal")
        if self.page == 7:
            self.next_btn.configure(text="Installa  ›", state="normal", fg_color=self.ACCENT)
        elif self.page >= 8:
            self.next_btn.configure(state="disabled", text="Avanti  ›")
        else:
            self.next_btn.configure(text="Avanti  ›", state="normal", fg_color=self.ACCENT)

    def card(self, parent: ctk.CTkBaseClass, title: str, subtitle: str = "") -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color="#0E1A2B", border_width=1, border_color="#21324A", corner_radius=10)
        frame.pack(fill="x", pady=8)
        ctk.CTkLabel(frame, text=title.upper(), text_color="#ADA2FF", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=18, pady=(16, 2))
        if subtitle:
            ctk.CTkLabel(frame, text=subtitle, text_color="#8798B1", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=18, pady=(0, 8))
        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(6, 18))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        return body

    def field(self, parent: ctk.CTkBaseClass, spec: FieldSpec, row: int, col: int = 0, span: int = 1) -> ctk.CTkEntry:
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=row, column=col, columnspan=span, sticky="ew", padx=(0, 12) if col == 0 and span == 1 else 0, pady=6)
        cell.grid_columnconfigure(0, weight=1)
        required = " *" if spec.required else ""
        ctk.CTkLabel(cell, text=spec.label + required, text_color="#D9E2F2", anchor="w").grid(row=0, column=0, sticky="ew", pady=(0, 5))
        if spec.default and not self.var(spec.key).get():
            self.var(spec.key).set(spec.default)
        entry = ctk.CTkEntry(
            cell,
            textvariable=self.var(spec.key),
            height=38,
            corner_radius=7,
            fg_color="#162337",
            border_color="#2D405D",
            placeholder_text=spec.placeholder,
            show="•" if spec.secret else "",
        )
        entry.grid(row=1, column=0, sticky="ew")
        if spec.secret:
            eye = ctk.CTkButton(cell, text="◉", width=38, height=34, fg_color="#1D2C43", hover_color="#2B405F", command=lambda e=entry: self.toggle_secret(e))
            eye.grid(row=1, column=1, padx=(6, 0))
        if spec.help_text:
            ctk.CTkLabel(cell, text=spec.help_text, text_color="#71839F", font=ctk.CTkFont(size=11), anchor="w").grid(row=2, column=0, columnspan=2, sticky="ew", pady=(3, 0))
        self.entries[spec.key] = entry
        return entry

    @staticmethod
    def toggle_secret(entry: ctk.CTkEntry) -> None:
        entry.configure(show="" if entry.cget("show") else "•")

    def scroll_page(self) -> ctk.CTkScrollableFrame:
        frame = ctk.CTkScrollableFrame(self.content_holder, fg_color="transparent", scrollbar_button_color="#243653")
        frame.grid(row=0, column=0, sticky="nsew")
        return frame

    def build_welcome(self) -> None:
        page = self.scroll_page()
        hero = ctk.CTkFrame(page, fg_color="#101E33", border_width=1, border_color="#283C5B", corner_radius=14)
        hero.pack(fill="x", pady=(12, 16))
        ctk.CTkLabel(hero, text="◆", text_color="#7C6CFF", font=ctk.CTkFont(size=54, weight="bold")).pack(pady=(30, 8))
        ctk.CTkLabel(hero, text="Configura tutto dal PC Windows", text_color="#F0F5FF", font=ctk.CTkFont(size=27, weight="bold")).pack()
        ctk.CTkLabel(
            hero,
            text="La GUI invia la configurazione al server via SSH, esegue il setup Linux, configura NPM e mostra i log.\nIl server può restare completamente headless/CLI.",
            text_color="#A7B6CC",
            justify="center",
            font=ctk.CTkFont(size=14),
        ).pack(pady=(10, 28))
        info = self.card(page, "Cosa farà il wizard")
        items = [
            "Test SSH e verifica prerequisiti sul server",
            "Clone/aggiornamento di dav1dera/stream-stack",
            "Creazione di setup.env remoto senza salvare i secret in Git",
            "Generazione automatica dei secret locali e delle chiavi runtime",
            "Configurazione Nginx Proxy Manager e certificati HTTPS",
            "Avvio e verifica dei container Docker",
        ]
        for i, item in enumerate(items):
            ctk.CTkLabel(info, text=f"✓  {item}", text_color="#C7D3E6", anchor="w").grid(row=i, column=0, columnspan=2, sticky="ew", pady=4)

    def build_server(self) -> None:
        page = self.scroll_page()
        body = self.card(page, "Connessione SSH", "Puoi usare password oppure chiave privata.")
        self.field(body, FieldSpec("SSH_HOST", "IP / Host server", "192.168.1.20", required=True), 0, 0)
        self.field(body, FieldSpec("SSH_PORT", "Porta SSH", default="22", required=True), 0, 1)
        self.field(body, FieldSpec("SSH_USER", "Utente SSH", "pi", required=True), 1, 0)
        self.field(body, FieldSpec("SSH_PASSWORD", "Password SSH", secret=True), 1, 1)
        key_entry = self.field(body, FieldSpec("SSH_KEY_PATH", "Chiave SSH privata", "C:\\Users\\...\\.ssh\\id_ed25519"), 2, 0)
        ctk.CTkButton(body, text="Sfoglia…", width=100, fg_color="#1B2B44", command=lambda: self.choose_key(key_entry)).grid(row=2, column=1, sticky="w", padx=4, pady=(31, 0))
        self.field(body, FieldSpec("SSH_KEY_PASSPHRASE", "Passphrase chiave", secret=True), 3, 0)
        self.field(body, FieldSpec("SUDO_PASSWORD", "Password sudo (se diversa)", secret=True, help_text="Lascia vuoto se Docker è già configurato per il tuo utente o se sudo non serve."), 3, 1)
        self.field(body, FieldSpec("REMOTE_DIR", "Directory stack sul server", default="~/stream-stack", required=True), 4, 0, 2)

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=10)
        self.test_btn = ctk.CTkButton(actions, text="Test connessione", fg_color=self.ACCENT, command=self.test_connection)
        self.test_btn.pack(side="left")
        self.connection_result = ctk.CTkLabel(actions, text="", text_color="#A6B6CC")
        self.connection_result.pack(side="left", padx=16)

    def choose_key(self, entry: ctk.CTkEntry) -> None:
        path = filedialog.askopenfilename(title="Seleziona chiave privata SSH", filetypes=[("SSH keys", "*"), ("All files", "*")])
        if path:
            self.var("SSH_KEY_PATH").set(path)

    def build_network(self) -> None:
        page = self.scroll_page()
        body = self.card(page, "Rete", "Questi valori vengono propagati in Headscale, Tailscale, Honey e nei file applicativi.")
        self.field(body, FieldSpec("SERVER_LAN_IP", "IP privato del server", "192.168.1.20", required=True), 0, 0)
        self.field(body, FieldSpec("LAN_SUBNET", "Subnet LAN", "192.168.1.0/24", required=True), 0, 1)
        self.field(body, FieldSpec("BASE_DOMAIN", "Dominio base", "example.com", required=True), 1, 0)
        self.field(body, FieldSpec("TAILNET_DOMAIN", "Dominio MagicDNS", "wg.example.com", help_text="Vuoto = wg.<dominio base>."), 1, 1)
        self.field(body, FieldSpec("PROXMOX_IP", "IP Proxmox", "192.168.1.10", help_text="Solo per Honey; vuoto = IP server."), 2, 0)
        self.field(body, FieldSpec("AMP_IP", "IP AMP", "192.168.1.30", help_text="Solo per Honey; vuoto = IP server."), 2, 1)
        self.field(body, FieldSpec("TIMEZONE", "Timezone", default="Europe/Rome"), 3, 0)

        domains = self.card(page, "Domini pubblici", "La logica interna resta identica; gli FQDN possono essere scelti liberamente.")
        switch = ctk.CTkSwitch(domains, text="Usa nomi standard derivati dal dominio base", variable=self.bool_var("USE_STANDARD_HOSTS"), command=self.refresh_host_fields, progress_color=self.ACCENT)
        switch.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        for idx, (key, label, prefix) in enumerate(self.HOST_FIELDS, start=1):
            row = (idx + 1) // 2
            col = (idx - 1) % 2
            self.field(domains, FieldSpec(key, label, f"{prefix}.example.com"), row, col)
        self.var("BASE_DOMAIN").trace_add("write", lambda *_: self.refresh_host_fields())
        self.refresh_host_fields()

    def refresh_host_fields(self) -> None:
        base = self.var("BASE_DOMAIN").get().strip().lower().rstrip(".")
        use_defaults = self.bool_var("USE_STANDARD_HOSTS").get()
        for key, _, prefix in self.HOST_FIELDS:
            entry = self.entries.get(key)
            if not entry:
                continue
            if use_defaults and base:
                self.var(key).set(f"{prefix}.{base}")
                entry.configure(state="disabled")
            else:
                entry.configure(state="normal")

    def build_vpn(self) -> None:
        page = self.scroll_page()
        body = self.card(page, "Gluetun / Mullvad", "Mantiene la stessa catena Gluetun → WARP/GOST del server di riferimento.")
        self.field(body, FieldSpec("WIREGUARD_PRIVATE_KEY", "WireGuard private key", secret=True, required=True), 0, 0, 2)
        self.field(body, FieldSpec("WIREGUARD_ADDRESS_CIDR", "WireGuard address CIDR", "10.x.x.x/32", required=True), 1, 0)
        ctk.CTkLabel(body, text="MicroWARP crea una nuova identità locale. Non viene copiata alcuna identità WARP privata dalla repo sorgente.", text_color="#8EA0B9", wraplength=900, justify="left").grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def build_apis(self) -> None:
        page = self.scroll_page()
        cloud = self.card(page, "Cloudflare")
        self.field(cloud, FieldSpec("CLOUDFLARE_API_TOKEN", "Cloudflare API token", secret=True, required=True, help_text="Token con permessi DNS edit sulle zone usate dai domini scelti."), 0, 0, 2)

        media = self.card(page, "Metadata & Debrid")
        self.field(media, FieldSpec("TMDB_API_KEY", "TMDB API key", secret=True, required=True), 0, 0)
        self.field(media, FieldSpec("TMDB_ACCESS_TOKEN", "TMDB read access token", secret=True, required=True), 0, 1)
        self.field(media, FieldSpec("TVDB_API_KEY", "TVDB API key", secret=True, required=True), 1, 0)
        self.field(media, FieldSpec("TORBOX_API_KEY", "TorBox API key", secret=True, required=True), 1, 1)

    def build_auth(self) -> None:
        page = self.scroll_page()
        oauth = self.card(page, "Google OAuth2", "OAuth2 Proxy protegge Headplane come nel deployment di riferimento.")
        self.field(oauth, FieldSpec("ALLOWED_EMAIL", "Account Google consentito", "nome@gmail.com", required=True), 0, 0)
        self.field(oauth, FieldSpec("GOOGLE_OAUTH_CLIENT_ID", "OAuth Client ID", required=True), 1, 0)
        self.field(oauth, FieldSpec("GOOGLE_OAUTH_CLIENT_SECRET", "OAuth Client Secret", secret=True, required=True), 1, 1)

        npm = self.card(page, "Nginx Proxy Manager", "Su installazione nuova il wizard crea l'admin; su NPM esistente usa le credenziali attuali.")
        self.field(npm, FieldSpec("NPM_ADMIN_EMAIL", "Email admin NPM", "vuoto = account Google"), 0, 0)
        self.field(npm, FieldSpec("NPM_ADMIN_PASSWORD", "Password admin NPM", secret=True, help_text="Vuoto = generata automaticamente."), 0, 1)
        self.field(npm, FieldSpec("LETSENCRYPT_EMAIL", "Email Let's Encrypt", "vuoto = account Google"), 1, 0)

        logins = self.card(page, "Login applicativi", "Se lasci le password vuote vengono generate dal setup Linux e salvate solo sul server.")
        self.field(logins, FieldSpec("AIO_USER", "Utente AIOStreams", default="admin"), 0, 0)
        self.field(logins, FieldSpec("AIO_PASSWORD", "Password AIOStreams", secret=True), 0, 1)
        self.field(logins, FieldSpec("AIO_CONFIG_ACCESS_KEY", "AIO Config Access Key", secret=True), 1, 0)
        self.field(logins, FieldSpec("STREMTHRU_USER", "Utente StremThru", default="admin"), 1, 1)
        self.field(logins, FieldSpec("STREMTHRU_PASSWORD", "Password StremThru", secret=True), 2, 0)
        self.field(logins, FieldSpec("SEANIME_MAIN_PASSWORD", "Password Seanime", secret=True), 2, 1)
        self.field(logins, FieldSpec("SEANIME_SHARED_PASSWORD", "Password Seanime Shared", secret=True), 3, 0)

    def build_optional(self) -> None:
        page = self.scroll_page()
        body = self.card(page, "Integrazioni opzionali", "Lasciale vuote se non vengono utilizzate.")
        optional = [
            FieldSpec("MDBLIST_API_KEY", "MDBList API key", secret=True),
            FieldSpec("GEMINI_API_KEY", "Gemini API key", secret=True),
            FieldSpec("ANILIST_CLIENT_ID", "AniList Client ID"),
            FieldSpec("ANILIST_CLIENT_SECRET", "AniList Client Secret", secret=True),
            FieldSpec("TRAKT_CLIENT_ID", "Trakt Client ID"),
            FieldSpec("TRAKT_CLIENT_SECRET", "Trakt Client Secret", secret=True),
            FieldSpec("GITHUB_USERNAME", "GitHub username (StremThru)"),
            FieldSpec("GITHUB_TOKEN", "GitHub token (StremThru)", secret=True),
            FieldSpec("AIOMETADATA_CONFIG_UUID", "AIOMetadata config UUID"),
            FieldSpec("AIO_TRUSTED_UUID", "AIOStreams trusted UUID"),
        ]
        for idx, spec in enumerate(optional):
            self.field(body, spec, idx // 2, idx % 2)

        opts = self.card(page, "Opzioni deployment")
        choices = [
            ("AUTO_RUNTIME_KEYS", "Genera automaticamente chiavi Headscale e rileva API key Jackett"),
            ("AUTO_CONFIGURE_NPM", "Configura automaticamente NPM, proxy host e certificati"),
            ("INSTALL_PREREQS", "Installa Git/Python/Docker automaticamente se mancanti (richiede sudo)"),
            ("START_FULL_STACK", "Avvia tutto lo stack al termine"),
        ]
        for idx, (key, label) in enumerate(choices):
            ctk.CTkSwitch(opts, text=label, variable=self.bool_var(key), progress_color=self.ACCENT).grid(row=idx, column=0, columnspan=2, sticky="w", pady=6)

    def build_review(self) -> None:
        page = self.scroll_page()
        errors = self.validate_all(show_message=False)
        status = self.card(page, "Validazione")
        if errors:
            ctk.CTkLabel(status, text="⚠ Correggi questi campi prima di installare:", text_color=self.WARNING, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w")
            for idx, err in enumerate(errors, start=1):
                ctk.CTkLabel(status, text=f"• {err}", text_color="#F7C873", anchor="w").grid(row=idx, column=0, columnspan=2, sticky="w", pady=2)
        else:
            ctk.CTkLabel(status, text="✓ I campi obbligatori sono coerenti.", text_color=self.SUCCESS, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w")

        summary = self.card(page, "Riepilogo")
        keys = [
            "SSH_HOST", "SSH_USER", "REMOTE_DIR", "SERVER_LAN_IP", "LAN_SUBNET", "BASE_DOMAIN",
            *[k for k, _, _ in self.HOST_FIELDS],
            "ALLOWED_EMAIL", "NPM_ADMIN_EMAIL", "AIO_USER", "STREMTHRU_USER",
            "AUTO_RUNTIME_KEYS", "AUTO_CONFIGURE_NPM", "START_FULL_STACK",
        ]
        row = 0
        for key in keys:
            if key in self.bool_vars:
                value = "Sì" if self.bool_var(key).get() else "No"
            else:
                value = self.var(key).get() or "(automatico / vuoto)"
            ctk.CTkLabel(summary, text=key, text_color="#8193AD", anchor="w").grid(row=row, column=0, sticky="w", pady=2)
            ctk.CTkLabel(summary, text=value, text_color="#DCE6F5", anchor="w", wraplength=650).grid(row=row, column=1, sticky="w", pady=2)
            row += 1
        ctk.CTkLabel(page, text="I secret non vengono mostrati nel riepilogo e non vengono committati nella repo.", text_color="#7E91AD").pack(anchor="w", pady=10)

    def build_deploy(self) -> None:
        page = ctk.CTkFrame(self.content_holder, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(page, fg_color="#0E1A2B", border_width=1, border_color="#21324A", corner_radius=10)
        top.grid(row=0, column=0, sticky="ew", pady=(8, 10))
        self.deploy_status = ctk.CTkLabel(top, text="Pronto", text_color="#DCE6F5", font=ctk.CTkFont(size=16, weight="bold"))
        self.deploy_status.pack(side="left", padx=18, pady=14)
        self.deploy_progress = ctk.CTkProgressBar(top, width=360, progress_color=self.ACCENT)
        self.deploy_progress.pack(side="right", padx=18, pady=14)
        self.deploy_progress.set(0)

        self.logbox = ctk.CTkTextbox(page, fg_color="#07101D", border_width=1, border_color="#21324A", font=ctk.CTkFont(family="Consolas", size=12), wrap="word")
        self.logbox.grid(row=1, column=0, sticky="nsew")
        self.logbox.insert("end", "Premi Avvia installazione per iniziare.\n")
        self.logbox.configure(state="disabled")

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=12)
        self.deploy_btn = ctk.CTkButton(actions, text="Avvia installazione", fg_color=self.ACCENT, command=self.start_deployment)
        self.deploy_btn.pack(side="left")
        ctk.CTkButton(actions, text="Copia log", fg_color="#1B2B44", command=self.copy_log).pack(side="left", padx=8)

    def build_complete(self) -> None:
        page = self.scroll_page()
        hero = ctk.CTkFrame(page, fg_color="#0E1F28", border_width=1, border_color="#1E5B46", corner_radius=14)
        hero.pack(fill="x", pady=(10, 18))
        ctk.CTkLabel(hero, text="✓", text_color=self.SUCCESS, font=ctk.CTkFont(size=54, weight="bold")).pack(pady=(26, 2))
        ctk.CTkLabel(hero, text="Configurazione completata", text_color="#EFFCF6", font=ctk.CTkFont(size=26, weight="bold")).pack()
        ctk.CTkLabel(hero, text="Il server è stato configurato. Completa solo gli stati applicativi che non possono essere pubblicati.", text_color="#9FC5B5").pack(pady=(8, 24))

        body = self.card(page, "Passi ancora manuali")
        for idx, text in enumerate([
            "Completa il wizard iniziale di AdGuard Home",
            "Aggiungi i tuoi indexer/account dentro Jackett",
            "Importa il JSON sanitizzato di AIOStreams e inserisci le credenziali provider/indexer",
            "Verifica i servizi e le varianti AIOStreams end-to-end",
        ]):
            ctk.CTkLabel(body, text=f"{idx + 1}.  {text}", text_color="#D5E1F1", anchor="w").grid(row=idx, column=0, columnspan=2, sticky="w", pady=4)

        links = ctk.CTkFrame(page, fg_color="transparent")
        links.pack(fill="x", pady=10)
        ip = self.var("SERVER_LAN_IP").get()
        urls = [
            ("AdGuard", f"http://{ip}:3010"),
            ("Jackett", f"http://{ip}:9117"),
            ("Portainer", f"http://{ip}:9000"),
            ("AIOStreams", f"https://{self.var('AIOSTREAMS_HOST').get()}"),
        ]
        for label, url in urls:
            ctk.CTkButton(links, text=f"Apri {label}", fg_color="#1B2B44", command=lambda u=url: webbrowser.open(u)).pack(side="left", padx=(0, 8))

    def back(self) -> None:
        if not self.deploying:
            self.show_page(self.page - 1)

    def next(self) -> None:
        if self.page == 7:
            if self.validate_all(show_message=True):
                return
            self.show_page(8)
            return
        self.show_page(self.page + 1)

    def validate_all(self, show_message: bool = False) -> list[str]:
        required = {
            "SSH_HOST": "Server SSH",
            "SSH_PORT": "Porta SSH",
            "SSH_USER": "Utente SSH",
            "REMOTE_DIR": "Directory remota",
            "BASE_DOMAIN": "Dominio base",
            "SERVER_LAN_IP": "IP server",
            "LAN_SUBNET": "Subnet LAN",
            "WIREGUARD_PRIVATE_KEY": "WireGuard private key",
            "WIREGUARD_ADDRESS_CIDR": "WireGuard address",
            "CLOUDFLARE_API_TOKEN": "Cloudflare API token",
            "TMDB_API_KEY": "TMDB API key",
            "TMDB_ACCESS_TOKEN": "TMDB access token",
            "TVDB_API_KEY": "TVDB API key",
            "TORBOX_API_KEY": "TorBox API key",
            "ALLOWED_EMAIL": "Email OAuth consentita",
            "GOOGLE_OAUTH_CLIENT_ID": "Google OAuth Client ID",
            "GOOGLE_OAUTH_CLIENT_SECRET": "Google OAuth Client Secret",
        }
        errors: list[str] = []
        for key, label in required.items():
            if not self.var(key).get().strip():
                errors.append(f"{label} mancante")
        try:
            port = int(self.var("SSH_PORT").get())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            errors.append("Porta SSH non valida")
        try:
            ipaddress.ip_address(self.var("SERVER_LAN_IP").get().strip())
        except ValueError:
            errors.append("IP server non valido")
        try:
            ipaddress.ip_network(self.var("LAN_SUBNET").get().strip(), strict=False)
        except ValueError:
            errors.append("Subnet LAN non valida")
        base = self.var("BASE_DOMAIN").get().strip().lower().rstrip(".")
        if base and ("://" in base or "/" in base or " " in base or "." not in base):
            errors.append("Dominio base non valido")
        if self.var("ALLOWED_EMAIL").get() and "@" not in self.var("ALLOWED_EMAIL").get():
            errors.append("Email OAuth non valida")
        fqdn_re = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.I)
        for key, label, _ in self.HOST_FIELDS:
            value = self.var(key).get().strip().rstrip(".")
            if value and not fqdn_re.match(value):
                errors.append(f"Hostname {label} non valido")
        if show_message and errors:
            messagebox.showerror("Configurazione incompleta", "\n".join(f"• {e}" for e in errors))
        return errors

    def test_connection(self) -> None:
        errors = []
        for key in ("SSH_HOST", "SSH_PORT", "SSH_USER"):
            if not self.var(key).get().strip():
                errors.append(key)
        if errors:
            messagebox.showerror("SSH", "Compila host, porta e utente SSH.")
            return
        self.test_btn.configure(state="disabled", text="Connessione…")
        self.connection_result.configure(text="")
        threading.Thread(target=self._connection_worker, daemon=True).start()

    def _connection_worker(self) -> None:
        try:
            self.ensure_connected(force=True)
            version = self.session.capture("uname -srmo && printf '\\n' && (docker --version 2>/dev/null || true) && (docker compose version 2>/dev/null || true)")
            self.events.put(("connection_ok", (self.session.fingerprint, version.strip())))
        except Exception as exc:
            self.events.put(("connection_error", str(exc)))

    def ensure_connected(self, force: bool = False) -> None:
        if self.connected and self.session.client and not force:
            transport = self.session.client.get_transport()
            if transport and transport.is_active():
                return
        self.session.connect(
            self.var("SSH_HOST").get().strip(),
            int(self.var("SSH_PORT").get().strip() or "22"),
            self.var("SSH_USER").get().strip(),
            self.var("SSH_PASSWORD").get(),
            self.var("SSH_KEY_PATH").get().strip(),
            self.var("SSH_KEY_PASSPHRASE").get(),
        )
        self.connected = True

    def setup_env_text(self) -> str:
        values: dict[str, str] = {}
        keys = [
            "BASE_DOMAIN", "SERVER_LAN_IP", "LAN_SUBNET", "TAILNET_DOMAIN", "PROXMOX_IP", "AMP_IP", "ALLOWED_EMAIL", "TIMEZONE",
            *[k for k, _, _ in self.HOST_FIELDS],
            "NPM_ADMIN_EMAIL", "NPM_ADMIN_PASSWORD", "LETSENCRYPT_EMAIL",
            "AIO_USER", "AIO_PASSWORD", "AIO_CONFIG_ACCESS_KEY", "STREMTHRU_USER", "STREMTHRU_PASSWORD",
            "SEANIME_MAIN_PASSWORD", "SEANIME_SHARED_PASSWORD", "CLOUDFLARE_API_TOKEN", "WIREGUARD_PRIVATE_KEY",
            "WIREGUARD_ADDRESS_CIDR", "TMDB_API_KEY", "TMDB_ACCESS_TOKEN", "TVDB_API_KEY", "TORBOX_API_KEY",
            "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "MDBLIST_API_KEY", "GEMINI_API_KEY",
            "ANILIST_CLIENT_ID", "ANILIST_CLIENT_SECRET", "TRAKT_CLIENT_ID", "TRAKT_CLIENT_SECRET",
            "GITHUB_USERNAME", "GITHUB_TOKEN", "AIOMETADATA_CONFIG_UUID", "AIO_TRUSTED_UUID", "HEADSCALE_USER",
        ]
        for key in keys:
            values[key] = self.var(key).get().strip()
        values["AUTO_RUNTIME_KEYS"] = "true" if self.bool_var("AUTO_RUNTIME_KEYS").get() else "false"
        values["AUTO_CONFIGURE_NPM"] = "true" if self.bool_var("AUTO_CONFIGURE_NPM").get() else "false"
        lines = [
            "# Generated by Stream Stack Setup Wizard for Windows",
            "# Local runtime secret file. Never commit this file.",
            "",
        ]
        for key, value in values.items():
            if value == "":
                lines.append(f"{key}=")
                continue
            if re.fullmatch(r"[A-Za-z0-9_./:@%+,=*?\-]+", value):
                rendered = value
            else:
                rendered = json.dumps(value)
            lines.append(f"{key}={rendered}")
        return "\n".join(lines) + "\n"

    def start_deployment(self) -> None:
        if self.deploying:
            return
        if self.validate_all(show_message=True):
            return
        self.deploying = True
        self.deploy_btn.configure(state="disabled")
        self.back_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
        self.set_deploy_status("Connessione SSH…", 0.03)
        threading.Thread(target=self._deploy_worker, daemon=True).start()

    def _deploy_worker(self) -> None:
        def emit(line: str) -> None:
            self.events.put(("log", line))

        try:
            self.ensure_connected(force=True)
            remote_dir = self.session.resolve(self.var("REMOTE_DIR").get())
            self.events.put(("deploy_status", ("Verifica prerequisiti…", 0.08)))
            checks = self.session.capture(
                "printf 'git='; command -v git || true; "
                "printf 'python3='; command -v python3 || true; "
                "printf 'docker='; command -v docker || true; "
                "printf 'compose='; docker compose version >/dev/null 2>&1 && echo yes || true"
            )
            emit(checks.strip())
            missing = any(x in checks for x in ("git=\n", "python3=\n", "docker=\n", "compose=\n"))
            if missing and self.bool_var("INSTALL_PREREQS").get():
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
usermod -aG docker "$SUDO_USER" || true
""".strip()
                sudo_pw = self.var("SUDO_PASSWORD").get() or self.var("SSH_PASSWORD").get()
                code = self.session.stream(install, emit, timeout=1200, sudo_password=sudo_pw)
                if code != 0:
                    raise RemoteError("Installazione prerequisiti fallita")
            elif missing:
                raise RemoteError("Mancano Git/Python/Docker sul server. Attiva 'Installa prerequisiti' oppure installali manualmente.")

            self.events.put(("deploy_status", ("Clone / aggiornamento repository…", 0.2)))
            parent = posixpath.dirname(remote_dir)
            cmd = (
                f"mkdir -p {shlex.quote(parent)} && "
                f"if [ -d {shlex.quote(remote_dir)}/.git ]; then "
                f"git -C {shlex.quote(remote_dir)} pull --ff-only; "
                f"else git clone {shlex.quote(REPO_URL)} {shlex.quote(remote_dir)}; fi"
            )
            if self.session.stream(cmd, emit, timeout=300) != 0:
                raise RemoteError("Clone/aggiornamento repository fallito")

            self.events.put(("deploy_status", ("Scrittura setup.env sicuro…", 0.28)))
            self.session.put_text(posixpath.join(remote_dir, "setup.env"), self.setup_env_text(), 0o600)
            emit("setup.env scritto via SFTP con mode 0600")

            self.events.put(("deploy_status", ("Esecuzione setup Linux…", 0.38)))
            setup_cmd = f"cd {shlex.quote(remote_dir)} && chmod +x setup.sh scripts/bootstrap.sh && ./setup.sh --non-interactive"
            if self.session.stream(setup_cmd, emit, timeout=1800) != 0:
                raise RemoteError("setup.sh ha restituito un errore")

            if self.bool_var("START_FULL_STACK").get():
                self.events.put(("deploy_status", ("Avvio stack completo…", 0.78)))
                up_cmd = f"cd {shlex.quote(remote_dir)} && docker compose --profile all up -d"
                if self.session.stream(up_cmd, emit, timeout=1800) != 0:
                    raise RemoteError("Avvio dello stack fallito")

            self.events.put(("deploy_status", ("Verifica container…", 0.9)))
            status_cmd = f"cd {shlex.quote(remote_dir)} && docker compose --profile all ps"
            status = self.session.capture(status_cmd, timeout=120)
            emit(status.rstrip())
            self.events.put(("deploy_done", status))
        except Exception as exc:
            self.events.put(("deploy_error", str(exc)))

    def append_log(self, line: str) -> None:
        if not hasattr(self, "logbox"):
            return
        self.logbox.configure(state="normal")
        self.logbox.insert("end", line.rstrip() + "\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def copy_log(self) -> None:
        if not hasattr(self, "logbox"):
            return
        text = self.logbox.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)

    def set_deploy_status(self, text: str, value: float) -> None:
        if hasattr(self, "deploy_status"):
            self.deploy_status.configure(text=text)
        if hasattr(self, "deploy_progress"):
            self.deploy_progress.set(value)

    def poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "connection_ok":
                    fingerprint, version = payload  # type: ignore[misc]
                    self.connected = True
                    self.sidebar_status.configure(text="SSH: connesso", text_color=self.SUCCESS)
                    if hasattr(self, "test_btn"):
                        self.test_btn.configure(state="normal", text="Test connessione")
                    if hasattr(self, "connection_result"):
                        self.connection_result.configure(text=f"✓ Connesso · {fingerprint}", text_color=self.SUCCESS)
                    messagebox.showinfo("Connessione riuscita", f"Server raggiungibile.\n\nHost key: {fingerprint}\n\n{version}")
                elif kind == "connection_error":
                    self.connected = False
                    self.sidebar_status.configure(text="SSH: errore", text_color=self.DANGER)
                    if hasattr(self, "test_btn"):
                        self.test_btn.configure(state="normal", text="Test connessione")
                    if hasattr(self, "connection_result"):
                        self.connection_result.configure(text="✕ Connessione fallita", text_color=self.DANGER)
                    messagebox.showerror("Errore SSH", str(payload))
                elif kind == "log":
                    self.append_log(str(payload))
                elif kind == "deploy_status":
                    text, progress = payload  # type: ignore[misc]
                    self.set_deploy_status(str(text), float(progress))
                elif kind == "deploy_done":
                    self.append_log("\n=== INSTALLAZIONE COMPLETATA ===")
                    self.set_deploy_status("Completato", 1.0)
                    self.deploying = False
                    self.sidebar_status.configure(text="SSH: connesso", text_color=self.SUCCESS)
                    self.after(800, lambda: self.show_page(9))
                elif kind == "deploy_error":
                    self.append_log(f"\nERRORE: {payload}")
                    self.set_deploy_status("Installazione fallita", 1.0)
                    self.deploying = False
                    if hasattr(self, "deploy_btn"):
                        self.deploy_btn.configure(state="normal", text="Riprova")
                    self.back_btn.configure(state="normal")
                    messagebox.showerror("Installazione fallita", str(payload))
        except queue.Empty:
            pass
        self.after(100, self.poll_events)

    def on_close(self) -> None:
        if self.deploying:
            if not messagebox.askyesno("Installazione in corso", "Chiudere comunque il wizard? Il comando remoto potrebbe continuare sul server."):
                return
        self.session.close()
        self.destroy()


if __name__ == "__main__":
    app = Wizard()
    app.mainloop()
