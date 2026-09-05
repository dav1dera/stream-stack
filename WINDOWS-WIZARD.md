# Windows graphical setup

A Windows GUI is available in [`windows-wizard/`](windows-wizard/README.md).

Quick start:

```powershell
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack\windows-wizard
.\run.ps1
```

The GUI runs on Windows and configures the headless Ubuntu Docker server remotely over SSH/SFTP. It uses the same `setup.sh`, NPM automation and templates as the CLI installer, so the stack logic remains identical.

With **Avvia stack completo** enabled (the default), the wizard does not stop after writing configuration files: it starts the full Compose profile and the final page probes the server's published ports from the Windows PC. The completion screen shows `OK/KO`, the local `http(s)://SERVER_LAN_IP:PORT` address and an **Apri** button for each main web service. This includes both Seanime instances on ports `43211` and `43311`.

AdGuard Home is no longer deployed by this Compose; LAN DNS is expected to be provided by a separate resolver/AdGuard instance. Jackett and other applications can remain locally reachable while still requiring their application-specific first-run configuration.

For a standalone executable, run:

```powershell
.\build.ps1
```

or download the `StreamStackSetupWizard-Windows` artifact produced by the repository's **Windows Setup Wizard** GitHub Actions workflow.
