import serial
import datetime
from xbee import xbee

import database

SERIALPORT = "COM3"    # the com/serial port the XBee is connected to
BAUDRATE = 19200      # the baud rate we talk to the xbee
CURRENTSENSE = 4       # which XBee ADC has current draw data
VOLTSENSE = 0          # which XBee ADC has mains voltage data
MAINSVPP = 170 * 2     # +-170V is what 120Vrms ends up being (= 120*2sqrt(2))
vrefcalibration = [492,  # Calibration for sensor #0
                   507,  # Calibration for sensor #1
                   489,  # Calibration for sensor #2
                   492,  # Calibration for sensor #3
                   501,  # Calibration for sensor #4
                   493]  # etc... approx ((2.4v * (10Ko/14.7Ko)) / 3
CURRENTNORM = 15.5  # conversion to amperes from ADC
NUMWATTDATASAMPLES = 1800 # how many samples to watch in the plot window, 1 hr @ 2s samples

def read_data(port):
    packet = xbee.find_packet(port)
    if not packet:
        raise RuntimeError
    xb = xbee(packet)

    voltage_samples = []
    amperage_samples = []
    for sample in xb.analog_samples[1:]:
        voltage_samples.append(sample[VOLTSENSE])
        amperage_samples.append(sample[CURRENTSENSE])

    # get max and min voltage and normalize the curve to '0'
    # to make the graph 'AC coupled' / signed
    min_v = min(voltage_samples)
    max_v = max(voltage_samples)

    # figure out the 'average' of the max and min readings
    avgv = (max_v + min_v) / 2.0
    # also calculate the peak to peak measurements
    vpp =  max_v-min_v

    for i in range(len(voltage_samples)):
        #remove 'dc bias', which we call the average read
        voltage_samples[i] -= avgv
        # We know that the mains voltage is 120Vrms = +-170Vpp
        voltage_samples[i] = (voltage_samples[i] * MAINSVPP) / vpp

    # normalize current readings to amperes
    for i in range(len(amperage_samples)):
        # VREF is the hardcoded 'DC bias' value, its
        # about 492 but would be nice if we could somehow
        # get this data once in a while maybe using xbeeAPI
        if vrefcalibration[xb.address_16]:
            amperage_samples[i] -= vrefcalibration[xb.address_16]
        else:
            amperage_samples[i] -= vrefcalibration[0]
            # the CURRENTNORM is our normalizing constant
            # that converts the ADC reading to Amperes
        amperage_samples[i] /= CURRENTNORM

    wattage_data = [v * a for v, a in zip(voltage_samples, amperage_samples)]

    amperage = sum(map(abs, amperage_samples)) / float(len(amperage_samples))
    wattage = sum(map(abs, wattage_data)) / float(len(wattage_data))

    return datetime.datetime.now(), amperage, wattage

if __name__ == "__main__":
    database.metadata.create_all()
    port = serial.Serial(SERIALPORT, BAUDRATE)
    while True:
        timestamp, amperage, wattage = read_data(port)
        print type(timestamp)
        ins = database.readings.insert().values(
            timestamp = timestamp,
            amperage = amperage,
            wattage = wattage
        )
        conn = database.engine.connect()
        conn.execute(ins)
