import serial
import time
PMS_CMD_CHANGE_MODE_PASSIVE = b'\x42\x4d\xe1\x00\x00\x01\x70'
PMS_CMD_CHANGE_MODE_ACTIVE = b'\x42\x4d\xe1\x00\x01\x01\x71'
PMS_CMD_TO_SLEEP = b'\x42\x4d\xe4\x00\x00\x01\x73'
PMS_CMD_TO_WAKEUP = b'\x42\x4d\xe4\x00\x01\x01\x74'
PMS_CMD_READ_IN_PASSIVE = b'\x42\x4d\xe2\x00\x00\x01\x71'

class PMS7003:
    def __init__(self,passiveMode=False,portPath='/dev/serial0',factoryPMvalues=True,atmosphericPMvalues=True,particleCount=True):
        self.serialPort = serial.Serial(
            port=portPath,
            baudrate = 9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=2
        )
        self.factoryPMvalues = factoryPMvalues
        self.atmosphericPMvalues = atmosphericPMvalues
        self.particleCount = particleCount
        self.passiveMode = passiveMode
        self.lastRead = None
        if passiveMode: 
            self.serialPort.write(PMS_CMD_CHANGE_MODE_PASSIVE)
            self.serialPort.flush()
            time.sleep(0.2)
        else: 
            self.serialPort.write(PMS_CMD_CHANGE_MODE_ACTIVE)
            self.serialPort.flush()
            time.sleep(0.2)
            self.set_to_wakeup()


    def readValues(self):
        readCount = 0
        if self.passiveMode:
            self.set_to_wakeup()
            time.sleep(30)
            self.serialPort.write(PMS_CMD_READ_IN_PASSIVE)
            self.serialPort.flush()
            time.sleep(2)
        self.serialPort.reset_input_buffer()
        while True:
            if self.serialPort.in_waiting >= 32:
                # Check that we are reading the payload from the correct place (i.e. the start bits)
                if ord(self.serialPort.read()) == 0x42 and ord(self.serialPort.read()) == 0x4d:
                    sensorValues = {'err': False}
                    # Read the remaining payload data
                    data = self.serialPort.read(30)
                    # Extract the byte data by summing the bit shifted high byte with the low byte
                    # Use ordinals in python to get the byte value rather than the char value
                    frameLength = ord(data[1]) + (ord(data[0])<<8)

                    # Standard particulate values in ug/m3
                    if self.factoryPMvalues:
                        sensorValues['concPM1_0_CF1'] = ord(data[3]) + (ord(data[2])<<8)
                        sensorValues['concPM2_5_CF1'] = ord(data[5]) + (ord(data[4])<<8)
                        sensorValues['concPM10_0_CF1'] = ord(data[7]) + (ord(data[6])<<8)

                    # Atmospheric particulate values in ug/m3
                    if self.atmosphericPMvalues:
                        sensorValues['concPM1_0_ATM'] = ord(data[9]) + (ord(data[8])<<8)
                        sensorValues['concPM2_5_ATM'] = ord(data[11]) + (ord(data[10])<<8)
                        sensorValues['concPM10_0_ATM'] = ord(data[13]) + (ord(data[12])<<8)
                    # Raw counts per 0.1l
                    if self.particleCount:
                        sensorValues['rawGt0_3um'] = ord(data[15]) + (ord(data[14])<<8)
                        sensorValues['rawGt0_5um'] = ord(data[17]) + (ord(data[16])<<8)
                        sensorValues['rawGt1_0um'] = ord(data[19]) + (ord(data[18])<<8)
                        sensorValues['rawGt2_5um'] = ord(data[21]) + (ord(data[20])<<8)
                        sensorValues['rawGt5_0um'] = ord(data[23]) + (ord(data[22])<<8)
                        sensorValues['rawGt10_0um'] = ord(data[25]) + (ord(data[24])<<8)
                    # Misc data
                    version = ord(data[26])
                    errorCode = ord(data[27])
                    payloadChecksum = ord(data[29]) + (ord(data[28])<<8)

                    # Calculate the payload checksum (not including the payload checksum bytes)
                    inputChecksum = 0x42 + 0x4d
                    for x in range(0,28):
                        inputChecksum = inputChecksum + ord(data[x])


                    #os.system('clear') # Set to 'cls' on Windows
                    # print("PMS7003 Sensor Data:")
                    # print("PM1.0 = " + str(concPM1_0_CF1) + " ug/m3")
                    # print("PM2.5 = " + str(concPM2_5_CF1) + " ug/m3")
                    # print("PM10 = " + str(concPM10_0_CF1) + " ug/m3")
                    # print("PM1 Atmospheric concentration = " + str(concPM1_0_ATM) + " ug/m3")
                    # print("PM2.5 Atmospheric concentration = " + str(concPM2_5_ATM) + " ug/m3")
                    # print("PM10 Atmospheric concentration = " + str(concPM10_0_ATM) + " ug/m3")
                    # print("Count: 0.3um = " + str(rawGt0_3um) + " per 0.1l")
                    # print("Count: 0.5um = " + str(rawGt0_5um) + " per 0.1l")
                    # print("Count: 1.0um = " + str(rawGt1_0um) + " per 0.1l")
                    # print("Count: 2.5um = " + str(rawGt2_5um) + " per 0.1l")
                    # print("Count: 5.0um = " + str(rawGt5_0um) + " per 0.1l")
                    # print("Count: 10um = " + str(rawGt10_0um) + " per 0.1l")
                    # print("Version = " + str(version))
                    # print("Error Code = " + str(errorCode))
                    # print("Frame length = " + str(frameLength))
                    if inputChecksum != payloadChecksum:
                        sensorValues['err'] = True
                        sensorValues['errMessage'] = "Checksum not match !"
                    if errorCode != 0:
                        sensorValues['err'] = True
                        sensorValues['errMessage'] = "Error code : "+ str(errorCode)
                        if readCount < 10: continue
                    if self.passiveMode: self.set_to_sleep()
                    self.lastValues = sensorValues
                    self.lastRead = time.time()
                    return sensorValues
                elif readCount > 10: return {'err': True, 'errMessage': "Cannot read dust sensor !"}
            elif readCount > 10: return {'err': True, 'errMessage': "Cannot read dust sensor !"}
            readCount+=1
            if self.passiveMode: time.sleep(3)
            time.sleep(0.7)

    def set_to_sleep(self, to_sleep=True):
        """
            This makes the sensor fan to stop.
            From datasheet "Stable data should be got at least 30 seconds after the sensor wakeup
            from the sleep mode because of the fan's performance."
        """

        if to_sleep:
            self.serialPort.write(PMS_CMD_TO_SLEEP)
        else:
            self.serialPort.write(PMS_CMD_TO_WAKEUP)

        self.serialPort.flush()  # Make sure tx buffer is completely sent
        # Number not specified in datasheet but sensor does not receive command for 2s.
        time.sleep(3)  

    def set_to_wakeup(self):
        """
            Starts the sensors fan
        """
        self.set_to_sleep(False)