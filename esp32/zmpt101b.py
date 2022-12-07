import machine
import time
import os

class ZMPT101B:
    def __init__(self, pin):
        self.pin = machine.Pin(pin, machine.Pin.IN)
        self.adc = machine.ADC(self.pin)
        self.adc.atten(machine.ADC.ATTN_11DB)
        self.ac_voltage = 0
        self.no_load_voltage = 0
        self.load_voltage = 0

    def set_sensor_config(self, voltage):
        self.ac_voltage = float(voltage)

    def is_sensor_configured(self):
        for file in os.listdir():
            if file == 'sensor_configured.cfg':
                with open('sensor_configured.cfg', 'r') as file:
                    stored_value = file.read()
                    try: 
                        _, sensor_voltage, _ = stored_value.split(',')
                        if float(sensor_voltage) > 0:
                            self.ac_voltage = float(sensor_voltage)
                            print("[is_sensor_configured]Voltage sensor max voltage set to ", self.load_voltage)
                            return True
                    except ValueError:
                        print("[is_sensor_configured]Invalid sensor config stored in flash")
                        self.ac_voltage = 0
                        return False
                break #file found, no need to continue

        return False #file not found or config invalid

    def getVPP(self):
        """
        Capture the peak to peak voltage of the current ADC signal.
        Period of measurement is 50ms. The ADC is sampled every 500us. 100 samples are taken.
        AC current in spain is 50Hz.
        We should be able to capture at least 2 full cycles of the sinusoidal signal with its peaks.
        """
        min_value = 4095
        max_value = 0
        average_value = 0
        for i in range(100):
            adc_raw = self.adc.read()
            average_value += adc_raw
            if adc_raw < min_value:
                min_value = adc_raw
            elif adc_raw > max_value:
                max_value = adc_raw
            time.sleep_us(500)
        max_value_V = ((max_value * 3.3) / 4095)
        min_value_V = ((min_value * 3.3) / 4095)

        return max_value_V, min_value_V


    def calibration(self, relay, calibration_time=10, input_from_user=False):
        #first read voltage without load, so turn off relay
        print("[calibration]Calibrating voltage sensor...")
        print("[calibration]Turning off relay")
        relay.value(0)
        #during calibration_time, get average of max and min value from adc
        values = []
        start = time.ticks_ms()
        while time.ticks_ms() - start < (calibration_time/2) * 1000:
            max, min = self.getVPP()
            values.append((max - min) * 0.3536)
        end = time.ticks_ms()
        
        self.no_load_voltage = sum(values) / len(values)

        print("[calibration]No load voltage: " + str(self.no_load_voltage) + "V in " + str(end - start) + "ms")
        
        print("[calibration]Turning on relay")
        #now, read voltage with load and get input from user
        relay.value(1)
        values_load = []
        start = time.ticks_ms()
        while time.ticks_ms() - start < (calibration_time/2) * 1000:
            max, min = self.getVPP()
            values_load.append((max - min) * 0.3536)
        end = time.ticks_ms()
        
        self.load_voltage = sum(values_load) / len(values_load)
        print("[calibration]Load voltage: " + str(self.load_voltage) + "V in " + str(end - start) + "ms")
        if input_from_user:
            ac_voltage = input("AC voltage measured with multimeter: ")
            self.ac_voltage = float(ac_voltage)
            print("[calibration]AC voltage set to " + str(self.ac_voltage) + "V")
        else:
            print("[calibration]AC voltage received from app " + str(self.ac_voltage) + "V")
    
    def getVoltage(self):
        """
        Use linear equation to get voltage. x1, y1, x2, y2 are the points used to calculate the equation.
        """
        x1 = self.no_load_voltage
        y1 = 0
        x2 = self.load_voltage
        y2 = self.ac_voltage
        m = (y2 - y1) / (x2 - x1)
        b = y1 - m * x1

        values_load = []
        start = time.ticks_ms()
        while time.ticks_ms() - start < 1000:
            max, min = self.getVPP()
            values_load.append((max - min) * 0.3536)
        voltage = sum(values_load) / len(values_load)
        ac_voltage = m * voltage + b

        return ac_voltage


def main():
    voltage_sensor = ZMPT101B(33)
    voltage_sensor.calibration()

    while True:
        print("Voltage: " + str(voltage_sensor.getVoltage()) + "V")
        pass

if __name__ == "__main__":
    main()