from __future__ import annotations

# Adapter della GUI Windows alla topologia corrente. Il motore SSH/deploy resta
# in launcher.py; qui aggiorniamo soltanto i campi che devono seguire streams-aio.
import app as base

base.Wizard.HOST_FIELDS = [
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

import launcher

launcher.Wizard.HOST_FIELDS = base.Wizard.HOST_FIELDS
if ("EASYPROXY_PASSWORD", "EasyProxy API password") not in launcher.CREDENTIAL_KEYS:
    launcher.CREDENTIAL_KEYS.append(("EASYPROXY_PASSWORD", "EasyProxy API password"))

if __name__ == "__main__":
    wizard = launcher.Wizard()
    wizard.mainloop()
