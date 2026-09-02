from __future__ import annotations

import socket
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor

import customtkinter as ctk

import demo_launcher as current

# Keep the GUI thin: it still writes setup.env and delegates all real logic to
# the same Linux setup.sh used from CLI. We only expose the new current services.
EXTRA_HOST_FIELDS = [
    ("EASYPROXY_HOST", "EasyProxy", "easyproxy"),
    ("TVVOO_HOST", "TvVoo", "tvvoo"),
    ("AIOMANAGER_HOST", "AIOManager", "aiomanager"),
]

# launcher.py filters which generated secrets are shown at the end. Mutating the
# shared list keeps the transport/deployment code single-sourced.
for item in [
    ("EASYPROXY_PASSWORD", "EasyProxy password"),
    ("AIOMANAGER_ENCRYPTION_KEY", "AIOManager encryption key"),
]:
    if item not in current.hardened.CREDENTIAL_KEYS:
        current.hardened.CREDENTIAL_KEYS.append(item)


LOCAL_SERVICES = [
    ("Nginx Proxy Manager", 81, "http"),
    ("AdGuard Home setup", 3010, "http"),
    ("Portainer", 9443, "https"),
    ("Headplane", 3000, "http"),
    ("AIOStreams", 4444, "http"),
    ("AIOMetadata", 1337, "http"),
    ("MediaFlow Proxy", 8888, "http"),
    ("Honey", 4173, "http"),
    ("EasyProxy", 8760, "http"),
    ("TvVoo", 5000, "http"),
    ("AIOManager", 1610, "http"),
    ("Comet", 2020, "http"),
    ("StremThru", 9090, "http"),
    ("Jackett", 9117, "http"),
    ("StreamViX", 7860, "http"),
    ("Seanime", 43211, "http"),
    ("Seanime Shared", 43311, "http"),
]


class Wizard(current.Wizard):
    """Final wizard layer aligned to the current streams-aio topology."""

    HOST_FIELDS = [
        item for item in current.Wizard.HOST_FIELDS
        if item[0] != "JACKETTIO_HOST"
    ] + EXTRA_HOST_FIELDS

    def _port_open(self, host: str, port: int, timeout: float = 0.45) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def probe_local_services(self) -> dict[int, bool]:
        host = self.var("SERVER_LAN_IP").get().strip()
        if not host:
            return {port: False for _, port, _ in LOCAL_SERVICES}
        pending = {port for _, port, _ in LOCAL_SERVICES}
        results = {port: False for _, port, _ in LOCAL_SERVICES}
        for attempt in range(4):
            if not pending:
                break
            ports = sorted(pending)
            with ThreadPoolExecutor(max_workers=min(16, len(ports))) as pool:
                checks = list(pool.map(lambda p: (p, self._port_open(host, p)), ports))
            for port, ok in checks:
                if ok:
                    results[port] = True
                    pending.discard(port)
            if pending and attempt < 3:
                time.sleep(0.8)
        return results

    def build_complete(self) -> None:
        if self.demo_enabled():
            super().build_complete()
            return

        super().build_complete()
        children = self.content_holder.winfo_children()
        if not children:
            return
        page = children[0]
        host = self.var("SERVER_LAN_IP").get().strip()
        started = self.bool_var("START_FULL_STACK").get()
        results = self.probe_local_services() if started else {port: False for _, port, _ in LOCAL_SERVICES}
        ok_count = sum(1 for value in results.values() if value)
        total = len(LOCAL_SERVICES)

        if started and ok_count == total:
            title = "Setup locale pronto"
            subtitle = f"{ok_count}/{total} servizi LAN raggiungibili da questo PC."
            border = "#1E5B46"
            heading_color = self.SUCCESS
        elif started:
            title = "Verifica accesso locale"
            subtitle = f"{ok_count}/{total} porte LAN rispondono. I servizi mancanti possono essere ancora in avvio."
            border = "#7A5714"
            heading_color = self.WARNING
        else:
            title = "Stack non avviato"
            subtitle = "I file sono configurati, ma la verifica LAN richiede l'avvio dello stack completo."
            border = "#7A5714"
            heading_color = self.WARNING

        body = ctk.CTkFrame(page, fg_color="#0D192A", border_width=1, border_color=border, corner_radius=14)
        body.pack(fill="x", pady=(8, 18))
        body.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(body, text=title, text_color=heading_color, font=ctk.CTkFont(size=21, weight="bold"), anchor="w").grid(row=0, column=0, columnspan=4, sticky="ew", padx=18, pady=(16, 3))
        ctk.CTkLabel(body, text=subtitle, text_color="#AFC0D9", anchor="w", justify="left", wraplength=980).grid(row=1, column=0, columnspan=4, sticky="ew", padx=18, pady=(0, 12))

        for row, (label, port, scheme) in enumerate(LOCAL_SERVICES, start=2):
            ok = results.get(port, False)
            status_text = "● OK" if ok else ("● KO" if started else "● OFF")
            status_color = self.SUCCESS if ok else self.DANGER if started else self.WARNING
            url = f"{scheme}://{host}:{port}" if host else ""
            ctk.CTkLabel(body, text=status_text, width=62, text_color=status_color, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", padx=(18, 6), pady=4)
            ctk.CTkLabel(body, text=label, width=170, text_color="#D7E1F0", anchor="w").grid(row=row, column=1, sticky="w", padx=(0, 8), pady=4)
            ctk.CTkLabel(body, text=url, text_color="#9FB0CA", anchor="w").grid(row=row, column=2, sticky="ew", pady=4)
            ctk.CTkButton(body, text="Apri", width=68, height=30, fg_color="#1B2B44", state="normal" if url else "disabled", command=lambda u=url: webbrowser.open(u)).grid(row=row, column=3, padx=(8, 18), pady=4)

        ctk.CTkLabel(body, text="La raggiungibilità della porta non sostituisce il controllo applicativo. AdGuard, Jackett e l'import JSON AIOStreams restano gli ultimi passaggi manuali previsti.", text_color="#8294AE", anchor="w", justify="left", wraplength=980).grid(row=2 + total, column=0, columnspan=4, sticky="ew", padx=18, pady=(10, 16))


if __name__ == "__main__":
    wizard = Wizard()
    wizard.mainloop()
