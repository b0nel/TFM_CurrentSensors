#!/bin/bash
for f in *
do
    if [ $f != "update_files.sh" ]
    then
        echo "Copying $f file to ESP32"
        ampy --port /dev/ttyUSB0 -b 115200 put $f
    fi
done