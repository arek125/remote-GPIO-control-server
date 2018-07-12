# DHT

Connect sensor e.g(data pin can be attached to any GPIO pin you prefer):
![conn](https://www.raspberrypi-spy.co.uk/wp-content/uploads/2017/09/DHT11_pi.png)

## Install necessary tools
```bash
sudo apt-get install git-core build-essential python-pip
```

## Now install the Adafruit DHT library:
Enter this at the command prompt to download the library:
```bash
git clone https://github.com/adafruit/Adafruit_Python_DHT.git
cd Adafruit_Python_DHT
python -m pip install --upgrade pip setuptools wheel
```

Then install the library with:
```bash
sudo python setup.py install
```