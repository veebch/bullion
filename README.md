![Action Shot](/image/bullion2.jpg)

[![YouTube Channel Views](https://img.shields.io/youtube/channel/views/UCz5BOU9J9pB_O0B8-rDjCWQ?label=YouTube&style=social)](https://www.youtube.com/channel/UCz5BOU9J9pB_O0B8-rDjCWQ)

# Bullion - Spot prices for metal (and more)

An ePaper Precious Metal/ Cryptocurrency/ Stock price ticker that runs as a Python script on a Raspberry Pi connected to a [Waveshare 2.7 inch monochrome ePaper display](https://www.waveshare.com/wiki/2.7inch_e-Paper_HAT). The script periodically (every 5 mins by default) takes data from [twelve data](https://www.twelvedata.com/) and prints a summary to the ePaper.

In addition to the spot price, it shows the gold/silver ratio (GSR) for gold, and the ratio to gold for all other precious metals.


# Getting started

## Prerequisites

(These instructions assume that your Raspberry Pi is already connected to the Internet, happily running `pip` and has `python3` installed)

If you are running the Pi headless, connect to your Raspberry Pi using `ssh`.

Connect to your ticker over ssh and update and install necessary packages 
```
sudo apt-get update
sudo apt-get install -y python3-pip mc git libopenjp2-7
sudo apt-get install -y libatlas-base-dev python3-pil
```

Enable spi (0=on 1=off)

```
sudo raspi-config nonint do_spi 0
```

Now clone the required software (Waveshare libraries and this script)

```
cd ~
git clone https://github.com/waveshare/e-Paper
git clone https://github.com/veebch/bullion.git
```
Move to the `btcticker` directory, copy the example config to `config.yaml` and move the required part of the waveshare directory to the `btcticker` directory
```
cd bullion
cp config_example.yaml config.yaml
cp -r /home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd .
rm -rf /home/pi/e-Paper
```

You will need an API key from twelvedata.com. Their free plan is sufficient for this code. Place your key in your `config.yaml` file.

Install the required Python3 modules
```
python3 -m pip install -r requirements.txt
```

## Add Autostart

```
cat <<EOF | sudo tee /etc/systemd/system/bullion.service
[Unit]
Description=bullion
After=network.target

[Service]
ExecStart=/usr/bin/python3 -u /home/pi/bullion/bullion.py
WorkingDirectory=/home/pi/bullion/
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF
```
Now, simply enable the service you just made and reboot
```  
sudo systemctl enable bullion.service
sudo systemctl start bullion.service

sudo reboot
```

Update frequency can be changed in the configuration file (default is 300 seconds).

# Configuration file

The file `config.yaml` (the copy of `config_example.yaml` you made earlier) contains a number of options that may be tweaked:

```
display:
  inverted: false
api:
  apikey: <insert twelvedata.com apikey>
ticker:
  currency: BTC,ETH,XAU,XAG,XPT
  fiatcurrency: USD
  timezone: Europe/Zurich
  refreshtime: 300
```

## Values

- **inverted**: Black text on grey background if **false**. Grey text on black background if **true**
- **apikey**: an api key for twelvedata.com
- **currency**: the symbols you would like to display (must be the twelvedata symbol name )
- **fiatcurrency**: currently only uses first one
- **timezone**: the timezone you're in
- **refreshtime**: (in seconds), how often to cycle to the next price


# Contributing

To contribute, please fork the repository and use a feature branch. Pull requests are welcome.

# Links

- A [fully configured unit](https://www.veeb.ch/store/p/w5exxxcog8vgv0tn4xiyw8pr31ltwp) or [custom case](https://www.veeb.ch/store/p/ticker-enclosure) can be obtained at [veeb.ch](http://www.veeb.ch/)


# Licencing

GNU GENERAL PUBLIC LICENSE Version 3.0
