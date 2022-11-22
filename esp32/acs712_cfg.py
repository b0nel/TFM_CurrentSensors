from machine import Pin, ADC
import utime
import machine
import os
from adc1_cal import ADC1Cal
import time

# Sensor scale factor for DC current measurement
SCALE_FACTOR_30A = (66  * 3.3) / 5
SCALE_FACTOR_20A = (100 * 3.3) / 5
SCALE_FACTOR_5A  = (185 * 3.3) / 5

SCALES_FACTOR = {
    '30A': SCALE_FACTOR_30A,
    '20A': SCALE_FACTOR_20A,
    '5A': SCALE_FACTOR_5A
}

# sensor output voltage when no current is flowing
AREF = 3.3 # volt
DEFAULT_OUTPUT_VOLTAGE = AREF/2  # sensor vcc = 5 V, but a voltage divider is used to get 1.65 V from 2.5 V for the sensor out pin
ERROR = 0 # ampere


def getMaxValue(array):
        """
        Return index of max value from given array
        """
        max = 0
        for i in range(len(array)):
            if array[i] > array[max]:
                    max = i
        return max
        
def getMinValue(array):
        """
        Return index of min value from given array
        """
        min = 0
        for i in range(len(array)):
            if array[i] < array[min]:
                    min = i
        return min
