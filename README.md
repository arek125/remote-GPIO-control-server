# Remote GPIO control server
Application allows you to control GPIO port on Pi devices via [android application client](https://play.google.com/store/apps/details?id=com.rgc) or build in www client.

Main features:
- Control the states of output pins
- Read the states of input pins and bind them with outputs
- Control PWM output pins
- Create sequential execution chains
- Read/store data from sensors DS18B20, DHT*, TSL2561
- Setup android notification base on output/input status or sensor value
- Plan output/pwm/chain state changes with multiple trigers 
<details><summary>Web client preview</summary>

![](webpreview.gif)
</details>

<details><summary>Android client preview</summary>

![](androidpreview.gif)
</details>

## Installation
### Download and unpack last release 
```bash
wget https://github.com/arek125/remote-GPIO-control-server/releases/download/2.1/rgc-server.tar.gz
tar -zxvf file.tar.gz
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
-mode <wwwOnly or mobileOnly># to limit mode, by default both modes are on
-wwwport <port number> #website port, default is 80
-mobileport <port number> #for tcp/udp mobile connection, default is 8888
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
Tested and working on Raspberry Pi devices with Raspiain OS.

Tested and working with Banana Pi devices with [this](https://github.com/BPI-SINOVOIP/RPi.GPIO) library.

Tested and working with Orange Pi Zero devices with [this](https://opi-gpio.readthedocs.io/en/latest/index.html) library.
(Import replacement from "import RPi.GPIO as GPIO" to "import OPi.GPIO as GPIO"  in file rgc-server.py is necessary)

Should work on similar devices/OS's but it requires a library [RPi.GPIO](https://pypi.python.org/pypi/RPi.GPIO) (Raspbian OS already has it) or another based on it. 



## License
Remote GPIO control server is available under the [MIT license](http://opensource.org/licenses/MIT).

## Donation
If you like this project please consider a donation:

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](arek125@gmail.com)
