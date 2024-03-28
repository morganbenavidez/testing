import time
import datetime
import csv
import os
import sys
import RPi.GPIO as GPIO
from PiPocketGeiger import RadiationWatch
import ms5837
from startUpBMP180 import *
from scd30_i2c import SCD30
import subprocess


class Bar02:

    def __init__(self,i2cbus=1):
        self.sensor = ms5837.MS5837_30BA(i2cbus)
        self.sensor.init()
       
    def read(self):
        self.sensor.read()
        _data = [self.sensor.pressure(ms5837.UNITS_psi), self.sensor.temperature(ms5837.UNITS_Centigrade), self.sensor.altitude()]
        return _data    


class Sensor:

    def __init__(self, pins):
        self.pins = pins
        for pin in self.pins:
            GPIO.setup(pin,GPIO.OUT)
       
    def read(self):
        return [GPIO.input(x) for x in self.pins]
   

def truncate(x):
    try:
        return round(x, 2)
    except:
        return x



def double_write(bar02, scd30, bmp, radiationWatch, date_var, time_var, ran_already, flag, ran_already_backup):

    # Set file_paths
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_path)
    csv_path = os.path.join(current_path, 'input_csv.csv')
    backup_csv_path = os.path.join(current_path, 'backup.csv')

    # Open backup csv and transmit csv
    with open(csv_path, 'a+', newline='') as SENSORS, open(backup_csv_path, 'a+', newline='') as backup_SENSORS:
        transmit_writer = csv.writer(SENSORS, delimiter=',') #all readings here bar02 was first
        backup_writer = csv.writer(backup_SENSORS, delimiter=',')

        # Backup File - Write once
        if not(ran_already_backup):

            backup_writer.writerow(['Date', 'Time', 'psi', 'temperature', 'altitude', 'CO2level', 'relativeHumidity', 'scdTemperature', 'bmp_temperature','bmp_pressure','bmp_altitude'])
            ran_already_backup = True

        # Transmit file - Will write more than once
        if not(ran_already):
            transmit_writer.writerow(['Date', 'Time', 'psi', 'temperature', 'altitude', 'CO2level', 'relativeHumidity', 'scdTemperature', 'bmp_temperature','bmp_pressure','bmp_altitude'])
            ran_already = True

        # Sensor 1
        try:
            scd30_data = scd30.read_measurement()
            C02level = scd30_data[0]
            scdTemperature = scd30_data[1]
            relativeHumidity = scd30_data[2]


        except:
            C02level, scdTemperature, relativeHumidity = 'null', 'null', 'null' #read -1 instead of null

        # Sensor 2
        try:
            bar_data = bar02.read()
            psi = bar_data[0]
            temperature = bar_data[1]
            altitude = bar_data[2]
        except:
            psi, temperature, altitude = 'null', 'null', 'null'


        # Sensor 3
        try:
            bmp_temperature = bmp.get_temp()
            bmp_pressure = bmp.get_pressure()
            bmp_altitude = bmp.get_altitude()
        except:
            bmp_temperature, bmp_pressure, bmp_altitude = 'null', 'null', 'null'

        # Sensor 4
        try:
            radiation_status = radiationWatch.status()
            duration = radiation_status.get('duration', 'null')
            uSvh = radiation_status.get('uSvh', 'null')
            uSvhError = radiation_status.get('uSvhError', 'null')
            cpm = radiation_status.get('cpm', 'null')
        except:
            duration, uSvh, uSvhError, cpm = 'null', 'null', 'null', 'null'


        total_values = [date_var, time_var, psi, temperature,
                        altitude, C02level, relativeHumidity,
                        scdTemperature, bmp_temperature, bmp_pressure, bmp_altitude,
                        duration, uSvh, uSvhError, cpm]


        # Truncate data
        total_values = [truncate(x) for x in total_values]
        print('total_values: ',total_values)

        # Backup and transmit data
        transmit_writer.writerow(total_values)
        backup_writer.writerow(total_values)

        # Continue reading sensors and writing to files
        if flag == 'continue':

            time.sleep(6)

            ran_already = True

        # Execute a transmission and delete main.csv
        elif flag == 'transmit':
            
            time.sleep(6)

            os.remove(csv_path)

            ran_already = False

        return ran_already, ran_already_backup




def read_all_sensors(bar02, scd30, bmp, radiationWatch, loop_counter, ran_already, ran_already_backup):

    # Get timestamp info and parse it
    timeStart = datetime.datetime.now()
    date_and_time = str(timeStart)
    dt_split = date_and_time.split(' ')
    date_var = dt_split[0]
    time_var = dt_split[1]

    # There will only be approximately 6 writes a minute
    # This is controlling whether or not to delete the transmit csv
    if (loop_counter % 10) == 0:
        flag = 'transmit'
    else:
        flag = 'continue'
    
    ran_already, ran_already_backup = double_write(bar02, scd30, bmp, radiationWatch, date_var, time_var, ran_already, flag, ran_already_backup)

    return ran_already, ran_already_backup




########################End function definitions######################
bar02 = Bar02()
scd30 = SCD30()
bmp = bmp180(0x77)
GPIO.setmode(GPIO.BCM)
ran_already_backup = False

# Initialize the RadiationWatch object


with RadiationWatch(24, 23) as radiationWatch:
    while True: 
        try:
            loop_counter = 0
            ran_already = False
            while True:
                loop_counter += 1
                psi, temperature, altitude = 'null', 'null', 'null'
                CO2level, scdTemperature, relativeHumidity = 'null', 'null', 'null'
                bmp_temperature, bmp_pressure, bmp_altitude = 'null', 'null', 'null'

                ran_already, ran_already_backup = read_all_sensors(bar02, scd30, bmp, radiationWatch, loop_counter, ran_already, ran_already_backup)

        except KeyboardInterrupt:
            print("Exiting the program.")
            GPIO.cleanup()  # Clean up GPIO pins if you've been using them
            sys.exit(0)