class ACS712:
    """
    ACS712 class for current measurement
    """
    def __init__(self, pin, default_output_voltage=DEFAULT_OUTPUT_VOLTAGE, error=ERROR, calibration=0.05, calibration_factor=1.15):
        self.pin_number = pin
        self.scale_factor = 0
        self.default_output_voltage = default_output_voltage
        self.default_VRMS = 0
        self.error = error
        self.pin = Pin(pin, Pin.IN)
        self.adc = ADC(self.pin)
        self.adc.atten(ADC.ATTN_11DB)  # 3.3V input range
        #self.adc = ADC1Cal(self.pin, 1, None, 500, "ADC1 Calibrated")
        #self.adc.atten(ADC.ATTN_11DB)  # 3.3V input range
        self.calibration = calibration
        self.referenceVoltage = 0
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
            
        print("[calculateCurrent]Amps: ", abs(current), "A")

        return abs(current)

    def calculateWatts(self, current):
        """
        Calculate the power consumption in Watts.
        """
        watts = self.referenceVoltage * current
        print("[calculateWatts]Watts: ", watts, "W")

        return watts       
        
    def is_sensor_configured(self):
        for file in os.listdir():
            if file == 'sensor_configured.cfg':
                with open('sensor_configured.cfg', 'r') as file:
                    stored_value = file.read()
                    try: 
                        sensor_type, sensor_voltage = stored_value.split(',')
                        if self.process_sensor_type(sensor_type) and self.process_reference_voltage(sensor_voltage):
                            print("[is_sensor_configured]Sensor is configured as ", sensor_type, " with ", sensor_voltage, "V")
                            return True
                    except ValueError:
                        print("[is_sensor_configured]Invalid sensor config stored in flash")
                        self.referenceVoltage = 0
                        return False
                break #file found, no need to continue

        return False #file not found or config invalid
    
    def process_sensor_type(self, sensor_type):
        modules = ['5A', '20A', '30A']
        self.scale_factor = 0
        for type in modules:
            if sensor_type == type:
                self.scale_factor = SCALES_FACTOR[type]
                return True
        return False
    
    def process_reference_voltage(self, reference_voltage):
        accepted_AC_values = ['220', '230', '240']
        accepted_DC_values = ['12', '24', '48']

        if reference_voltage in accepted_AC_values or reference_voltage in accepted_DC_values:
            self.referenceVoltage = int(reference_voltage)
        else:
            self.referenceVoltage = 0
        
        return self.referenceVoltage != 0


    def set_sensor_config(self, value):
        try:
            sensor_type, sensor_voltage = value.split(',')
            if self.process_sensor_type(sensor_type) and self.process_reference_voltage(sensor_voltage):
                #save sensor config in flash
                with open('sensor_configured.cfg', 'w') as file:
                    file.write(str(value))
                    print("[set_sensor_config]Sensor configured. Sensor type: ", sensor_type, "Sensor voltage: ", sensor_voltage)
            else:
                print("[set_sensor_config]Invalid sensor config received.")
        except ValueError:
            print("[set_sensor_config]Invalid sensor config format received.")

    def readSensorVPP(self, logging=False):
        """
        Capture the peak to peak voltage of the current ADC signal.
        Period of measurement is 50ms. The ADC is sampled every 500us. 100 samples are taken.
        AC current in spain is 50Hz.
        We should be able to capture at least 2 full cycles of the sinusoidal signal with its peaks.
        """
        min_value = 4095
        max_value = 0
        average_value = 0
        start = time.ticks_ms()
        for i in range(100):
            adc_raw = self.adc.read()
            average_value += adc_raw
            if adc_raw < min_value:
                min_value = adc_raw
            elif adc_raw > max_value:
                max_value = adc_raw
            time.sleep_us(500)
        end = time.ticks_ms()
        max_value_V = ((max_value * 3.3) / 4095)
        min_value_V = ((min_value * 3.3) / 4095)
        average_value_V = ((average_value / 100) * 3.3) / 4095
        peak_to_peak = (max_value_V - min_value_V)
        if logging:
            print("[readSensorVPP]Time to read 100 samples: ", time.ticks_diff(end, start), "ms")
            print("[readSensorVPP]Average value: ", average_value_V, "V")
            print("[readSensorVPP]Max value: ", max_value_V, "V; Min value: ", min_value_V, "V; VPP: ", peak_to_peak, "V")

        return peak_to_peak, average_value_V 

    def RMSFilter(self, voltage_array, samples_to_remove=10, logging=False):
        """
        Removed more noisy readings from array of voltage
        """
        noisy_readings = list()
        if logging:
            print("[RMSFilter]Removing ", samples_to_remove, " noisy readings...")
            print("[RMSFilter]Voltage array before filtering: ", voltage_array)
        for i in range(samples_to_remove):
            to_remove = getMaxValue(voltage_array)
            noisy_readings.append(voltage_array[to_remove])
            voltage_array.pop(to_remove)
        
        
        if logging:
            print("[RMSFilter]Final samples array: ", voltage_array)
            print("[RMSFilter]Removed samples: ", noisy_readings)

        return voltage_array
    
    def readRMSVoltage(self, logging=False):
        voltage_RMS = 0
        voltage_RMS_nofilter = 0
        average_voltage = 0
        samplesVPP = list()
        samplesV = list()
        start = time.ticks_ms()
        while time.ticks_ms() - start < 1000:
            voltagePP, voltage = self.readSensorVPP(logging=False)
            samplesVPP.append(voltagePP * 0.3536)
            samplesV.append(voltage)
        end = time.ticks_ms()
        for i in range(len(samplesVPP)):
            voltage_RMS_nofilter += samplesVPP[i]
            average_voltage += samplesV[i]
        """
        for sample in samplesVPP:
            voltage_RMS_nofilter += sample
        """
        voltage_RMS_nofilter = voltage_RMS_nofilter / len(samplesVPP)
        average_voltage = average_voltage / len(samplesV)
        #apply sw filter
        samplesVPP = self.RMSFilter(samplesVPP, logging=False)
        for sample in samplesVPP:
            voltage_RMS += sample
        voltage_RMS = voltage_RMS / len(samplesVPP)

        if logging:
            print("[readRMSVoltage]Time to read ", len(samplesV), " values: ", time.ticks_diff(end, start), "ms")
            print("[readRMSVoltage]Voltage RMS: ", voltage_RMS * 1000, "mV", " default VRMS: ", self.default_VRMS * 1000, "mV")
            print("[readRMSVoltage]Voltage RMS no filter: ", voltage_RMS_nofilter * 1000, "mV", " default VRMS: ", self.default_VRMS * 1000, "mV")
            print("[readRMSVoltage]Average voltage: ", average_voltage * 1000, "mV", " default output voltage: ", self.default_output_voltage * 1000, "mV")
        
        return voltage_RMS, average_voltage

    def readRMSVoltage_BACK(self, logging=False):
        counter = 0
        voltage_RMS = 0
        start = time.ticks_ms()
        while time.ticks_ms() - start < 1000:
            voltage_RMS += self.readSensorVPP() * 0.3536
            counter += 1
        end = time.ticks_ms()
        voltage_RMS = voltage_RMS / counter
        if logging:
            print("[readRMSVoltage]Time to read ", counter, " values: ", time.ticks_diff(end, start), "ms")
            print("[readRMSVoltage]Voltage RMS: ", voltage_RMS * 1000, "mV", " default output voltage: ", self.default_VRMS * 1000, "mV")
        
        return voltage_RMS
        
    def checkZeroRange(self, voltage_RMS, voltage, logging=False):
        """
        Check if the voltage is in the zero Amps range.        
        """
        # if voltage is near default output voltage
        # and voltage_RMS is less than default VRMS
        # then we are in zero range
        if ((self.default_output_voltage + 0.05) > voltage > (self.default_output_voltage - 0.05)) and (voltage_RMS < self.default_VRMS):
            return True
        else:
            return False

    def readRMSAmps(self, logging=False):
        voltage_RMS, voltage = self.readRMSVoltage(logging=logging)
        #decide whether to apply an error correction or not
        if self.checkZeroRange(voltage_RMS, voltage, logging=logging):
            Amps_RMS = 0
        else:
            Amps_RMS = (voltage_RMS * 1000) / self.scale_factor
        if logging:
            print("[readRMSAmps]Current: ", Amps_RMS, "A")

        return Amps_RMS

    def getACWatts(self, logging=False):
        """
        Calculate the power consumption in Watts.
        """
        Amps_RMS = self.readRMSAmps(logging=logging)
        watts = self.referenceVoltage * Amps_RMS
        if logging:
            print("[getACWatts]Watts: ", watts, "W")

        return watts, Amps_RMS

    def calibrateSensorAC(self, seconds=10):
        """
        Calibrate the sensor to get the average voltage reading when there is no load.
        """
        print("[testCalibrateSensor]Calibrating sensor...")
        print("[testCalibrateSensor]Please disconnect the sensor from the load NOW!")
        for i in reversed(range(5)):
            print("[testCalibrateSensor]Starting calibration in " + str(i+1) + " seconds...")
            utime.sleep(0.5)
        print("[testCalibrateSensor]Calibrating...")
        counter = 0
        voltage_RMS = 0
        average_voltage = 0
        start = time.ticks_ms()
        while time.ticks_ms() - start < (1000 * seconds):
            min_value = 4095
            max_value = 0
            voltage = 0
            for i in range(100):
                adc_raw = self.adc.read()
                voltage += adc_raw
                if adc_raw < min_value:
                    min_value = adc_raw
                elif adc_raw > max_value:
                    max_value = adc_raw
                time.sleep_us(500)
            average_voltage += ((voltage * 3.3) / 4095) / 100
            counter = counter + 1
            max_value_V = ((max_value * 3.3) / 4095)
            min_value_V = ((min_value * 3.3) / 4095)
            peak_to_peak = (max_value_V - min_value_V)
            voltage_RMS += peak_to_peak * 0.3536
        end = time.ticks_ms()
        print("[readAmps2]Time to read ", counter, " values: ", time.ticks_diff(end, start), "ms")
        voltage_RMS = voltage_RMS / counter
        if voltage_RMS > 0.020:
            self.default_VRMS = voltage_RMS
        else:
            self.default_VRMS = 0.020
        self.default_output_voltage = average_voltage / counter
        #add 5mV to the default output voltage to avoid negative values
        self.default_VRMS = self.default_VRMS + 0.005
        print("[calibrateSensorAC]Sensor calibrated. Default output voltage: ", self.default_output_voltage, "V")
        print("[calibrateSensorAC]Sensor calibrated. Default VRMS: ", self.default_VRMS, "V")
