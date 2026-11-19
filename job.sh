set -e
gh release upload clips out/mila-2026-11-24-01.mp4 --clobber --repo "$GITHUB_REPOSITORY"
gh release view clips --repo "$GITHUB_REPOSITORY" --json assets --jq ".assets[].name" | grep mila-2026-11-24
