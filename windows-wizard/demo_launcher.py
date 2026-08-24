from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import launcher as hardened


DEMO_VALUES = {
    "SSH_HOST": "192.0.2.20",
    "SSH_PORT": "22",
    "SSH_USER": "demo",
    "SSH_PASSWORD": "DEMO_NOT_REAL_SSH_PASSWORD",
    "SSH_KEY_PATH": "",
    "SSH_KEY_PASSPHRASE": "",
    "SUDO_PASSWORD": "DEMO_NOT_REAL_SUDO_PASSWORD",
    "REMOTE_DIR": "~/stream-stack-demo",
    "SERVER_LAN_IP": "192.0.2.20",
    "LAN_SUBNET": "192.0.2.0/24",
    "BASE_DOMAIN": "example.test",
    "TAILNET_DOMAIN": "wg.example.test",
    "PROXMOX_IP": "192.0.2.10",
    "AMP_IP": "192.0.2.30",
    "TIMEZONE": "Europe/Rome",
    "WIREGUARD_PRIVATE_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "WIREGUARD_ADDRESS_CIDR": "10.64.0.2/32",
    "CLOUDFLARE_API_TOKEN": "DEMO_NOT_REAL_CLOUDFLARE_TOKEN_000000000000",
    "TMDB_API_KEY": "00000000000000000000000000000000",
    "TMDB_ACCESS_TOKEN": "DEMO_NOT_REAL_TMDB_READ_ACCESS_TOKEN",
    "TVDB_API_KEY": "DEMO_NOT_REAL_TVDB_API_KEY",
    "TORBOX_API_KEY": "00000000-0000-4000-8000-000000000000",
    "ALLOWED_EMAIL": "demo@example.test",
    "GOOGLE_OAUTH_CLIENT_ID": "000000000000-demo.apps.googleusercontent.com",
    "GOOGLE_OAUTH_CLIENT_SECRET": "GOCSPX-DEMO-NOT-REAL",
    "NPM_ADMIN_EMAIL": "demo@example.test",
    "NPM_ADMIN_PASSWORD": "DEMO_NotReal_NPM_Password_123!",
    "LETSENCRYPT_EMAIL": "demo@example.test",
    "AIO_USER": "demo-admin",
    "AIO_PASSWORD": "DEMO_NotReal_AIO_Password_123!",
    "AIO_CONFIG_ACCESS_KEY": "DEMO_NOT_REAL_AIO_CONFIG_ACCESS_KEY",
    "STREMTHRU_USER": "demo-admin",
    "STREMTHRU_PASSWORD": "DEMO_NotReal_StremThru_Password_123!",
    "SEANIME_MAIN_PASSWORD": "DEMO_NotReal_Seanime_Password_123!",
    "SEANIME_SHARED_PASSWORD": "DEMO_NotReal_Shared_Seanime_Password_123!",
    "MDBLIST_API_KEY": "DEMO_NOT_REAL_MDBLIST_API_KEY",
    "GEMINI_API_KEY": "DEMO_NOT_REAL_GEMINI_API_KEY",
    "ANILIST_CLIENT_ID": "000000",
    "ANILIST_CLIENT_SECRET": "DEMO_NOT_REAL_ANILIST_CLIENT_SECRET",
    "TRAKT_CLIENT_ID": "DEMO_NOT_REAL_TRAKT_CLIENT_ID",
    "TRAKT_CLIENT_SECRET": "DEMO_NOT_REAL_TRAKT_CLIENT_SECRET",
    "GITHUB_USERNAME": "demo-user",
    "GITHUB_TOKEN": "DEMO_NOT_REAL_GITHUB_TOKEN",
    "AIOMETADATA_CONFIG_UUID": "00000000-0000-4000-8000-000000000001",
    "AIO_TRUSTED_UUID": "00000000-0000-4000-8000-000000000002",
    "HEADSCALE_USER": "demo",
}


