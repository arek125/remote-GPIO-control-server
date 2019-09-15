# Server config overview
Server config can be edited directly from file:
```bash
sudo nano rgc-config.ini
```
Or from web client: Home (config button)

Every time when config is changed server restart is required (web client will ask for it):
```bash
sudo systemctl restart rgc.service
```
## Postgresql config
```ini
[postgresql]
host = localhost
user = root
password = SECRET
db = db_rgc
```
Is necessary to set it before first start. 

## Main config
```ini
[main]
mode = all
mobilePort = 8888
wwwPort = 80
debug = no
passwordEnabled = no
password = SECRET
```
By setting `mode = all` both server (mobile and web) are runnig, limit it to one by setting `mode = wwwOnly` or `mode = mobileOnly`.  
`mobilePort` for android connection (UDP and TCP)  
`wwwPort` for http connection  
By setting `passwordEnabled = yes` encritpion is enabled and access is protected with setted `password`  

## Sensors config
```ini
[sensors]
ds18b20 = no
dht = no
dhtType = 11
dhtGpio = -1
tsl2561 = no
tsl2561Gain = 0
rotaryEncoder = no
rotaryEncoderClk = -1 
rotaryEncoderDt = -1 
rotaryEncoderMax = 10 
rotaryEncoderMin = 0
rangeSensor = no
rangeSensorTrigger = -1
rangeSensorEcho = -1
rangeSensorMaxValue = 340
```
`ds18b20` all conected to 1wire `yes` or `no`  
`dhtType` 11 or 22 or AM2302 (comma separated for more)  
`dhtGpio` GPIO BCM PIN number (comma separated for more)  
`tsl2561Gain` from 1-16 or 0 for auto gain  
`rotaryEncoderClk` GPIO BCM PIN number (comma separated for more)  
`rotaryEncoderDt` GPIO BCM PIN number (comma separated for more)  
`rotaryEncoderMax` max value of counter (comma separated for more)  
`rotaryEncoderMin` min value of counter (comma separated for more)  
`rangeSensorTrigger` GPIO BCM PIN number  
`rangeSensorEcho` GPIO BCM PIN number  
`rangeSensorMaxValue` value in cm  

## Radio frequency
```ini
[rf]
reciver = no
reciverGpio = -1
transmiter = no
transmiterGpio = -1
```
`reciverGpio` GPIO BCM PIN number  
`transmiterGpio` GPIO BCM PIN number  