#!/bin/bash
ampy --port /dev/ttyUSB0 put main.py
ampy --port /dev/ttyUSB0 put acs712_cfg.py
ampy --port /dev/ttyUSB0 put mqtt_cfg.py
ampy --port /dev/ttyUSB0 mkdir lib
ampy --port /dev/ttyUSB0 put lib/umqttsimple.py lib/umqttsimple.py
ampy --port /dev/ttyUSB0 put lib/ssd1306.py lib/ssd1306.py