class Wizard(hardened.Wizard):
    def __init__(self) -> None:
        self.demo_env_text = ""
        self._active_scroll_page = None
        super().__init__()

    def demo_enabled(self) -> bool:
        return self.bool_var("DEMO_DRY_RUN").get()

    def scroll_page(self) -> ctk.CTkScrollableFrame:
        page = super().scroll_page()
        self._active_scroll_page = page
        return page

    def enable_demo_mode(self) -> None:
        self.bool_var("DEMO_DRY_RUN").set(True)
        self.bool_var("USE_STANDARD_HOSTS").set(True)
        self.bool_var("AUTO_RUNTIME_KEYS").set(True)
        self.bool_var("AUTO_CONFIGURE_NPM").set(True)
        self.bool_var("INSTALL_PREREQS").set(False)
        self.bool_var("START_FULL_STACK").set(True)

        for key, value in DEMO_VALUES.items():
            self.var(key).set(value)
        for key, _, prefix in self.HOST_FIELDS:
            self.var(key).set(f"{prefix}.example.test")

        self.connected = False
        self.session.close()
        self.sidebar_status.configure(text="DEMO / DRY RUN: attivo", text_color=self.WARNING)
        if hasattr(self, "demo_mode_status"):
            self.demo_mode_status.configure(
                text="✓ Modalità demo attiva: nessuna connessione esterna verrà eseguita.",
                text_color=self.SUCCESS,
            )
        messagebox.showinfo(
            "Demo / Dry Run",
            "Valori fittizi caricati. Puoi attraversare tutto il wizard senza account reali.\n\n"
            "Il Dry Run genera e valida setup.env, ma non usa SSH, Docker, Cloudflare o API esterne.",
        )

    def disable_demo_mode(self) -> None:
        self.bool_var("DEMO_DRY_RUN").set(False)
        self.sidebar_status.configure(text="SSH: non connesso", text_color="#8091AA")
        if hasattr(self, "demo_mode_status"):
            self.demo_mode_status.configure(
                text="Modalità reale attiva. I valori demo restano visibili finché non li sostituisci.",
                text_color=self.WARNING,
            )

    def build_welcome(self) -> None:
        super().build_welcome()
        page = self._active_scroll_page
        if page is None or not page.winfo_exists():
            return
        body = self.card(
            page,
            "Demo / Dry Run",
            "Prova l'intero wizard con domini, IP, password e API key fittizi senza creare account o toccare un server.",
        )
        ctk.CTkLabel(
            body,
            text=(
                "Usa example.test e la rete TEST-NET 192.0.2.0/24. Il wizard genera realmente setup.env, "
                "controlla che sia parsabile e verifica i campi obbligatori, ma blocca ogni operazione remota."
            ),
            text_color="#C7D3E6",
            anchor="w",
            justify="left",
            wraplength=900,
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=1, column=0, columnspan=2, sticky="w")
        ctk.CTkButton(
            actions,
            text="Attiva Demo / Dry Run",
            fg_color=self.ACCENT,
            command=self.enable_demo_mode,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Torna a modalità reale",
            fg_color="#1B2B44",
            command=self.disable_demo_mode,
        ).pack(side="left", padx=8)
        self.demo_mode_status = ctk.CTkLabel(
            body,
            text=(
                "✓ Modalità demo attiva: nessuna connessione esterna verrà eseguita."
                if self.demo_enabled()
                else "Modalità demo non attiva."
            ),
            text_color=self.SUCCESS if self.demo_enabled() else "#8798B1",
            anchor="w",
        )
        self.demo_mode_status.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def build_server(self) -> None:
        super().build_server()
        if self.demo_enabled():
            self.test_btn.configure(text="Simula test SSH")
            self.connection_result.configure(text="Dry Run: SSH disabilitato", text_color=self.WARNING)

    def test_connection(self) -> None:
        if not self.demo_enabled():
            super().test_connection()
            return
        self.connected = False
        self.sidebar_status.configure(text="DEMO / DRY RUN: attivo", text_color=self.WARNING)
        if hasattr(self, "connection_result"):
            self.connection_result.configure(text="✓ Test simulato · nessuna rete usata", text_color=self.SUCCESS)
        messagebox.showinfo(
            "Test SSH simulato",
            "Dry Run attivo: il wizard non ha aperto alcuna connessione SSH. I campi server vengono validati solo sintatticamente.",
        )

    def build_review(self) -> None:
        super().build_review()
        if not self.demo_enabled():
            return
        page = self._active_scroll_page
        if page is None or not page.winfo_exists():
            return
        body = self.card(page, "Dry Run attivo")
        ctk.CTkLabel(
            body,
            text="Nessun server verrà modificato. Il passo successivo genererà setup.env soltanto in memoria locale.",
            text_color=self.WARNING,
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w")

    def build_deploy(self) -> None:
        super().build_deploy()
        if not self.demo_enabled():
            return
        self.deploy_btn.configure(text="Esegui Dry Run")
        self.deploy_status.configure(text="Dry Run pronto")
        self.logbox.configure(state="normal")
        self.logbox.delete("1.0", "end")
        self.logbox.insert(
            "end",
            "DEMO / DRY RUN\n"
            "Nessuna connessione SSH, chiamata API o operazione Docker verrà eseguita.\n"
            "Premi 'Esegui Dry Run' per generare e validare setup.env con valori fittizi.\n",
        )
        self.logbox.configure(state="disabled")

    def setup_env_text(self) -> str:
        text = super().setup_env_text()
        if not self.demo_enabled():
            return text
        return text.replace(
            "# Generated by Stream Stack Setup Wizard for Windows\n",
            "# Generated by Stream Stack Setup Wizard for Windows - DEMO / DRY RUN\n"
            "# ALL VALUES IN THIS FILE ARE FAKE AND MUST NOT BE USED IN PRODUCTION.\n",
            1,
        )

    def start_deployment(self) -> None:
        if not self.demo_enabled():
            super().start_deployment()
            return
        if self.deploying:
            return
        if self.validate_all(show_message=True):
            return

        self.deploying = True
        self.deploy_btn.configure(state="disabled")
        self.back_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
        self.set_deploy_status("Generazione setup.env demo…", 0.20)
        self.update_idletasks()

        try:
            self.append_log("[DRY RUN] Generazione configurazione locale…")
            env_text = self.setup_env_text()
            parsed = hardened.parse_env(env_text)
            self.demo_env_text = env_text
            self.set_deploy_status("Validazione configurazione…", 0.55)

            required = [
                "BASE_DOMAIN",
                "SERVER_LAN_IP",
                "LAN_SUBNET",
                "WIREGUARD_PRIVATE_KEY",
                "WIREGUARD_ADDRESS_CIDR",
                "CLOUDFLARE_API_TOKEN",
                "TMDB_API_KEY",
                "TMDB_ACCESS_TOKEN",
                "TVDB_API_KEY",
                "TORBOX_API_KEY",
                "ALLOWED_EMAIL",
                "GOOGLE_OAUTH_CLIENT_ID",
                "GOOGLE_OAUTH_CLIENT_SECRET",
            ]
            missing = [key for key in required if not parsed.get(key)]
            if missing:
                raise RuntimeError("setup.env demo incompleto: " + ", ".join(missing))
            if parsed.get("BASE_DOMAIN") != "example.test":
                raise RuntimeError("Il dominio demo non è quello riservato example.test")
            invalid_hosts = [
                key for key, _, _ in self.HOST_FIELDS
                if not parsed.get(key, "").endswith(".example.test")
            ]
            if invalid_hosts:
                raise RuntimeError("Hostname demo inattesi: " + ", ".join(invalid_hosts))
            if "CHANGE_ME_" in env_text:
                raise RuntimeError("Sono rimasti placeholder CHANGE_ME_* nel setup.env demo")

            self.generated_credentials = {
                key: parsed.get(key, "")
                for key, _ in hardened.CREDENTIAL_KEYS
                if parsed.get(key, "")
            }
            self.append_log(f"[OK] setup.env generato: {len(env_text.splitlines())} righe")
            self.append_log(f"[OK] {len(parsed)} variabili parsate correttamente")
            self.append_log("[OK] Campi obbligatori presenti")
            self.append_log("[OK] Domini demo confinati a *.example.test")
            self.append_log("[OK] Nessun placeholder CHANGE_ME_* presente")
            self.append_log("[SKIP] SSH: non eseguito")
            self.append_log("[SKIP] Cloudflare / API esterne: non eseguite")
            self.append_log("[SKIP] Docker / NPM / setup.sh: non eseguiti")
            self.append_log("\n=== DRY RUN COMPLETATO ===")
            self.set_deploy_status("Dry Run completato", 1.0)
            self.deploying = False
            self.after(250, lambda: self.show_page(9))
        except Exception as exc:
            self.deploying = False
            self.set_deploy_status("Dry Run fallito", 1.0)
            self.deploy_btn.configure(state="normal", text="Riprova Dry Run")
            self.back_btn.configure(state="normal")
            self.append_log(f"\nERRORE DRY RUN: {exc}")
            messagebox.showerror("Dry Run fallito", str(exc))

    def build_complete(self) -> None:
        if not self.demo_enabled():
            super().build_complete()
            return

        page = self.scroll_page()
        hero = ctk.CTkFrame(page, fg_color="#2A2110", border_width=1, border_color="#7A5714", corner_radius=14)
        hero.pack(fill="x", pady=(10, 18))
        ctk.CTkLabel(hero, text="✓", text_color=self.WARNING, font=ctk.CTkFont(size=54, weight="bold")).pack(pady=(26, 2))
        ctk.CTkLabel(hero, text="Dry Run completato", text_color="#FFF6DD", font=ctk.CTkFont(size=26, weight="bold")).pack()
        ctk.CTkLabel(
            hero,
            text="setup.env è stato generato e validato localmente. Nessun server o servizio esterno è stato contattato.",
            text_color="#D9C69B",
        ).pack(pady=(8, 24))

        checks = self.card(page, "Controlli superati")
        for idx, text in enumerate([
            "Configurazione setup.env generata con valori fittizi",
            "Parsing KEY=VALUE riuscito",
            "Campi obbligatori presenti",
            "Hostname confinati al dominio riservato example.test",
            "Nessun placeholder CHANGE_ME_* residuo",
            "Zero operazioni SSH / Docker / Cloudflare / API esterne",
        ]):
            ctk.CTkLabel(checks, text=f"✓  {text}", text_color="#D5E1F1", anchor="w").grid(
                row=idx, column=0, columnspan=2, sticky="w", pady=4
            )

        preview = self.card(page, "Anteprima setup.env demo", "Il file contiene esclusivamente credenziali fittizie.")
        box = ctk.CTkTextbox(
            preview,
            height=260,
            fg_color="#07101D",
            border_width=1,
            border_color="#21324A",
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none",
        )
        box.grid(row=0, column=0, columnspan=2, sticky="ew")
        box.insert("1.0", self.demo_env_text)
        box.configure(state="disabled")

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=(4, 16))
        ctk.CTkButton(
            actions,
            text="Salva setup.env demo…",
            fg_color=self.ACCENT,
            command=self.save_demo_env,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Copia setup.env demo",
            fg_color="#1B2B44",
            command=self.copy_demo_env,
        ).pack(side="left", padx=8)

        ctk.CTkLabel(
            page,
            text="Nota: il Dry Run verifica il wizard e il file setup.env. Non esegue setup.sh né testa credenziali reali contro provider esterni.",
            text_color="#8EA0B9",
            wraplength=950,
            justify="left",
        ).pack(anchor="w", pady=(0, 18))

    def save_demo_env(self) -> None:
        if not self.demo_env_text:
            messagebox.showerror("Dry Run", "Nessun setup.env demo è stato generato.")
            return
        path = filedialog.asksaveasfilename(
            title="Salva setup.env demo",
            initialfile="stream-stack-demo-setup.env",
            defaultextension=".env",
            filetypes=[("ENV files", "*.env"), ("All files", "*")],
        )
        if not path:
            return
        Path(path).write_text(self.demo_env_text, encoding="utf-8")
        messagebox.showinfo("Dry Run", f"File demo salvato in:\n{path}")

    def copy_demo_env(self) -> None:
        if not self.demo_env_text:
            return
        self.clipboard_clear()
        self.clipboard_append(self.demo_env_text)


if __name__ == "__main__":
    wizard = Wizard()
    wizard.mainloop()
