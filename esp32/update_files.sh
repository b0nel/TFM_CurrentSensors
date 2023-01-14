#!/bin/bash
ampy --port /dev/ttyUSB1 put main.py
ampy --port /dev/ttyUSB1 put acs712_cfg.py
ampy --port /dev/ttyUSB1 put mqtt_cfg.py
ampy --port /dev/ttyUSB1 put zmpt101b.py
ampy --port /dev/ttyUSB1 mkdir lib
ampy --port /dev/ttyUSB1 put lib/umqttsimple.py lib/umqttsimple.py
ampy --port /dev/ttyUSB1 put lib/ssd1306.py lib/ssd1306.py
