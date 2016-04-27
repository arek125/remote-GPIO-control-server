# Remote GPIO control server
Application allows you to control GPIO ports on Pi devices via [android application client](https://play.google.com/store/apps/details?id=com.rgc).

## Installation
```bash
sudo apt-get install python-dev python-crypto
```
It also requires a library [RPi.GPIO](https://pypi.python.org/pypi/RPi.GPIO) 0.6.2 or later.

## Usage
```bash
python rgc-server1_0.py -port <port> -password <password>
```
Without -password parameter encrypted communication is disabled

## License
Remote GPIO control server is available under the [MIT license](http://opensource.org/licenses/MIT).
