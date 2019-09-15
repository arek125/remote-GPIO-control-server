#!/bin/sh
sed -i '7 c ExecStart=/usr/bin/python rgc-server.py' rgc.service 
sed -i '9 c WorkingDirectory='$(dirname $(realpath $0))'' rgc.service
cp -f rgc.service /lib/systemd/system/rgc.service
chmod 644 /lib/systemd/system/rgc.service
chmod +x rgc-server.py
systemctl daemon-reload
systemctl enable rgc.service