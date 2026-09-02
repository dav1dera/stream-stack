from __future__ import annotations

# Entry point della GUI allineato alla topologia corrente, mantenendo gli strati
# esistenti (SSH hardening, Demo/Dry Run e verifica LAN finale).
import app as base

HOST_FIELDS = [
    ("AIOSTREAMS_HOST", "AIOStreams", "aiostreams"),
    ("AIOMETADATA_HOST", "AIOMetadata", "aiometadata"),
    ("MEDIAFLOW_HOST", "MediaFlow", "mfp"),
    ("EASYPROXY_HOST", "EasyProxy", "easyproxy"),
    ("HEADSCALE_HOST", "Headscale + Headplane", "headscale"),
    ("STREAMVIX_HOST", "StreamViX", "streamv"),
    ("TVVOO_HOST", "TvVoo", "tvvoo"),
    ("AIOMANAGER_HOST", "AIOManager", "aiomanager"),
    ("SEANIME_HOST", "Seanime", "seanime"),
    ("SEANIME_SHARED_HOST", "Seanime Shared", "shared-seanime"),
    ("COMETNET_HOST", "CometNet", "cometnet"),
    ("STREMTHRU_HOST", "StremThru", "stremthru"),
    ("PORTAINER_HOST", "Portainer", "portainer"),
]
base.Wizard.HOST_FIELDS = HOST_FIELDS

import launcher
launcher.Wizard.HOST_FIELDS = HOST_FIELDS
if ("EASYPROXY_PASSWORD", "EasyProxy API password") not in launcher.CREDENTIAL_KEYS:
    launcher.CREDENTIAL_KEYS.append(("EASYPROXY_PASSWORD", "EasyProxy API password"))

import demo_launcher
import local_ready

# Porte LAN aggiunte dalla topologia corrente.
known = {port for _, port, _ in local_ready.LOCAL_SERVICES}
for item in [
    ("EasyProxy", 8760, "http"),
    ("TvVoo", 5000, "http"),
    ("AIOManager", 1610, "http"),
]:
    if item[1] not in known:
        local_ready.LOCAL_SERVICES.append(item)

if __name__ == "__main__":
    wizard = local_ready.Wizard()
    wizard.mainloop()
