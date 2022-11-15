from machine import Pin, ADC
import utime
import machine
import os
from adc1_cal import ADC1Cal

# Sensor scale factor for DC current measurement
MILLIVOLT_PER_AMPERE = 66  # 66 mV per Amp for 30 Amp sensor

# sensor output voltage when no current is flowing
AREF = 3.3 # volt
DEFAULT_OUTPUT_VOLTAGE = AREF/2  # sensor vcc = 5 V, but a voltage divider is used to get 1.65 V from 2.5 V for the sensor out pin
ERROR = 0 # ampere

class ACS712:
    """
    ACS712 class for current measurement
    """
    def __init__(self, pin, scale_factor=MILLIVOLT_PER_AMPERE, default_output_voltage=DEFAULT_OUTPUT_VOLTAGE, error=ERROR, calibration=0.05, calibration_factor=1.15):
        self.pin_number = pin
        self.scale_factor = scale_factor
        self.default_output_voltage = default_output_voltage
        self.error = error
        self.pin = Pin(pin, Pin.IN)
        #self.adc = ADC(self.pin)
        #self.adc.atten(ADC.ATTN_11DB)  # 3.3V input range
        self.adc = ADC1Cal(self.pin, 1, None, 500, "ADC1 Calibrated")
        self.adc.atten(ADC.ATTN_11DB)  # 3.3V input range
        self.calibration = calibration
        self.sensor_configured = None
        self.calibration_factor = calibration_factor
    
    def calibrateSensor(self, seconds=10):
        """
        Calibrate the sensor by measuring the sensor output voltage when no current is flowing.
        """
        print("[calibrateSensor]Calibrating sensor...")
        print("[calibrateSensor]Please disconnect the sensor from the load NOW!")
        for i in reversed(range(5)):
            print("[calibrateSensor]Starting calibration in " + str(i+1) + " seconds...")
            utime.sleep(0.5)
        print("[calibrateSensor]Calibrating...")
        averageVoltage = 0
        totalReadings = 0
        start = utime.time()
        while utime.time() - start < seconds:
            averageVoltage = averageVoltage + (self.readSensor() - averageVoltage) / (totalReadings + 1)
            totalReadings += 1

        self.default_output_voltage = averageVoltage
        
        print("[calibrateSensor]Sensor calibrated. Default output voltage: ", self.default_output_voltage, "V")
        print("[calibrateSensor]ADC Vref: ", self.adc.vref, "mV")

    def calibrateSensorFast(self):
        """
        Calibrate the sensor by measuring the sensor output voltage when no current is flowing.
        """
        print("[calibrateSensorFast]Calibrating sensor...")
        print("[calibrateSensorFast]Please disconnect the sensor from the load...")
        self.default_output_voltage = self.adc.voltage / 1000
        print("[calibrateSensorFast]Sensor calibrated. Default output voltage: ", self.default_output_voltage, "V")

    def calculateCurrent(self, voltage, calibration=0):
        """
        Calculate current from input voltage.
        """
        """
        print("[calculateCurrent]Voltage: ", voltage * 1000, "mV")
        print("[calculateCurrent]Default output voltage: ", self.default_output_voltage * 1000, "mV")
        print("[calculateCurrent]Scale factor: ", self.scale_factor, "mV/A")
        print("[calculateCurrent]Error: ", self.error, "A")
        """
        current = (voltage - self.default_output_voltage) * 1000 / self.scale_factor
        if current < 0 and current > -self.calibration:
            current = 0
        elif current > 0 and current < self.calibration:
            current = 0
        else:
            current = current * self.calibration_factor
            
        print("[calculateCurrent]Amps: ", current, "A")

        return current

    def readSensor(self):
        """
        Read the voltage from the ACS712 sensor.
        RETURNS:
            voltage in Volt
        """
        # read the sensor output voltage
        count = 0
        averageVoltage = 0
        start = utime.time()
        while utime.time() - start < 1:
            sensorVoltage = self.adc.voltage / 1000
            averageVoltage = averageVoltage + (sensorVoltage - averageVoltage) / (count + 1)
            count += 1
        
        print("[readSensor]Sensor voltage: ", averageVoltage, "V ---- Default output voltage: ", self.default_output_voltage, "V")

        return averageVoltage

    def timeToReadVoltage(self):
        """ Calculate the time needed to sample one value of the sensor"""
        start = utime.ticks_us()
        self.adc.voltage
        end = utime.ticks_us()
        print ("[timeToReadVoltage]Time to read voltage: ", utime.ticks_diff(end, start), "us")

    def calculateWatts(self, current, voltage=230):
        """
        Calculate the power consumption in Watts.
        """
        watts = voltage * current
        print("[getWatts2]Watts: ", watts, "W")

        return watts

    def getVPP(self):
        """
        Get the peak to peak voltage of the current signal.
        RETURNS:
            peak to peak voltage in mV
        """
        minValue = 1000000
        maxValue = 0
        start = utime.time()
        while utime.time() - start < 1:
            voltage = self.adc.voltage / 1000
            if voltage < minValue:
                minValue = voltage
            if voltage > maxValue:
                maxValue = voltage

        print("[getVPP]Max value: ", maxValue, "V; Min value: ", minValue, "V; VPP: ", (maxValue - minValue), "V")
        
        return (maxValue - minValue)

    def getWatts(self, reference_voltage=230, power_factor=1):
        """
        Get the current power consumption in Watt.
        RETURNS:
            power in Watt
        """
        voltage = self.getVPP()
        VRMS = (voltage / 2) * 0.707
        AmpsRMS = ((VRMS * 1000) / self.scale_factor) - self.error
        if AmpsRMS < 0 and AmpsRMS > -self.calibration:
            AmpsRMS = 0
        elif AmpsRMS > 0 and AmpsRMS < self.calibration:
            AmpsRMS = 0
        else:
            pass
        print("[getWatts]AmpsRMS: ", AmpsRMS, "A")
        watt = (AmpsRMS * reference_voltage) / power_factor # to be calibrated with a real wattmeter
        print("[getWatts]Watt: ", watt, "W")
        return watt, AmpsRMS

    def is_sensor_configured(self):
        for file in os.listdir():
            if file == 'sensor_configured.cfg':
                with open('sensor_configured.cfg', 'r') as file:
                    content_file = file.read()
                    if content_file == 'AC' or content_file == 'DC':
                        self.sensor_configured = content_file
                    else:
                        self.sensor_configured = None
                    print('[is_sensor_configured] Sensor configured as ' + content_file)
        return self.sensor_configured != None
    
    def set_sensor_configured(self, value):
        with open('sensor_configured.cfg', 'w') as file:
            if value == 'AC' or value == 'DC':
                file.write(value)
                self.sensor_configured = value
            else:
                file.write('None')
                self.sensor_configured = None
    
    def is_AC(self):
        return self.sensor_configured == 'AC'
    
    def is_DC(self):
        return self.sensor_configured == 'DC'