# Windows graphical setup

A Windows GUI is available in [`windows-wizard/`](windows-wizard/README.md).

Quick start:

```powershell
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack\windows-wizard
.\run.ps1
```

The GUI runs on Windows and configures the headless Ubuntu Docker server remotely over SSH/SFTP. It uses the same `setup.sh`, NPM automation and templates as the CLI installer, so the stack logic remains identical.

For a standalone executable, run:

```powershell
.\build.ps1
```

or download the `StreamStackSetupWizard-Windows` artifact produced by the repository's **Windows Setup Wizard** GitHub Actions workflow.
