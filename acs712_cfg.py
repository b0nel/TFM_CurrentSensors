from machine import Pin, ADC
import utime

# Sensor scale factor for DC current measurement
MILLIVOLT_PER_AMPERE = 66  # 66 mV per Amp for 30 Amp sensor -> if 3.3V divider is used them 55 mV per Amp

# sensor output voltage when no current is flowing
AREF = 3.3 # volt
DEFAULT_OUTPUT_VOLTAGE = AREF/2  # sensor vcc = 5 V, but a voltage divider is used to get 1.65 V from 2.5 V for the sensor out pin
ERROR = -0 # ampere

class ACS712:
    """
    ACS712 class for current measurement
    """
    def __init__(self, pin, scale_factor=MILLIVOLT_PER_AMPERE, default_output_voltage=DEFAULT_OUTPUT_VOLTAGE, error=ERROR, hysteresis=0.5):
        self.pin_number = pin
        self.scale_factor = scale_factor
        self.default_output_voltage = default_output_voltage
        self.error = error
        self.pin = Pin(pin, Pin.IN)
        self.adc = ADC(self.pin)
        self.adc.atten(ADC.ATTN_11DB)  # 3.3V input range
        self.hysteresis = hysteresis

    def calibrateSensor(self):
        """
        Calibrate the sensor by measuring the sensor output voltage when no current is flowing.
        """
        print("Calibrating sensor...")
        print("Please disconnect the sensor from the load and press enter.")
        input()
        print("Measuring...")
        now = utime.time()
        averageVoltage = 0
        for i in range(6000):
            averageVoltage = averageVoltage + ((self.adc.read_u16() * AREF / 65535) - averageVoltage) / (i + 1)
            utime.sleep(0.01)
        
        self.default_output_voltage = averageVoltage
        end = utime.time()
        print("Sensor calibrated. Default output voltage: ", self.default_output_voltage, "V")
        print("Calibration took ", end - now, " seconds.")

    def calibrateSensorFast(self):
        """
        Calibrate the sensor by measuring the sensor output voltage when no current is flowing.
        """
        print("Calibrating sensor...")
        print("Please disconnect the sensor from the load and press enter.")
        self.default_output_voltage = self.adc.read_u16() * AREF / 65535
        print("Sensor calibrated. Default output voltage: ", self.default_output_voltage, "V")

    def readCurrent(self):
        """
        Read the current from the ACS712 sensor.
        RETURNS:
            current in Ampere
        """
        # read the sensor output voltage
        sensorVoltage = self.adc.read_u16() * AREF / 65535
        #print("Sensor voltage: ", sensorVoltage, "V")
        #voltage to millivolt
        sensorVoltage = (sensorVoltage - self.default_output_voltage) * 1000
        # convert the voltage to current and apply error correction
        current = (sensorVoltage / self.scale_factor) + self.error
        if current < 0 and current > -self.hysteresis:
            current = 0
        elif current > 0 and current < self.hysteresis:
            current = 0
        else:
            pass

        return current