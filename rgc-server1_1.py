import socket
import sys
import hashlib
from datetime import datetime
import os
import signal
import glob
import sqlite3
import threading
import time
import RPi.GPIO as GPIO

HOST = ''   
PORT = 8888 
PASSWORD = ''
ENC_KEY = ''
exitapp = False
break_ = -1
db_path = 'rgc-server.db3'
CODE_VERSION = 2

def stringToint(string):
    try:
        ints = int(string)
    except ValueError:
        print "Error while converting String to Int"
    return ints

def planowanie():
    if exitapp == False:
        rtime = 1
        threading.Timer(rtime, planowanie).start()
        conndb2 = sqlite3.connect(db_path, check_same_thread=False)
        conndb2.isolation_level = None
        cursor2 = conndb2.execute("SELECT * from  planowanie p join stany s on p.Out_id = s.Id")
        for row in cursor2:
            if row[1] == 'date':
                if row[4] == datetime.utcnow().strftime('%Y-%m-%d %H:%M'):
                    if row[10] != row[6]:
                        set=row[6]
                        if row[6] == 2:
                            set=int(not row[10])
                        GPIOset(row[9],set)
                        gpiolist = row[9].split(",")
                        for gpio in gpiolist:
                            conndb2.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=? and IN_OUT like 'out') or (GPIO_BCM like ? and Id!=? and IN_OUT like 'out');",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),"%"+gpio+",%",row[5],"%,"+gpio+"%",row[5]))
                            conndb2.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? and IN_OUT like 'out' ;",(set,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),gpio,row[5]))
                        conndb2.execute("UPDATE stany set Stan =?, Edit_time=? where Id=?",(set,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),row[5]))
                        conndb2.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("scheduled",row[5],"ON" if ((set and not row[14]) or (not set and row[14])) else "OFF"))
                    conndb2.execute("DELETE from planowanie where Id=?", (row[0],))
                    conndb2.execute("UPDATE planowanie set Edit_time=? where Id in (SELECT Id FROM planowanie LIMIT 1)",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
                    conndb2.commit()
            elif row[1] == 'hour':
                if row[4] == datetime.utcnow().strftime('%H:%M'):
                    if row[10] != row[6]:
                        set=row[6]
                        if row[6] == 2:
                            set=int(not row[10])
                        GPIOset(row[9],set)
                        gpiolist = row[9].split(",")
                        for gpio in gpiolist:
                            conndb2.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=? and IN_OUT like 'out') or (GPIO_BCM like ? and Id!=? and IN_OUT like 'out');",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),"%"+gpio+",%",row[5],"%,"+gpio+"%",row[5]))
                            conndb2.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? and IN_OUT like 'out' ;",(set,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),gpio,row[5]))
                        conndb2.execute("UPDATE stany set Stan =?, Edit_time=? where Id=?",(set,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),row[5]))
                        conndb2.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("scheduled",row[5],"ON" if ((set and not row[14]) or (not set and row[14])) else "OFF"))
                    if row[3] == 'once':
                        conndb2.execute("DELETE from planowanie where Id=?", (row[0],))
                        conndb2.execute("UPDATE planowanie set Edit_time=? where Id in (SELECT Id FROM planowanie LIMIT 1)",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
                    conndb2.commit()
            elif row[1] == 'timer':
                timelist = row[4].split(",")
                time = int(timelist[1]) - rtime
                if time <= 0:
                    if row[10] != row[6]:
                        set=row[6]
                        if row[6] == 2:
                            set=int(not row[10])
                        GPIOset(row[9],set)
                        gpiolist = row[9].split(",")
                        for gpio in gpiolist:
                            conndb2.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=? and IN_OUT like 'out') or (GPIO_BCM like ? and Id!=? and IN_OUT like 'out');",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),"%"+gpio+",%",row[5],"%,"+gpio+"%",row[5]))
                            conndb2.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? and IN_OUT like 'out' ;",(set,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),gpio,row[5]))
                        conndb2.execute("UPDATE stany set Stan =?, Edit_time=? where Id=?",(set,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),row[5]))
                        conndb2.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("scheduled",row[5],"ON" if ((set and not row[14]) or (not set and row[14])) else "OFF"))
                    if row[3] == 'once':
                        conndb2.execute("DELETE from planowanie where Id=?", (row[0],))
                        conndb2.execute("UPDATE planowanie set Edit_time=? where Id in (SELECT Id FROM planowanie LIMIT 1)",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
                    else:
                        conndb2.execute("UPDATE planowanie set Dane=?, Edit_time=? where Id=?",(timelist[0]+','+timelist[0],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),row[0]))
                else:
                    conndb2.execute("UPDATE planowanie set Dane=?, Edit_time=? where Id=?",(str(timelist[0])+','+str(time),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),row[0]))
                conndb2.commit()
        conndb2.close()

