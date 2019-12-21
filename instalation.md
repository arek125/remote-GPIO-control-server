# Installation
## Download and unpack last release 
```bash
wget -O rgc-install.tar.gz https://github.com/arek125/remote-GPIO-control-server/releases/latest/download/rgc-install.tar.gz
tar -zxvf rgc-install.tar.gz
cd rgc
```
## Install necessary packages
```bash
sudo apt-get update
sudo apt-get install python-dev python-crypto python-systemd python-pip postgresql libpq-dev postgresql-client 
sudo pip install psycopg2 psutil
```
In case of:
```bash
E: Unable to locate package python-systemd
```
Add backports repository:
```bash
sudo nano /etc/apt/sources.list
Paste line:
For stretch: deb http://archive.debian.org/debian stretch-backports main
For jessie: deb http://archive.debian.org/debian jessie-backports main
sudo apt-get update
```

## Create postgresql user and database
```bash
sudo su postgres
createuser pi -P --interactive # set super user to yes
psql
CREATE DATABASE db_rgc;
#Ctrl+D 
#Ctrl+D 
```

## Create systemd service
```bash
sudo chmod 644 rgc-setup.sh
sudo bash rgc-setup.sh
```

## Configure server config
```bash
sudo nano rgc-config.ini # configure sql connection there and any other parameters as neded
```
[More about server config](serverConfig.md)

Keep time on server and client synchronized (diffrent timezones are supported).

## Server control
Use commands to control server app:
```bash
sudo systemctl start rgc.service
sudo systemctl stop rgc.service
sudo systemctl restart rgc.service
sudo systemctl status rgc.service
journalctl -u rgc.service # to see logs in case of problems (avalible form client too)
```

## Server access

To access web app go to http://deviceIpOrHost:port (eg. http://192.168.1.4:9999)
To access from android app, install apk file and configure connection.

## Update
```bash
cd /home/pi # or go to rgc main folder destination
wget -O rgc-update.tar.gz https://github.com/arek125/remote-GPIO-control-server/releases/latest/download/rgc-update.tar.gz
tar -zxvf rgc-update.tar.gz
sudo systemctl restart rgc.service
```