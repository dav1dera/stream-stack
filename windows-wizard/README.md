# Stream Stack Setup Wizard for Windows

Graphical Windows front-end for the `stream-stack` installer.

The Ubuntu server remains headless/CLI. The wizard runs on Windows, connects over SSH/SFTP, writes the private `setup.env`, runs the Linux setup, starts the stack and — with the default settings — refuses to show **Completed** until the strict post-deploy acceptance test passes.

## Before pressing Install

For a fresh public deployment, forward these ports on the router **before** starting the install:

```text
TCP 80  -> SERVER_LAN_IP:80
TCP 443 -> SERVER_LAN_IP:443
```

TCP 80 is required while the wizard obtains the Let's Encrypt certificate via HTTP-01. TCP 443 is required for the final HTTPS path.

The wizard contains an explicit confirmation switch for these rules. With automatic NPM + strict acceptance enabled, you cannot start a real deployment until the confirmation is checked.

## Recommended one-click settings

```text
AUTO_RUNTIME_KEYS       ON
AUTO_CONFIGURE_NPM      ON
START_FULL_STACK        ON
STRICT_ACCEPTANCE       ON
PUBLIC_READY_TIMEOUT    600
ROUTER_PORTS_READY      confirmed
```

### Strict Acceptance

When enabled, the real deployment sequence is:

```text
SSH / prerequisites
        ↓
clone / update repo
        ↓
write setup.env
        ↓
render configs + runtime keys
        ↓
Cloudflare DDNS
        ↓
wait for public DNS
        ↓
NPM + Let's Encrypt
        ↓
start full Compose stack
        ↓
scripts/acceptance.py
        ↓
Completed only on ACCEPTANCE OK
```

The acceptance test waits up to `PUBLIC_READY_TIMEOUT` and verifies:

- all Compose services are running;
- healthchecked containers are healthy;
- expected LAN ports are reachable;
- public non-LAN-only hostnames resolve;
- TLS certificate/hostname validation succeeds;
- NPM routing returns non-5xx responses;
- Headscale `/admin` reaches the OAuth flow.

If the timeout expires, the wizard reports **deployment failed** and keeps the detailed reason in the log instead of presenting a green completion page.

## DNS / certificate waiting

The NPM setup waits for Cloudflare's public DNS resolver to see all generated hostnames before requesting the certificate. This removes the common race where DDNS has just created a record but Let's Encrypt is started immediately.

If certificate issuance still fails, check:

```text
TCP 80 forwarding
TCP 443 forwarding
SERVER_LAN_IP
Cloudflare DNS / token permissions
CGNAT / public reachability
```

## What the wizard does

1. SSH connection test;
2. network/subnet and hostname collection;
3. Mullvad/WireGuard configuration;
4. Cloudflare, metadata/debrid and OAuth credentials;
5. application logins;
6. optional integrations;
7. deployment options / one-click readiness controls;
8. review and validation;
9. remote install with live logs;
10. strict acceptance and final service/credential page.

The Linux scripts remain the source of truth. Windows only collects input and orchestrates the remote workflow.

## Real deployment security

- SSH/API secrets stay in process memory on Windows;
- the real `setup.env` is uploaded directly over SFTP;
- remote `setup.env` is mode `0600` and gitignored;
- the review screen does not expose secret values;
- generated credentials are read back only for the final masked/copyable fields;
- closing the wizard discards the Windows-side copy.

## Demo / Dry Run

Choose **Demo / Dry Run** on the first page to exercise the GUI without touching a server.

It uses:

- `example.test`;
- TEST-NET addresses;
- fake credentials;
- no SSH;
- no Docker;
- no Cloudflare/provider calls;
- no real Strict Acceptance.

The demo validates only the generated `setup.env` and GUI flow.

## Launch from source

Requirements: Windows 10/11 and Python 3.11+.

```powershell
git clone https://github.com/dav1dera/stream-stack.git
cd stream-stack\windows-wizard
.\run.ps1
```

or double-click:

```text
Start-Wizard.cmd
```

`run.ps1` creates a local virtual environment and launches the current `local_ready.py` entry point.

## Standalone EXE

```powershell
cd windows-wizard
.\build.ps1
```

Output:

```text
windows-wizard\dist\StreamStackSetupWizard.exe
```

GitHub Actions also builds the Windows artifact automatically.

## SSH authentication

Supported modes:

- username + password;
- OpenSSH private key;
- encrypted private key + passphrase;
- SSH agent/default keys.

The optional sudo password is used only when prerequisite installation requires it. If Docker is installed during the run, the wizard reconnects after adding the SSH user to the `docker` group.

## Remaining manual application state

`ACCEPTANCE OK` means the infrastructure, DNS/TLS and service routing are ready. It does not fabricate private application data.

Afterwards, depending on the operator's setup:

- add personal Jackett indexers/accounts;
- import the sanitized AIOStreams backup/config and private provider/indexer/Usenet/debrid credentials;
- complete any Seanime/Portainer user-specific state.

These are intentionally not committed or guessed by the wizard.
