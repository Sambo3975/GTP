mkdir -p /usr/bin/gtp-lib/
cp -r .venv /usr/bin/gtp-lib/
cp gtp-header.lark /usr/bin/gtp-lib/gtp-header.lark
cp gtp.lark /usr/bin/gtp-lib/gtp.lark
cp main.py /usr/bin/gtp-lib/main.py
chmod +x /usr/bin/gtp-lib/main.py

echo "/usr/bin/gtp-lib/.venv/bin/python /usr/bin/gtp-lib/main.py \$1" | tee /usr/bin/gtp > /dev/null
chmod +x /usr/bin/gtp
