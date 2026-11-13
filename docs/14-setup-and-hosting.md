# 14. Setting up and hosting Nabz

How to run Nabz again from a fresh clone, on your own computer or on a server people can reach. Everything runs in Docker; nothing else has to be installed.

| | Your computer | A server |
|---|---|---|
| Compose file | `compose.yaml` | `compose.prod.yaml` |
| Settings | `.env` from `.env.example` | `.env` from `.env.production.example` |
| Web app | Vite with hot reload, <http://localhost:5173> | Built once, served by Caddy with HTTPS |
| Email | Mailpit inbox, <http://localhost:8025> | A real mail service over SMTP |
| Tests and tools | Installed | Not installed |

## 1. On your own computer

You need Docker Desktop (or Docker Engine with Compose v2) and about 10 GB of free disk space. The first build takes a few minutes.

```bash
git clone https://github.com/Bishnu2430/Nabz.git
```

```bash
cd Nabz
```

```bash
cp .env.example .env
```

Open `.env` and set `POSTGRES_PASSWORD` to anything. Add `GROQ_API_KEY` for explanations written by the model and `ELEVENLABS_API_KEY` for narration. Without them, Nabz uses the safe template and has no audio, and everything else works.

Start the stack and prepare the database. Run these once, in this order:

```bash
docker compose up --build -d
```

```bash
docker compose exec api alembic upgrade head
```

```bash
docker compose exec api python -m app.cli seed-catalogue
```

```bash
docker compose exec api python -m tools.knowledge model
```

```bash
docker compose exec api python -m app.cli load-knowledge
```

- **`alembic upgrade head`** creates the tables.
- **`seed-catalogue`** loads the 108 tests, ranges, units and percentiles from `data/catalogue/`.
- **`tools.knowledge model`** downloads the embedding model (135 MB) into `data/external/models/` and checks each file's SHA-256.
- **`load-knowledge`** embeds the committed MedlinePlus passages for retrieval.

Open <http://localhost:5173> and sign up. The confirmation email arrives in Mailpit at <http://localhost:8025>. For a ready-made family with five years of reports:

```bash
docker compose exec api python -m tools.family --email <your email>
```

