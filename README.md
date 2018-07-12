# Remote GPIO control server
Application allows you to control GPIO port on Pi devices via [android application client](https://play.google.com/store/apps/details?id=com.rgc).


## Installation
### Download and unpack last release 
```bash
wget https://github.com/arek125/remote-GPIO-control-server/releases/download/2.0/rgc-server.tar.gz
tar -zxvf rgc-server.tar.gz
cd rgc
```
### Run instalation script
```bash
sudo chmod 644 rgc-setup.sh
sudo bash rgc-setup.sh
```

### Set startup parameters data
Modify service file:
```bash
sudo nano /lib/systemd/system/rgc.service
```
In line 'ExecStart' set parametrs (e.g):
```bash
ExecStart=/usr/bin/python rgc-server.py -port 8889 -password Password123
```
Available parameters:
```bash
-port <port number> #for tcp/udp connection, default is 8888
-password <password string> #for encryprion,if this parameter is not set encrypted communication is disabled
-debug #for debugging purposes
-db_path <database file path string> #to set diffrent database file path
-ds18b20 #to enalbe ds18b20 sensors support all connected to 1wire, see md file for instalation instructions
-dht <11 or 22 or AM2302> <GPIO BCM PIN number> #to enalbe dht* sensor support, see md file for instalation instructions
-tsl2561 <gain from 1-16 or 0 for auto gain> #to enalbe tsl2561 sensor support, see md file for instalation instructions
```

After parameters are changed call:
```bash
sudo systemctl daemon-reload
sudo systemctl restart rgc.service
```

Keep time on server and client synchronized (diffrent timezones are supported).

## Server control
Use commands to control server app:
```bash
sudo systemctl start rgc.service
sudo systemctl stop rgc.service
sudo systemctl restart rgc.service
sudo systemctl status rgc.service
journalctl -u rgc.service # to see logs in case of problems
```

## Support
Application tested on Raspberry pi devices with Raspiain OS.
Should work on similar devices/OS's but it requires a library [RPi.GPIO](https://pypi.python.org/pypi/RPi.GPIO) 0.6.2 or later (Raspbian OS already has it).

## License
Remote GPIO control server is available under the [MIT license](http://opensource.org/licenses/MIT).

## Donation
If you like this project please consider a donation:

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=arek125%40gmail%2ecom&lc=PL&item_name=RGC%20FAMILY&currency_code=USD&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHostedGuest)
