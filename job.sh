set -e
gh release upload clips out/mila-2026-10-19-01.mp4 --clobber --repo "$GITHUB_REPOSITORY"
echo upload-ok
