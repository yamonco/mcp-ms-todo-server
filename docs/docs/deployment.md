---
sidebar_position: 5
---

# Deployment Guide

## Build the Site

```bash
cd docs
npm run build
```

## Local Preview

```bash
npm run serve
```

## GitHub Pages Auto-Deploy
- On push to master/main, GitHub Actions will build and deploy to the `gh-pages` branch.
- See `.github/workflows/docusaurus.yml` for workflow details.

## Exclude Build Artifacts
- `docs/build/` is excluded from git via `.gitignore`.

## Custom Domain
- To use a custom domain, add a `CNAME` file in `docs/static/` and configure repository settings.

---

# Troubleshooting
- Check Node.js and npm versions
- Ensure Docker is running for API server
- Review GitHub Actions logs for deployment issues
