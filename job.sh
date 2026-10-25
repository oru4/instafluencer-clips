set -e
for i in mila-2026-10-19-01 mila-2026-10-20-01 mila-2026-10-21-01 mila-2026-10-22-01 mila-2026-10-23-01 nele-2026-10-19-01 nele-2026-10-20-01 nele-2026-10-21-01 nele-2026-10-22-01 nele-2026-10-23-01 hilde-2026-10-19-01 hilde-2026-10-20-01 hilde-2026-10-21-01 hilde-2026-10-22-01 hilde-2026-10-23-01; do gh release upload clips out/$i.mp4 --clobber --repo "$GITHUB_REPOSITORY"; done
gh release view clips --repo "$GITHUB_REPOSITORY" --json assets --jq '.assets[].name' | sort