def GPIOset(pinout,onoff):
    pins = pinout.split(",")
    onoff = stringToint(onoff)
    if onoff < 2:
        for pin in pins:
            pin = stringToint(pin)
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, onoff)

	
def GPIOstate(pin):
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(stringToint(pin), GPIO.OUT)
    return GPIO.input(stringToint(pin))

def GPIOset_in(inpin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(inpin,GPIO.IN,GPIO.PUD_UP)
    
def GPIOPWM(inpin,fr):
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(inpin, GPIO.OUT)
    p = GPIO.PWM(inpin, fr)
    return p

pwm = {k: [] for k in range(2)}

def inputLoop2(outid,inid,inpin,Stan,reverse):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    inpin = int(inpin)
    id2 = int(inid)
    Stan = int(Stan)
    GPIO.setup(inpin,GPIO.IN,GPIO.PUD_UP)
    if Stan == 1:
        stan = 6
    else:
        stan = 1
    while exitapp == False:
        if stan ==1:
            if GPIO.input(inpin)==0:
                stan=2
            cursor1 = conndb.execute("SELECT Stan, Reverse from stany where Id=?", (outid,))
            for row in cursor1:
                if int(row[0])==1:
                    stan=3
        elif stan ==2:
            cursor2 = conndb.execute("SELECT GPIO_BCM, Reverse from stany where Id=?", (outid,))
            for row in cursor2:
                GPIOset(str(row[0]),1)
                gpiolist = row[0].split(",")
            for gpio in gpiolist:
                conndb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=?) or (GPIO_BCM like ? and Id!=?);",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),"%"+gpio+",%",str(outid),"%,"+gpio+"%",str(outid)))
                conndb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? ;",(str(1),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),gpio,str(outid)))
            conndb.execute("UPDATE stany set Stan =?,Edit_time=? where Id=?",(str(1),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(outid)))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",outid,"ON" if (not reverse) else "OFF"))
            conndb.execute("UPDATE stany set Stan =1,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(inpin)))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",inid,"ON" if (not reverse) else "OFF"))
            conndb.commit()
            stan = 5
            if GPIO.input(inpin)==1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",inid,"ON" if reverse else "OFF"))
                conndb.commit()
                stan=3
        elif stan ==3:
            if GPIO.input(inpin)==0:
                stan=4
            cursor1 = conndb.execute("SELECT Stan, Reverse from stany where Id=?", (outid,))
            for row in cursor1:
                if int(row[0])==0:
                    stan=1
        elif stan ==4:
            cursor2 = conndb.execute("SELECT GPIO_BCM, Reverse from stany where Id=?", (outid,))
            for row in cursor2:
                GPIOset(str(row[0]),0)
                gpiolist = row[0].split(",")
            for gpio in gpiolist:
                conndb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=?) or (GPIO_BCM like ? and Id!=?);",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),"%"+gpio+",%",str(outid),"%,"+gpio+"%",str(outid)))
                conndb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? ;",(str(0),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),gpio,str(outid)))
            conndb.execute("UPDATE stany set Stan =?,Edit_time=? where Id=?",(str(0),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(outid)))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",outid,"ON" if reverse else "OFF"))
            conndb.execute("UPDATE stany set Stan =1,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(inpin)))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",inid,"ON" if (not reverse) else "OFF"))
            conndb.commit()
            stan = 6
            if GPIO.input(inpin)==1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",inid,"ON" if reverse else "OFF"))
                conndb.commit()
                stan=1
        elif stan ==5:
            if GPIO.input(inpin)==1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",inid,"ON" if reverse else "OFF"))
                conndb.commit()
                stan=3
        elif stan ==6:
            if GPIO.input(inpin)==1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",inid,"ON" if reverse else "OFF"))
                conndb.commit()
                stan=1

        time.sleep(0.05)
        if break_ == id2:
            break

