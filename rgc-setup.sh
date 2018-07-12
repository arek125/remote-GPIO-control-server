#!/bin/sh
apt-get update
apt-get install python-dev python-crypto python-systemd
sed -i '7 c ExecStart=/usr/bin/python rgc-server.py' rgc.service 
sed -i '9 c WorkingDirectory='$(dirname $(realpath $0))'' rgc.service
mv -f rgc.service /lib/systemd/system/rgc.service
chmod 644 /lib/systemd/system/rgc.service
chmod +x rgc-server.py
systemctl daemon-reload
systemctl enable rgc.service