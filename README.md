# ci-ggregate

Aggregate the CI status/badges of automatically every 6 hours.

## CI Status

<!-- CI_BADGES_START -->
_Run the workflow once to populate this table._
<!-- CI_BADGES_END -->

---

## Setup

### Configure Monitored Orgs/Users

```bash
vim config.yml
```

### GH_TOKEN secret

The workflow needs a Personal Access Token (PAT) stored as a repository secret named `GH_TOKEN` to call the GitHub API with a decent rate limit (5 000 req/h vs 60 req/h unauthenticated).

**1. Create a Personal Access Token**

- Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
  (`https://github.com/settings/tokens`)
- Click **Generate new token (classic)**
- Give it a descriptive name (e.g. `ci-ggregate`)
- Select the **`public_repo`** scope (read-only access to public repositories is enough)
- Click **Generate token** and copy the value — you won't see it again

> If you also want to scan **private** repositories, select the full **`repo`** scope instead.

**2. Add the secret to this repository**

- Go to this repository on GitHub → **Settings → Secrets and variables → Actions**
- Click **New repository secret**
- Name: `GH_TOKEN`
- Value: paste the token you copied above
- Click **Add secret**

**3. Trigger the first run**

- Go to **Actions → Update CI Badges → Run workflow** (manual dispatch), or
- Simply push a change to `config.yml` or `update_badges.py`

The workflow then runs automatically every 6 hours.
