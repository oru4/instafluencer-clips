set -e
pip install -q resemblyzer
python3 job9.py
# nur hochladen, wenn die gewählte Stimme klar zu Milas bisherigen Clips passt
if python3 -c "import json,sys; b=json.load(open('out/job9.json')); sys.exit(0 if b['gewählt']!='Original' and b['kandidaten'][b['gewählt']]>=0.85 else 1)"; then
  gh release upload clips out/mila-2026-11-24-01.mp4 --clobber --repo "$GITHUB_REPOSITORY"
  echo HOCHGELADEN
else
  echo "NICHT HOCHGELADEN: Stimme passt nicht klar"
fi
