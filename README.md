# Remote GPIO control server
Application allows you to control GPIO port on Pi devices via [android application client](https://play.google.com/store/apps/details?id=com.rgc).

## Installation
```bash
sudo apt-get install python-dev python-crypto
```
It also requires a library [RPi.GPIO](https://pypi.python.org/pypi/RPi.GPIO) 0.6.2 or later (Raspbian OS already has it).

## Usage
To run server:
```bash
python rgc-server1_1.py -port <port> -password <password>
```
Without -password parameter encrypted communication is disabled

For autostart add above to file:
```bash
/etc/rc.local
```

Keep time on server and client synchronized (diffrent timezones are suported).


## License
Remote GPIO control server is available under the [MIT license](http://opensource.org/licenses/MIT).