Staff accounts (reviewer, admin, doctor) are made with `tools.staff`; see the [README](../README.md#quick-start). It prints the new password and the two-step sign-in key once.

Check that everything is in place:

```bash
docker compose exec api pytest -q
```

```bash
docker compose exec web npm test
```

**Stopping and starting.** `docker compose stop` stops the stack and keeps everything. `docker compose up -d` starts it again. `docker compose down` removes the containers but keeps the data volumes. `docker compose down -v` also deletes the database and the uploads.

## 2. On a server

### 2.1 What you need

- **A Linux server.** For example Ubuntu 24.04 with 2 CPUs, 4 GB of memory and 25 GB of disk. Measured on the trial in §2.3: reading a photo by OCR took 18 s, and the worker peaked at about 450 MB. The API used about 120 MB, the database 50 MB and Caddy 16 MB, so 2 GB is the minimum.
- **Docker Engine with Compose.** Install it from <https://docs.docker.com/engine/install/>.
- **A domain name.** Add a DNS `A` record that points it at the server's address.
- **Open ports.** Ports 80 and 443 must be reachable. Caddy uses 80 to get the certificate.
- **A mail service with SMTP.** For example Brevo, Mailgun, Amazon SES or Zoho. Nobody can sign in before confirming their email, so this has to work first.

### 2.2 Install

```bash
git clone https://github.com/Bishnu2430/Nabz.git
```

```bash
cd Nabz
```

```bash
cp .env.production.example .env
```

Fill in `.env`:

- **`SITE_ADDRESS` and `APP_BASE_URL`:** your domain, the second with `https://`.
- **`SECRET_KEY` and `POSTGRES_PASSWORD`:** generate each with the command in the file. Keep `SECRET_KEY` with your backups. If it changes, everyone must set up two-step sign-in again.
- **`SMTP_*` and `MAIL_FROM`:** from your mail service. Send from an address on a domain the mail service has verified.
- **`GROQ_API_KEY` and `ELEVENLABS_API_KEY`:** optional.

Build and start. The first build takes 15–20 minutes:

```bash
docker compose -f compose.prod.yaml up -d --build
```

Until the tables exist, the worker restarts every few seconds with `relation "processing_job" does not exist`. That is expected. Prepare the database, as on your computer:

```bash
docker compose -f compose.prod.yaml exec api alembic upgrade head
```

```bash
docker compose -f compose.prod.yaml exec api python -m app.cli seed-catalogue
```

```bash
docker compose -f compose.prod.yaml run --rm --user "$(id -u):$(id -g)" api python -m tools.knowledge model
```

```bash
docker compose -f compose.prod.yaml exec api python -m app.cli load-knowledge
```

The model download runs as your own user (`--user`), because it writes into the `data/` folder of the clone, which your user owns. The other commands only write to the database.

Make the first admin. The command prints a password and a two-step sign-in key once; add the key to an authenticator app:

```bash
docker compose -f compose.prod.yaml exec api python -m tools.staff --email you@example.org --role admin
```

Open `https://<your domain>`. The first visit can take a few seconds while Caddy gets the certificate. To see what is happening:

```bash
docker compose -f compose.prod.yaml logs -f api worker web
```

### 2.3 Try the server setup on your computer first

Use `SITE_ADDRESS=:80`, `APP_BASE_URL=http://localhost:8088`, `COOKIE_SECURE=false` and `HTTP_PORT=8088` in the `.env` of a separate clone. Then open <http://localhost:8088>.

- **Model download:** the `--user` option is not needed on Docker Desktop. Use `exec api python -m tools.knowledge model`.
- **Accounts without email:** make one with `python -m app.cli create-user --email … --password …`. It creates an account whose email is already confirmed.

This is how `compose.prod.yaml` was checked before it was committed, on 13 November 2026, from a fresh clone. The checks:
- the setup commands of §2.2;
- a PDF and a photo uploaded through Caddy, with live progress;
- confirmation, analysis and the explanation;
- the backup and restore of §2.5.

### 2.4 Updating to a newer version

```bash
git pull
```

```bash
docker compose -f compose.prod.yaml up -d --build
```

```bash
docker compose -f compose.prod.yaml exec api alembic upgrade head
```

If the catalogue or the knowledge passages changed, run `seed-catalogue` and `load-knowledge` again. Both can be run any number of times.

### 2.5 Backups

Three things hold everything:

- the database;
- the `uploads` volume, which holds the reports and records people uploaded;
- your `.env`.

Back up the database:

```bash
docker compose -f compose.prod.yaml exec -T db pg_dump -U nabz -Fc nabz > nabz-$(date +%F).dump
```

Back up the uploads:

```bash
docker run --rm -v nabz-prod_uploads:/uploads:ro -v "$PWD":/backup alpine tar czf /backup/uploads-$(date +%F).tar.gz -C /uploads .
```

Restore the database into a fresh install, after `alembic upgrade head`:

```bash
docker compose -f compose.prod.yaml exec -T db pg_restore -U nabz -d nabz --clean --if-exists < nabz-2026-11-13.dump
```

Restore the uploads:

```bash
docker run --rm -v nabz-prod_uploads:/uploads -v "$PWD":/backup alpine tar xzf /backup/uploads-2026-11-13.tar.gz -C /uploads
```

Keep backups off the server, and encrypt them: they hold health data.

## 3. Other places to host

- **Render.** The whole system can run there:
  - the API as a Docker web service and the worker as a background worker, both from `backend/Dockerfile`;
  - Render Postgres, which has pgvector;
  - the web app as a static site, with `/v1/*` rewritten to the API, so pages and API share one address (the session cookie is `SameSite=Strict`).

  Uploads must be reachable by both the API and the worker, and a Render disk attaches to only one service. Use object storage, or run both in one service. The free tier's 512 MB of memory is too small for OCR and the embedding model.
- **Vercel, Netlify and other static hosts.** They can serve only the web app. The worker runs all the time, the models are too large for serverless functions, and uploads are kept on disk.
- **A Windows or Mac computer** runs `compose.prod.yaml` the same way, in Docker Desktop.

## 4. Before real people use it

Nabz is an academic prototype, not a medical device. Before anyone uses it for their own reports:

- **Clinical review.** Have a doctor review the critical limits and the explanations ([clinical review packet](review/clinical-review-packet.md)).
- **Language review.** Have native speakers review the Hindi and Odia text.
- **Privacy.** Health data is sensitive personal data under India's DPDP Act, 2023 ([10](10-safety-privacy-compliance.md)). Publish the terms and the privacy notice under your own name, and keep the server and its backups encrypted.
- **Security.** Caddy's HTTPS and HSTS close the open items of the security assessment that needed HTTPS ([13](13-security-assessment.md)). The others still stand.
- **Model limits.** Groq's free tier allows about 200,000 tokens a day. That covers roughly 25 explanations with their safety check ([11 §16](11-test-and-evaluation-plan.md)). After that, Nabz falls back to the template until the next day, so a paid plan is needed for regular use.

## 5. When something goes wrong

| Symptom | Likely cause |
|---|---|
| No sign-up email | Wrong `SMTP_*` values. The API logs "email … could not be sent"; check `logs api`. |
| Certificate error, or the site doesn't load | The DNS record doesn't point at the server yet, or port 80 is closed. Check `logs web`. |
| Explanations always use the template | No `GROQ_API_KEY`, the person gave no consent for AI, the embedding model or knowledge isn't loaded, or the daily limit is used up. The admin console's system page shows which. |
| "Set SECRET_KEY (32+ characters)" | `SECRET_KEY` in `.env` is empty or short. |
| On Git Bash for Windows, a path like `/srv/data/…` is changed | Prefix the command with `MSYS_NO_PATHCONV=1`. |

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-13 | First version: local setup from a fresh clone, hosting with `compose.prod.yaml`, backups, other hosts |