def inputLoop3(id,inpin,Stan,reverse,outid):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    inpin = int(inpin)
    id2 = int(id)
    Stan = int(Stan)
    GPIO.setup(inpin,GPIO.IN,GPIO.PUD_UP)
    Oreverse = 0

    if Stan == 0:
        stan = 2
    elif Stan == 1:
        stan = 4
    else:
        stan = 2
    while exitapp == False:
        if stan ==2: 
            if GPIO.input(inpin)==0:
                cursor2 = conndb.execute("SELECT GPIO_BCM, Reverse from stany where Id=?", (outid,))
                for row in cursor2:
                    Oreverse=int(row[1])
                    GPIOset(str(row[0]),1 if not Oreverse else 0)
                    gpiolist = row[0].split(",")
                for gpio in gpiolist:
                    conndb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=?) or (GPIO_BCM like ? and Id!=?);",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),"%"+gpio+",%",str(outid),"%,"+gpio+"%",str(outid)))
                    conndb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? ;",(str(1 if not Oreverse else 0),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),gpio,str(outid)))
                conndb.execute("UPDATE stany set Stan =?,Edit_time=? where Id=?",(str(1 if not Oreverse else 0),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(outid)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",outid,"ON" if (not reverse) else "OFF"))
                conndb.execute("UPDATE stany set Stan =1,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",id,"ON" if (not reverse) else "OFF"))
                conndb.commit()
                stan=4
        if stan ==4: 
            if GPIO.input(inpin)==1:
                cursor2 = conndb.execute("SELECT GPIO_BCM, Reverse from stany where Id=?", (outid,))
                for row in cursor2:
                    Oreverse=int(row[1])
                    GPIOset(str(row[0]),0 if not Oreverse else 1)
                    gpiolist = row[0].split(",")
                for gpio in gpiolist:
                    conndb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=?) or (GPIO_BCM like ? and Id!=?);",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),"%"+gpio+",%",str(outid),"%,"+gpio+"%",str(outid)))
                    conndb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? ;",(str(0 if not Oreverse else 1),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),gpio,str(outid)))
                conndb.execute("UPDATE stany set Stan =?,Edit_time=? where Id=?",(str(0 if not Oreverse else 1),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(outid)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",outid,"ON" if reverse else "OFF"))
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",id,"ON" if reverse else "OFF"))
                conndb.commit()
                stan=2
        time.sleep(0.05)
        if break_ == id2:
            break

def inputLoop4(id,inpin,Stan,reverse):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    inpin = int(inpin)
    id2 = int(id)
    Stan = int(Stan)
    GPIO.setup(inpin,GPIO.IN,GPIO.PUD_UP)


    if Stan == 0:
        stan = 2
    elif Stan == 1:
        stan = 4
    else:
        stan = 2
    while exitapp == False:
        if stan ==2: 
            if GPIO.input(inpin)==0:
                conndb.execute("UPDATE stany set Stan =1,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",id,"ON" if (not reverse) else "OFF"))
                conndb.commit()
                stan=4
        if stan ==4: 
            if GPIO.input(inpin)==1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",("input",id,"ON" if reverse else "OFF"))
                conndb.commit()
                stan=2
        time.sleep(0.05)
        if break_ == id2:
            break

if __name__ == '__main__':
    print 'Server is starting...'
    print 'Please press Ctrl+C to end the program...'
    conndb = sqlite3.connect(db_path, check_same_thread=False)
    conndb.isolation_level = None
    tableexist = conndb.execute("SELECT * FROM sqlite_master WHERE name ='stany' and type='table';")
    if len(tableexist.fetchall()) == 0:
        print "Creating database..."
        
    conndb.executescript('''CREATE TABLE IF NOT EXISTS `stany` (
        `Id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        `GPIO_BCM`    TEXT NOT NULL,
        `Stan`    INTEGER NOT NULL,
        `Name`    TEXT,
        `IN_OUT`    TEXT,
        `Edit_time`    TEXT,
        `Reverse`    INTEGER NOT NULL,
        `Bindid`    INTEGER,
        `Bindtype`    INTEGER);
        CREATE TABLE IF NOT EXISTS `planowanie` (
        `Id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        `Warunek`    TEXT NOT NULL,
        `Podwarunek`    TEXT,
        `Rodzaj`    TEXT NOT NULL,
        `Dane`    TEXT,
        `Out_id`	INTEGER NOT NULL,
        `Stan`	INTEGER NOT NULL,
        `Edit_time`	TEXT );
        CREATE TABLE IF NOT EXISTS `pwm` (
        `Id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        `GPIO_BCM`	TEXT NOT NULL,
        `FR`	NUMERIC NOT NULL,
        `DC`	INTEGER NOT NULL,
        `SS`	INTEGER NOT NULL,
        `Name`	TEXT NOT NULL,
        `Reverse`	INTEGER NOT NULL,
        `Edit_time`    TEXT);
        CREATE TABLE IF NOT EXISTS `historia` (
        `Id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        `Czas`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        `Typ`    TEXT,
        `Id_IO`    INTEGER,
        `Id_Pwm`    INTEGER,
        `Stan`    TEXT NOT NULL);''')
        
    print datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    try :
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print 'Socket created'
    except socket.error, msg :
        print 'Failed to create socket. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()
        
    i = 0
    for arg in sys.argv:
        if arg == '-port':
            try:
                PORT = int(sys.argv[i+1])
            except ValueError:
                print "Wrong port argument"
        elif arg == '-address':
            HOST = sys.argv[i+1]
        elif arg == '-password':
            PASSWORD = hashlib.sha256(sys.argv[i+1].encode()).hexdigest()
            ENC_KEY = hashlib.md5(sys.argv[i+1].encode()).hexdigest()
            print ENC_KEY
            import base64
            from Crypto import Random
            from Crypto.Cipher import AES
            def encrypt(key, message):
                try:
                    bs = 16
                    message = message + (bs - len(message) % bs) * chr(bs - len(message) % bs)
                    iv = Random.new().read(AES.block_size)
                    cipher = AES.new(key, AES.MODE_CBC, iv)
                    s = base64.b64encode(iv + cipher.encrypt(message)).decode('utf-8')
                except:
                    s = "error"
                return s
            def decrypt(key, enc_message):
                try:
                    enc_message = base64.b64decode(enc_message)
                    iv = enc_message[:AES.block_size]
                    cipher = AES.new(key, AES.MODE_CBC, iv)
                    s = cipher.decrypt(enc_message[AES.block_size:])
                    s = s[:-ord(s[len(s)-1:])].decode('utf-8')
                except:
                    s = "error"
                return s
        i = i+1

    try:
        s.bind((HOST, PORT))
    except socket.error , msg:
        print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()

    print 'Socket bind complete ' + str(s.getsockname()) + PASSWORD

    cursor1 = conndb.execute("SELECT * from stany where IN_OUT like 'out' order by Edit_time ASC")
    for row in cursor1:
        print 'OUTPUT: GPIO='+str(row[1])+' STATE='+str(row[2])
        GPIOset(row[1],row[2]) if not row[8] else GPIOset(row[1],0 if not row[6] else 1)
            
    cursor1 = conndb.execute("SELECT * from pwm")
    for row in cursor1:
        print 'OUTPUT PWM: GPIO='+str(row[1])+' S/S='+str(row[4])+' FR='+str(row[2])+' DC='+str(row[3])
        pwmpins = row[1].split(",")
        for pin in pwmpins:
            pwm[pin] = GPIOPWM(int(pin),float(row[2]))
            if row[4] == 1:
                pwm[pin].start(int(row[3]))

    
    try:    
        pid = planowanie()
        cursor1 = conndb.execute("SELECT * from stany where IN_OUT like 'in'")
        for row in cursor1:
            print 'INPUT: GPIO='+str(row[1])+' STATE='+str(row[2])
            if row[8] == 1:
                threading.Thread(target=inputLoop2, args=(row[7],row[0],row[1],row[2],row[6])).start()
            elif row[8] == 2:
                threading.Thread(target=inputLoop3, args=(row[0],row[1],row[2],row[6],row[7])).start()
            else:
                threading.Thread(target=inputLoop4, args=(row[0],row[1],row[2],row[6])).start()
        while 1:
            d = s.recvfrom(1024)
            data = d[0].strip()
            addr = d[1]
            datalist = data.split(";")
            passwalidation = False
            if PASSWORD == '':
                passwalidation = True
            else:
                if datalist[0] == PASSWORD:
                    temp = decrypt(ENC_KEY,datalist[1])
                    if temp == 'error':
                        passwalidation = False
                        print 'Decrytion error'
                    else:
                        datalist = ("0;"+temp).split(";")
                        passwalidation = True
                else:
                    passwalidation = False
                    
            if passwalidation == True:
                if datalist[1] == 'version_check':
                    reply = 'true;version_check;'+str(CODE_VERSION)+';'
                elif datalist[1] == 'GPIO_OEtime':
                    cursor8 = conndb.execute("SELECT Max(Edit_time) FROM stany where IN_OUT like 'out'")
                    for row in cursor8:
                        reply = 'true;GPIO_OEtime;'+str(row[0])+';'
                elif datalist[1] == 'GPIO_Olist':
                    cursor9 = conndb.execute("SELECT * from stany where IN_OUT like 'out'")
                    reply = 'true;GPIO_Olist;'
                    for row in cursor9:
                        reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[6])+';'+str(row[8])+';'
                elif datalist[1] == 'Add_GPIO_out':
                    idio = conndb.execute("INSERT INTO stany VALUES (null,?,2,?,'out',?,?,null,?)",(datalist[2],datalist[3],datalist[4],datalist[5],datalist[6])).lastrowid
                    conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",(datalist[7],str(idio),"ADDED"))
                    conndb.commit()
                    reply= 'true;Add_GPIO_out;'
                elif datalist[1] == 'Edit_GPIO_out':
                    conndb.execute("UPDATE stany set Stan=2, GPIO_BCM=?,Name=?, Edit_time=?, reverse=?, Bindtype=? where Id=?",(datalist[3],datalist[4],datalist[5],datalist[6],datalist[8],datalist[2]))
                    conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",(datalist[9],datalist[2],"EDITED"))
                    conndb.commit()
                    pwmpins = datalist[3].split(',')
                    pwmpins2 = datalist[7].split(',')
                    for pin2 in pwmpins2:
                        if pin2 not in pwmpins:
                            GPIO.cleanup(int(pin2))
                    reply= 'true;Edit_GPIO_out;'
                elif datalist[1] == 'Delete_GPIO_out':
                    break_ = int(datalist[2])
                    conndb.execute("DELETE from stany where Id=?",(datalist[2],))
                    conndb.execute("UPDATE stany set Edit_time=? where Id in (SELECT Id FROM stany LIMIT 1)",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
                    conndb.execute("DELETE from historia where Id_IO=?",(datalist[2],))
                    conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",(datalist[5],datalist[2],datalist[4]+" DELETED"))
                    r1 = conndb.execute("DELETE from planowanie where Out_id=?",(datalist[2],)).rowcount
                    if r1 > 0:
                        conndb.execute("UPDATE planowanie set Edit_time=? where Id in (SELECT Id FROM planowanie LIMIT 1)",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
                    conndb.commit()
                    pwmpins = datalist[3].split(",")
                    for pin in pwmpins:
                        GPIO.cleanup(int(pin))
                    reply= 'true;Delete_GPIO_out;'
                elif datalist[1] == 'GPIO_IEtime':
                    cursor8 = conndb.execute("SELECT Max(Edit_time) FROM stany where IN_OUT like 'in'")
                    for row in cursor8:
                        reply = 'true;GPIO_IEtime;'+str(row[0])+';'
                elif datalist[1] == 'GPIO_Ilist':
                    cursor13 = conndb.execute("SELECT * from stany where IN_OUT like 'in'")
                    reply = 'true;GPIO_Ilist;'
                    for row in cursor13:
                        reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[6])+';'+str(row[7])+';'+str(row[8])+';'
                elif datalist[1] == 'Add_GPIO_in':
                    id = conndb.execute("INSERT INTO stany VALUES (null,?,0,?,'in',?,?,?,?)",(datalist[2],datalist[3],datalist[4],datalist[5],datalist[6],datalist[7])).lastrowid
                    conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",(datalist[8],str(id),"ADDED"))
                    conndb.commit()
                    if datalist[7] == '1':
                        threading.Thread(target=inputLoop2, args=(datalist[6],id,datalist[2],'0',datalist[5])).start()
                    elif datalist[7] == '2':
                        threading.Thread(target=inputLoop3, args=(id,datalist[2],'0',datalist[5],datalist[6])).start()
                    else:
                        threading.Thread(target=inputLoop4, args=(id,datalist[2],'0',datalist[5])).start()
                    reply= 'true;Add_GPIO_in;'
                elif datalist[1] == 'Edit_GPIO_in':
                    break_ = int(datalist[2])
                    conndb.execute("DELETE from stany where Id=?",(datalist[2],))
                    conndb.execute("DELETE from historia where Id_IO=?",(datalist[2],))
                    id = conndb.execute("INSERT INTO stany VALUES (null,?,0,?,'in',?,?,?,?)",(datalist[3],datalist[4],datalist[5],datalist[6],datalist[7],datalist[8])).lastrowid
                    conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",(datalist[10],str(id),"EDITED"))
                    conndb.commit()
                    if datalist[3] != datalist[9]:
                        GPIO.cleanup(int(datalist[9]))
                    if datalist[8] == '1':
                        threading.Thread(target=inputLoop2, args=(datalist[7],id,datalist[3],'0',datalist[6])).start()
                    elif datalist[8] == '2':
                        threading.Thread(target=inputLoop3, args=(id,datalist[3],'0',datalist[6],datalist[7])).start()
                    else:
                        threading.Thread(target=inputLoop4, args=(id,datalist[3],'0',datalist[6])).start()
                    reply= 'true;Edit_GPIO_in;'
                elif datalist[1] == 'GPIO_Oname':
                    cursor12 = conndb.execute("SELECT Id,Name,GPIO_BCM,Reverse from stany where IN_OUT like 'out'")
                    reply = 'true;GPIO_Oname;'
                    for row in cursor12:
                        reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'
                elif datalist[1] == 'GPIO_PEtime':
                    cursor13 = conndb.execute("SELECT Max(Edit_time) FROM pwm")
                    for row in cursor13:
                        reply = 'true;GPIO_PEtime;'+str(row[0])+';'
                elif datalist[1] == 'GPIO_Plist':
                    cursor14 = conndb.execute("SELECT * from pwm")
                    reply = 'true;GPIO_Plist;'
                    for row in cursor14:
                        reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[4])+';'+str(row[5])+';'+str(row[6])+';'
                elif datalist[1] == 'GPIO_PDC':
                    pwmpins = datalist[3].split(",")
                    for pin in pwmpins:
                        pwm[pin].ChangeDutyCycle(int(datalist[4]))
                    reply = 'true;GPIO_PDC;'+datalist[4]+';'
                elif datalist[1] == 'GPIO_PDCu':
                    conndb.execute("UPDATE pwm set DC=?,Edit_time=? where Id=?",(datalist[4],datalist[5],datalist[2])) 
                    conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)",(datalist[6],datalist[2],"DC="+datalist[4]+"%"))
                    conndb.commit()
                    reply = 'true;GPIO_PDCu;'+datalist[4]+';'+datalist[5]+';'
                elif datalist[1] == 'GPIO_PFRDC':
                    pwmpins = datalist[3].split(",")
                    for pin in pwmpins:
                        pwm[pin].ChangeDutyCycle(int(datalist[5]))
                        pwm[pin].ChangeFrequency(float(datalist[4]))
                    conndb.execute("UPDATE pwm set FR=?,DC=?,Edit_time=? where Id=?",(datalist[4],datalist[5],datalist[6],datalist[2])) 
                    conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)",(datalist[7],datalist[2],"DC="+datalist[5]+"%,FR="+datalist[4]+"Hz"))
                    conndb.commit()
                    reply = 'true;GPIO_PFRDC;'+datalist[4]+';'+datalist[6]+';'+datalist[5]+';'
                elif datalist[1] == 'GPIO_PSS':
                    pwmpins = datalist[3].split(",")
                    for pin in pwmpins:
                        if datalist[6] == '1': 
                            pwm[pin].start(int(datalist[4]))
                            pwm[pin].ChangeFrequency(float(datalist[7]))
                            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)",(datalist[8],datalist[2],"ON:DC="+datalist[4]+"%,FR="+datalist[7]+"Hz"))
                        elif datalist[6] == '0':
                            pwm[pin].stop()
                            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)",(datalist[8],datalist[2],"OFF"))
                    conndb.execute("UPDATE pwm set DC=?,Edit_time=?,SS=? where Id=?",(datalist[4],datalist[5],datalist[6],datalist[2]))
                    conndb.commit()
                    reply = 'true;GPIO_PSS;'+datalist[4]+';'+datalist[5]+';'+datalist[6]+';'
                elif datalist[1] == 'Add_GPIO_pwm':
                    pwmpins = datalist[2].split(',')
                    for pin in pwmpins:
                        pwm[pin] = GPIOPWM(int(pin),float(datalist[3]))
                        pwm[pin].start(int(datalist[4]))
                    idpwm = conndb.execute("INSERT INTO pwm VALUES (null,?,?,?,1,?,?,?)",(datalist[2],datalist[3],datalist[4],datalist[5],datalist[6],datalist[7])).lastrowid
                    conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)",(datalist[8],str(idpwm),"ADDED:DC="+datalist[4]+"%,FR="+datalist[3]+"Hz"))
                    conndb.commit()
                    reply= 'true;Add_GPIO_pwm;'
                elif datalist[1] == 'Delete_GPIO_pwm':
                    break_ = int(datalist[2])
                    conndb.execute("DELETE from pwm where Id=?",(datalist[2],))
                    conndb.execute("DELETE from historia where Id_Pwm=?",(datalist[2],))
                    conndb.execute("UPDATE pwm set Edit_time=? where Id in (SELECT Id FROM pwm LIMIT 1)",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
                    conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)",(datalist[5],datalist[2],datalist[4]+" DELETED"))
                    conndb.commit()
                    pwmpins = datalist[3].split(',')
                    for pin in pwmpins:
                        pwm[pin].stop()
                        pwm.pop(pin)
                        GPIO.cleanup(int(pin))
                    reply= 'true;Delete_GPIO_pwm;'
                elif datalist[1] == 'Edit_GPIO_pwm':
                    pwmpins = datalist[3].split(',')
                    pwmpins2 = datalist[4].split(',')
                    for pin in pwmpins:
                        if pin not in pwmpins2:
                            pwm[pin].stop()
                            pwm.pop(pin)
                            GPIO.cleanup(int(pin))
                    for pin2 in pwmpins2:
                        if pin2 not in pwmpins:
                            pwm[pin2] = GPIOPWM(int(pin2),float(datalist[5]))
                            pwm[pin2].start(int(datalist[6]))
                        else:
                            pwm[pin2].ChangeDutyCycle(int(datalist[6]))
                            pwm[pin2].ChangeFrequency(float(datalist[5]))
                    conndb.execute("UPDATE pwm set GPIO_BCM=?, FR=?, DC=?, SS=1, Name=?, Reverse=?, Edit_time=? where Id=?",(datalist[4],datalist[5],datalist[6],datalist[7],datalist[8],datalist[9],datalist[2])) 
                    conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)",(datalist[10],datalist[2],"EDITED:DC="+datalist[6]+"%,FR="+datalist[5]+"Hz"))
                    conndb.commit()
                    reply= 'true;Edit_GPIO_pwm;'
                elif datalist[1] == 'Allpins_GPIO_pwm':
                    reply = 'true;Allpins_GPIO_pwm;'
                    cursor15 = conndb.execute("SELECT GPIO_BCM from pwm")
                    for row in cursor15:
                        pins = row[0].split(',')
                        for pin in pins:
                            reply+= pin+';'
                elif datalist[1] == 'Allpins_GPIO_out':
                    reply = 'true;Allpins_GPIO_out;'
                    cursor16 = conndb.execute("SELECT GPIO_BCM from stany where IN_OUT like 'out'")
                    for row in cursor16:
                        pins = row[0].split(',')
                        for pin in pins:
                            reply+= pin+';'
                elif datalist[1] == 'Allpins_GPIO_in':
                    reply = 'true;Allpins_GPIO_in;'
                    cursor17 = conndb.execute("SELECT GPIO_BCM from stany where IN_OUT like 'in'")
                    for row in cursor17:
                        reply+= str(row[0])+';'
                elif datalist[1] == 'GPIO_SAEtime':
                    cursor18 = conndb.execute("SELECT Max(Edit_time) FROM planowanie")
                    for row in cursor18:
                        reply = 'true;GPIO_SAEtime;'+str(row[0])+';'
                elif datalist[1] == 'GPIO_SAlist':
                    cursor19 = conndb.execute("SELECT * from  planowanie p join stany s on p.Out_id = s.Id")
                    reply = 'true;GPIO_SAlist;'
                    for row in cursor19:
                        reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[4])+';'+str(row[6])+';'+str(row[11])+';'+str(row[14])+';'
                elif datalist[1] == 'GPIO_set':
                    GPIOset(datalist[3],datalist[4])
                    reply = 'true;GPIO_set;'+datalist[4]+';'+datalist[5]+';'
                    gpiolist = datalist[3].split(",")
                    for gpio in gpiolist:
                        r1 = conndb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=? and IN_OUT like 'out') or (GPIO_BCM like ? and Id!=? and IN_OUT like 'out');",(datalist[5],"%"+gpio+",%",datalist[2],"%,"+gpio+"%",datalist[2])).rowcount
                        r2 = conndb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? and IN_OUT like 'out' ;",(datalist[4],datalist[5],gpio,datalist[2])).rowcount
                    conndb.execute("UPDATE stany set Stan =?,Edit_time=? where Id=?",(datalist[4],datalist[5],datalist[2]))
                    stan = int(datalist[4])
                    reverse = int(datalist[6])
                    conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",(datalist[7],datalist[2],"ON" if ((stan and not reverse) or (not stan and reverse)) else "OFF"))
                    if r1 > 0 or r2 > 0:
                        reply = 'true;GPIO_set;'+datalist[4]+';2000-01-01 00:00:00.000;'
                    conndb.commit()
                elif datalist[1] == 'GPIO_state':
                    reply = 'true;GPIO_state;'+str(datalist[2])+';'+str(GPIOstate(datalist[2]))+';'
                elif datalist[1] == 'Insert_Action':
                    conndb.execute("INSERT INTO planowanie(Warunek, Podwarunek, Rodzaj, Dane, Out_id, Stan, Edit_time) VALUES(?,?,?,?,?,?,?)",(datalist[2],datalist[3],datalist[4],datalist[5],datalist[6],datalist[7],datalist[8]))
                    conndb.commit()
                    reply= 'true;Insert_Action;'
                elif datalist[1] == 'Update_Action':
                    conndb.execute("UPDATE planowanie set Warunek=?, Podwarunek=?, Rodzaj=?, Dane=?, Out_id=?, Stan=?, Edit_time=? where Id=?",(datalist[2],datalist[3],datalist[4],datalist[5],datalist[6],datalist[7],datalist[9],datalist[8]))
                    conndb.commit()
                    reply= 'true;Update_Action;'
                elif datalist[1] == 'Delete_Action':
                    conndb.execute("DELETE from planowanie where Id=?",(datalist[2],))
                    conndb.execute("UPDATE planowanie set Edit_time=? where Id in (SELECT Id FROM planowanie LIMIT 1)",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
                    conndb.commit()
                    reply= 'true;Delete_Action;'
                elif datalist[1] == 'HR_count':
                    cursor6 = conndb.execute("SELECT COUNT(*) FROM historia where Czas between ? and ?",(datalist[2],datalist[3]))
                    for row in cursor6:
                        reply = 'true;HR_count;'+str(row[0])+';'
                elif datalist[1] == 'HR_sel':
                    cursor5 = conndb.execute("SELECT h.Id,Czas,Typ,case when s.Name is NULL then p.Name else s.Name end as 'Name',h.Stan FROM historia h Left JOIN stany s ON s.Id = h.Id_IO left JOIN pwm p ON p.Id = h.Id_Pwm where Czas between ? and ? order by Czas DESC",(datalist[2],datalist[3]))
                    reply = 'true;HR_sel;'+datalist[4]+";"
                    for row in cursor5:
                        reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[4])+';'
                else:
                    reply = 'false;Conection OK, but no compabile method found, probably encryption error;'
            else:
                reply = 'false;Wrong password !;'
            if PASSWORD != '' and passwalidation == True :
                reply = '1;'+encrypt(ENC_KEY,reply)+';'
            s.sendto(reply , addr)
            print 'Message[' + addr[0] + ':' + str(addr[1]) + '] - ' + data
            print reply
    except KeyboardInterrupt:
        print "...Ending..."
        exitapp = True
        s.close()
        conndb.close()
        GPIO.cleanup()
        sys.exit()
