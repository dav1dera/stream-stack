# AIOStreams runtime template

`stream-stack` ships a **sanitized reference configuration** for AIOStreams based on the reference deployment, but it does not publish the live backup exported from the source server.

## Security model

The tracked source is:

```text
data/aiostreams/runtime-template.json.gz.b64
```

It is a gzip + base64 transport of the sanitized JSON. Compression is only for keeping the tracked payload compact; it is **not** a security boundary. CI decodes and scans it on every validation run.

The public source has been normalized so it does not contain installation-specific secrets or identity data:

- variant IDs/names are `profile-01`, `profile-02`, ...;
- AIOStreams auth values inside variant scripts are placeholders;
- TMDB API key/access token are placeholders;
- StreamViX and TvVoo manifest URLs are placeholders because their original forms can embed proxy credentials;
- service `credentials` objects remain empty;
- the user-level `trusted` flag is removed;
- linked-account push behavior defaults to `ask` instead of automatically pushing a newly imported public template.

The validator rejects the tracked template if it detects an unexpected placeholder, JWT-like token, RFC1918 IP, known private hostname, non-empty credential dictionary or a non-anonymized variant.

## Runtime rendering

During `./setup.sh`, after the installation values and generated secrets are resolved, this runs automatically:

```bash
python3 scripts/render_aiostreams_template.py
```

It produces:

```text
data/aiostreams/runtime-template.json
```

The renderer fills only values belonging to the **new installation**, including:

- `AIO_USER` / `AIO_PASSWORD` used by the variant scripts;
- `TMDB_API_KEY` / `TMDB_ACCESS_TOKEN`;
- StreamViX public hostname;
- TvVoo public hostname;
- EasyProxy public hostname and generated password embedded in the StreamViX/TvVoo configuration URLs.

The generated file is intentionally different from the tracked source:

```text
tracked source       -> sanitized, safe to publish
runtime-template.json -> contains local installation secrets, NEVER publish
```

`runtime-template.json` is gitignored and written with mode `0600`.

## Windows wizard

At the end of a successful real deployment, the Windows wizard reads the generated template over the existing SSH connection and exposes:

```text
Salva JSON per import AIOStreams
```

The file is saved only where the operator chooses on the Windows PC. It is not committed to GitHub.

Import it in AIOStreams from:

```text
Save & Install -> Backups -> Import
```

The template contains the reference filters, sorting, formatter, presets, health checks and anonymized variants. Application state that cannot safely be fabricated or published still remains operator-specific, especially external provider/indexer/Usenet credentials and Jackett account/indexer state.

## Updating the reference template

Never commit a fresh live AIOStreams export directly.

Before replacing the tracked payload:

1. inspect the export for secrets both in normal JSON fields and inside arbitrary strings;
2. inspect variant scripts for usernames/passwords/API tokens;
3. decode any opaque/base64 configuration URLs and inspect the decoded value;
4. anonymize identity/profile names;
5. replace dynamic installation values with the supported `CHANGE_ME_*` placeholders;
6. keep `credentials` dictionaries empty;
7. run:

```bash
python3 scripts/validate_stack.py
```

A backup exported with an application's own "exclude credentials" option is not automatically considered safe for a public repository: credentials may still be embedded in scripts or encoded URLs.