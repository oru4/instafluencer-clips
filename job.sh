set -e
mkdir -p out
B=https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ
for p in "mila_b20 hf_20261025_230649_c339733b-2cf9-4035-8e43-2ed4858c5b09" "mila_b22 hf_20261025_230650_792a80ee-721e-4e33-b8e4-233e6db3fd87" "nele_b20 hf_20261025_230648_cc6abba6-9058-4a56-b907-b2d2e729f53e" "hilde_b20 hf_20261025_230650_df9eed97-5f24-4215-8ce5-f414e0b07739" "hilde_b22 hf_20261025_230650_8217285e-513f-4d86-a634-e94f437f6751"; do
  set -- $p
  curl -sSf -o out/$1.png "$B/$2.png"
  ffmpeg -loglevel error -y -i out/$1.png -vf scale=360:-1 out/$1_k.jpg
done
ls -la out
