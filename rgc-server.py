import SocketServer
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
import logging
from systemd.journal import JournalHandler
import re
import zlib
from random import choice
from string import ascii_uppercase
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
import urlparse
import urllib2
import json
log = logging.getLogger('demo')
log.addHandler(JournalHandler())
log.setLevel(logging.INFO)

HOST = ''
PORT = 8888
WWWPORT = 80
PASSWORD = ''
MODE = 'all'
ENC_KEY = ''
exitapp = False
break_ = -1
db_path = 'rgc-server.db3'
CODE_VERSION = 4
TAG_VERSION = 2.1
startTime = None
DS = None
TSL = None
pwm = {k: [] for k in range(2)}
debug = False

def stringToint(string):
    try:
        ints = int(string)
    except ValueError:
        log.error("Error while converting String to Int")
    return ints

trigger_timer = {}
def actions(conndb4,updateSignal,idCE = 0,changedBy="scheduled"):
    if idCE == 0:
        cursor = conndb4.execute("SELECT * FROM akcje a left join stany s on a.Out_id = s.Id left join pwm p on a.Pwm_id = p.Id")
    else:
        cursor = conndb4.execute("SELECT * FROM akcje a left join stany s on a.Out_id = s.Id left join pwm p on a.Pwm_id = p.Id WHERE a.Id = ?",(str(idCE),))
    for row in cursor:
        cursorW = conndb4.execute("SELECT * FROM wyzwalaczeAkcji w left join sensory s on w.Id_s = s.Id left join stany st on w.Id_s = st.Id left join pwm p on w.Id_s = p.Id WHERE w.Id_a = ? ORDER BY w.Lp",(row[0],))
        conditions = []
        conditionString = ''
        for rowW in cursorW:
            if rowW[4] == 'date':
                conditions.append(eval("datetime.strptime('"+rowW[6]+"','%Y-%m-%d %H:%M')"+rowW[5]+"datetime.utcnow().replace(microsecond=0,second=0)"))
            elif rowW[4] == 'hour':
                triggerHour = datetime.strptime(rowW[6],'%H:%M')
                currentHour = datetime.utcnow().replace(1900,1,1,microsecond=0,second=0)
                conditions.append(eval('triggerHour'+rowW[5]+'currentHour'))
            elif rowW[4] == 'timer':
                timelist = rowW[6].split(",")
                if rowW[0] not in trigger_timer or trigger_timer[rowW[0]][0] != int(timelist[0])*1000:
                    trigger_timer[rowW[0]] = (int(timelist[0])*1000,int(timelist[1])*1000,int(round(time.time()*1000)))
                timeS = trigger_timer[rowW[0]][1] - (int(round(time.time()*1000)) - trigger_timer[rowW[0]][2])
                conditions.append(timeS <= 0)
                if timeS > 0:
                    trigger_timer[rowW[0]] =(trigger_timer[rowW[0]][0],timeS,int(round(time.time()*1000)))
                    if updateSignal:
                        conndb4.execute("UPDATE wyzwalaczeAkcji set Dane=? where Id=?", (str(trigger_timer[rowW[0]][0]/1000)+','+str(timeS/1000), rowW[0]))
                        conndb4.execute("UPDATE akcje set Edit_time=? where Id=?", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), row[0]))
                        conndb4.commit()
                    break
                else:
                    trigger_timer[rowW[0]] = (trigger_timer[rowW[0]][0],trigger_timer[rowW[0]][0],int(round(time.time()*1000)))
            elif rowW[4] == 'sensor':
                sensorValue = getCurrentSensorValue(rowW[2],conndb4)
                conditions.append(eval(str(sensorValue)+rowW[5]+rowW[6]))
            elif rowW[4] == 'weekday':
                conditions.append(eval(rowW[6]+rowW[5]+"datetime.now().weekday()"))
            elif rowW[4] == 'i/o':
                planned = int(rowW[6])
                cState = int(rowW[18])
                reverse = int(rowW[22])
                conditions.append(True if ((planned==cState and not reverse) or (planned==2 and planned==cState) or (planned!=cState and reverse and planned!=2)) else False)
            elif rowW[4] == 'pwm state':
                conditions.append(int(rowW[6]) == int(rowW[29]))
            elif rowW[4] == 'pwm fr':
                conditions.append(eval(rowW[6]+rowW[5]+str(rowW[27])) and int(rowW[29] == 1))
            elif rowW[4] == 'pwm dc':
                conditions.append(eval(rowW[6]+rowW[5]+str(rowW[28])) and int(rowW[29] == 1))
            elif rowW[4] == 'in chain':
                conditions.append(eval(rowW[6]+rowW[5]+str(idCE != 0)))
            elif rowW[4] == 'ping':
                response = os.system("ping -c 1 -w 2 -t 2 "+rowW[2]+" > /dev/null 2>&1")
                if response == 0:
                    isPinging = True
                else:
                    isPinging = False
                conditions.append(eval(rowW[6]+rowW[5]+str(isPinging)))
        if len(conditions) > 0:
            if row[3] == None or not row[3]:
                i=1
                for cond in conditions:
                    if len(conditions)==i:
                        conditionString+=str(cond)
                    else:
                        conditionString+=str(cond)+" and "
                    i+=1
            else:
                i=1
                conditionString = row[3]
                for cond in conditions:
                    conditionString = re.sub('#'+str(i)+'#', str(cond), conditionString)
                    i+=1
            conjunctionValid = True
            try:
                eval(str(conditionString))
            except:
                pass
                log.error("Wrong conjunction at "+row[10]+":"+str(conditionString))
                conjunctionValid = False
            noe = int(row[2])
            if conditionString != '' and conjunctionValid and (noe > 0 or noe == -1):
                if eval(str(conditionString)):
                    execuded = False
                    if row[1] == 'output':
                        execuded = outputChange(row[16],row[5],row[20],row[15],row[4],conndb4,changedBy,True if row[13] else False)
                    elif row[1] == 'pwm':
                        execuded = pwmChange(row[9],row[27],row[8],row[26],row[7],row[25],row[24],row[6],conndb4,changedBy,True if row[13] else False)
                    elif row[1] == 'chain':
                        threading.Thread(target=chainExecude, args=(row[12], changedBy, True if row[13] else False)).start()
                    if noe > 0 and execuded:
                        conndb4.execute("UPDATE akcje set Rodzaj=?,Edit_time=? where Id = ?", (
                            str(noe-1),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),row[0]))
                    conndb4.commit()

def chainExecude(id,changedBy,log=True):
    conndb1 = newDBConn()
    def cancelIf():
        cdb = newDBConn()
        cursor1 = cdb.execute("SELECT Status from lancuchy WHERE Id=?",(id,))
        row1 = cursor1.fetchone()
        if row1[0] == 0: sys.exit()
        cdb.close()
    chainBonds = conndb1.execute("SELECT * FROM spoiwaLancuchow s JOIN lancuchy l on s.Id_c = l.Id LEFT JOIN stany st ON s.Out_id = st.Id LEFT JOIN pwm p ON s.Pwm_id = p.Id LEFT JOIN akcje a ON s.A_id = a.Id WHERE l.Id = ? ORDER BY Lp",(id,)).fetchall()
    cursor = conndb1.execute("SELECT Status from lancuchy WHERE Id=?",(id,))
    sRow = cursor.fetchone()
    status = int(sRow[0])
    conndb1.close()
    if status == 0:
        for row in chainBonds:
            conndb2 = newDBConn()
            if log and status == 0: conndb2.execute("INSERT INTO historia(Typ, Id_c, Stan) VALUES(?,?,?)", (changedBy, id, "START"))
            status = row[2]
            conndb2.execute("UPDATE lancuchy SET Status=?,Edit_time=? WHERE Id=?",(row[2],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),id))
            conndb2.close()
            daley = row[3]
            while daley > 0 and not exitapp:
                start_time = time.time()
                cancelIf()
                time.sleep(1)
                daley = daley-(time.time() - start_time)
            cancelIf()
            conndb5 = newDBConn()
            if row[4] == 'output':
                cursor1 = conndb5.execute("SELECT Stan FROM Stany WHERE Id=?",(row[6],))
                row1 = cursor1.fetchone()
                outputChange(row1[0],row[7],row[22],row[17],row[6],conndb5,changedBy,log)
            elif row[4] == 'pwm':
                cursor1 = conndb5.execute("SELECT SS,DC,FR FROM Pwm WHERE Id=?",(row[8],))
                row1 = cursor1.fetchone()
                pwmChange(row[11],row1[0],row[10],row1[1],row[9],row1[2],row[26],row[8],conndb5,changedBy,log)
            elif row[4] == 'action':
                actions(conndb5,True,row[5],changedBy)
            if (len(chainBonds)) == row[2]:
                conndb5.execute("UPDATE lancuchy SET Status=?,Edit_time=? WHERE Id=?",(0,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),id))
                if log: conndb5.execute("INSERT INTO historia(Typ, Id_c, Stan) VALUES(?,?,?)", (changedBy, id, "END"))
            conndb5.commit()
            conndb5.close()



def outputChange(currentState,plannedState,Reverse,GPIO_BCM,id,cdb,changedBy,log=True):#14;5;18;13;4
    if (currentState != plannedState and not Reverse) or (currentState == plannedState and Reverse) or plannedState == 2:
        if plannedState == 2:
            set = int(not currentState)
        elif Reverse:
            set = int(not plannedState)
        else:
            set = plannedState
        GPIOset(str(GPIO_BCM), set)
        gpiolist = str(GPIO_BCM).split(",")
        for gpio in gpiolist:
            cdb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=? and IN_OUT like 'out') or (GPIO_BCM like ? and Id!=? and IN_OUT like 'out');", (
                datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), "%"+gpio+",%", id, "%,"+gpio+"%", id))
            cdb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? and IN_OUT like 'out' ;", (
                set, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), gpio, id))
        cdb.execute("UPDATE stany set Stan =?, Edit_time=? where Id=?", (
            set, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), id))
        if log: cdb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)", (changedBy, id, "ON" if (
            (set and not Reverse) or (not set and Reverse)) else "OFF"))
        cdb.commit()
        return True
    else: return False

def pwmChange(planed_ss,current_ss,planned_dc,current_dc,planned_fr,current_fr,GPIO_BCM,id,cdb,changedBy,log=True):#9;25;8;24;7;23;22;6
    pwmpins = GPIO_BCM.split(",")
    if planed_ss == 2:
        set = not current_ss
    else:
        set = planed_ss
    for pin in pwmpins:
        if current_ss!=set and set == 1:
            pwm[pin].start(int(planned_dc) if planned_dc else int(current_dc))
        if (current_ss!=set and set == 1) or (planned_fr!=current_fr and planned_fr and set == 1):
            pwm[pin].ChangeFrequency(float(planned_fr) if (planned_fr)else float(current_fr))
        if planned_dc and current_dc!=planned_dc and set == 1:
            pwm[pin].ChangeDutyCycle(int(planned_dc))
        if current_ss!=set and set == 0:
            pwm[pin].stop()
    if current_ss!=set or (current_dc!=planned_dc and planned_dc) or (current_fr!=planned_fr and planned_fr):
        cdb.execute("UPDATE pwm set FR=?,DC=?,Edit_time=?,SS=? where Id=?",(planned_fr if (planned_fr)else current_fr,planned_dc if (planned_dc)else current_dc, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), set, id))
        if log: cdb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)", (changedBy, id, ("OFF" if set==0 else "ON")+":DC="+(str(planned_dc) if planned_dc else str(current_dc))+"%,FR="+(str(planned_fr) if planned_fr else str(current_fr))+"Hz"))
        if debug: print 'BY SHEDULED:'+str(id)+(" OFF" if set==0 else " ON")+":DC="+(str(planned_dc) if planned_dc else str(current_dc))+"%,FR="+(str(planned_fr) if planned_fr else str(current_fr))+"Hz"
        return True
    else: return False

def GPIOset(pinout, onoff):
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
    GPIO.setup(inpin, GPIO.IN, GPIO.PUD_UP)

def GPIOPWM(inpin, fr):
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(inpin, GPIO.OUT)
    p = GPIO.PWM(inpin, fr)
    return p

def inputLoop2(outid, inid, inpin, Stan, reverse):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    inpin = int(inpin)
    id2 = int(inid)
    Stan = int(Stan)
    GPIO.setup(inpin, GPIO.IN, GPIO.PUD_UP)
    if Stan == 1: stan = 6
    else: stan = 1
    while exitapp == False:
        conndb = newDBConn()
        if stan == 1:
            if GPIO.input(inpin) == 0:
                stan = 2
            cursor1 = conndb.execute(
                "SELECT Stan, Reverse from stany where Id=?", (outid,))
            for row in cursor1:
                if int(row[0]) == 1:
                    stan = 3
        elif stan == 2:
            cursor2 = conndb.execute(
                "SELECT GPIO_BCM, Reverse from stany where Id=?", (outid,))
            for row in cursor2:
                GPIOset(str(row[0]), 1)
                gpiolist = row[0].split(",")
            for gpio in gpiolist:
                conndb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=?) or (GPIO_BCM like ? and Id!=?);", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), "%"+gpio+",%", str(outid), "%,"+gpio+"%", str(outid)))
                conndb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? ;", (str(
                    1), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), gpio, str(outid)))
            conndb.execute("UPDATE stany set Stan =?,Edit_time=? where Id=?", (str(
                1), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(outid)))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                           ("input", outid, "ON" if (not reverse) else "OFF"))
            conndb.execute("UPDATE stany set Stan =1,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",
                           (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(inpin)))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                           ("input", inid, "ON" if (not reverse) else "OFF"))
            conndb.commit()
            stan = 5
            if GPIO.input(inpin) == 1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                               ("input", inid, "ON" if reverse else "OFF"))
                conndb.commit()
                stan = 3
        elif stan == 3:
            if GPIO.input(inpin) == 0:
                stan = 4
            cursor1 = conndb.execute(
                "SELECT Stan, Reverse from stany where Id=?", (outid,))
            for row in cursor1:
                if int(row[0]) == 0:
                    stan = 1
        elif stan == 4:
            cursor2 = conndb.execute(
                "SELECT GPIO_BCM, Reverse from stany where Id=?", (outid,))
            for row in cursor2:
                GPIOset(str(row[0]), 0)
                gpiolist = row[0].split(",")
            for gpio in gpiolist:
                conndb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=?) or (GPIO_BCM like ? and Id!=?);", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), "%"+gpio+",%", str(outid), "%,"+gpio+"%", str(outid)))
                conndb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? ;", (str(
                    0), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), gpio, str(outid)))
            conndb.execute("UPDATE stany set Stan =?,Edit_time=? where Id=?", (str(
                0), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(outid)))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                           ("input", outid, "ON" if reverse else "OFF"))
            conndb.execute("UPDATE stany set Stan =1,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'",
                           (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(inpin)))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                           ("input", inid, "ON" if (not reverse) else "OFF"))
            conndb.commit()
            stan = 6
            if GPIO.input(inpin) == 1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                               ("input", inid, "ON" if reverse else "OFF"))
                conndb.commit()
                stan = 1
        elif stan == 5:
            if GPIO.input(inpin) == 1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                               ("input", inid, "ON" if reverse else "OFF"))
                conndb.commit()
                stan = 3
        elif stan == 6:
            if GPIO.input(inpin) == 1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                               ("input", inid, "ON" if reverse else "OFF"))
                conndb.commit()
                stan = 1
        conndb.close()
        if break_ == id2: break
        time.sleep(0.05)

def inputLoop3(id, inpin, Stan, reverse, outid):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    inpin = int(inpin)
    id2 = int(id)
    Stan = int(Stan)
    GPIO.setup(inpin, GPIO.IN, GPIO.PUD_UP)
    Oreverse = 0
    if Stan == 0: stan = 2
    elif Stan == 1: stan = 4
    else: stan = 2
    while exitapp == False:
        conndb = newDBConn()
        if stan == 2:
            if GPIO.input(inpin) == 0:
                cursor = conndb.execute(
                    "SELECT GPIO_BCM, Reverse from stany where Id=?", (outid,))
                for row in cursor:
                    Oreverse = int(row[1])
                    GPIOset(str(row[0]), 1 if not Oreverse else 0)
                    gpiolist = row[0].split(",")
                for gpio in gpiolist:
                    conndb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=?) or (GPIO_BCM like ? and Id!=?);", (
                        datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), "%"+gpio+",%", str(outid), "%,"+gpio+"%", str(outid)))
                    conndb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? ;", (str(
                        1 if not Oreverse else 0), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), gpio, str(outid)))
                conndb.execute("UPDATE stany set Stan =?,Edit_time=? where Id=?", (str(
                    1 if not Oreverse else 0), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(outid)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                               ("input", outid, "ON" if (not reverse) else "OFF"))
                conndb.execute("UPDATE stany set Stan =1,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                               ("input", id, "ON" if (not reverse) else "OFF"))
                conndb.commit()
                stan = 4
        if stan == 4:
            if GPIO.input(inpin) == 1:
                cursor = conndb.execute(
                    "SELECT GPIO_BCM, Reverse from stany where Id=?", (outid,))
                for row in cursor:
                    Oreverse = int(row[1])
                    GPIOset(str(row[0]), 0 if not Oreverse else 1)
                    gpiolist = row[0].split(",")
                for gpio in gpiolist:
                    conndb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=?) or (GPIO_BCM like ? and Id!=?);", (
                        datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), "%"+gpio+",%", str(outid), "%,"+gpio+"%", str(outid)))
                    conndb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? ;", (str(
                        0 if not Oreverse else 1), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), gpio, str(outid)))
                conndb.execute("UPDATE stany set Stan =?,Edit_time=? where Id=?", (str(
                    0 if not Oreverse else 1), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(outid)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                               ("input", outid, "ON" if reverse else "OFF"))
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                               ("input", id, "ON" if reverse else "OFF"))
                conndb.commit()
                stan = 2
        conndb.close()
        if break_ == id2: break
        time.sleep(0.05)

def inputLoop4(id, inpin, Stan, reverse):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    inpin = int(inpin)
    id2 = int(id)
    Stan = int(Stan)
    GPIO.setup(inpin, GPIO.IN, GPIO.PUD_UP)
    if Stan == 0: stan = 2
    elif Stan == 1: stan = 4
    else: stan = 2
    while exitapp == False:
        conndb = newDBConn()
        if stan == 2:
            if GPIO.input(inpin) == 0:
                conndb.execute("UPDATE stany set Stan =1,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                               ("input", id, "ON" if (not reverse) else "OFF"))
                conndb.commit()
                stan = 4
        if stan == 4:
            if GPIO.input(inpin) == 1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=? where GPIO_BCM=? and IN_OUT like 'in'", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(inpin)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                               ("input", id, "ON" if reverse else "OFF"))
                conndb.commit()
                stan = 2
        conndb.close()
        if break_ == id2: break
        time.sleep(0.05)

def services():
    updateCD = 30000
    while exitapp == False:
        conndbth = newDBConn()
        startTime = int(round(time.time()*1000))
        try:
            actions(conndbth, updateCD <= 0)
            if sensorsInit: sensorLoop(conndbth)
        except Exception as e:
            log.error("Error: "+e.message)
        conndbth.close()
        elapsedTime = int(round(time.time()*1000))-startTime
        if updateCD <= 0: updateCD = 30000
        if elapsedTime < 1000: 
            time.sleep(1)
            updateCD -= 1000
        updateCD -= elapsedTime

def newDBConn():
    cdb = sqlite3.connect(db_path, timeout=15, isolation_level=None)
    cdb.text_factory = str
    return cdb

def requestMethod(data):
    datalist = data.split(";")
    passwalidation = False
    httpCode = 200
    if PASSWORD == '':
        passwalidation = True
    else:
        if datalist[0] == PASSWORD:
            temp = decrypt(ENC_KEY, datalist[1])
            if temp == 'error':
                passwalidation = False
                print 'Decrytion error'
            else:
                datalist = ("0;"+temp).split(";")
                data = temp
                passwalidation = True
        else:
            passwalidation = False
    if debug: print 'RECIVED: '+data
    conndb = newDBConn()
    if passwalidation == True:
        if datalist[1] == 'version_check':
            reply = 'true;version_check;'+str(CODE_VERSION)+';'
        elif datalist[1] == 'GPIO_OEtime':
            cursor = conndb.execute(
                "SELECT Max(Edit_time) FROM stany where IN_OUT like 'out'")
            for row in cursor:
                reply = 'true;GPIO_OEtime;'+str(row[0])+';'
        elif datalist[1] == 'GPIO_Olist':
            cursor = conndb.execute(
                "SELECT * from stany where IN_OUT like 'out'")
            reply = 'true;GPIO_Olist;'
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2]) + \
                    ';'+str(row[3])+';'+str(row[6])+';'+str(row[8])+';'
        elif datalist[1] == 'GPIO_OlistT0':
            cursor = conndb.execute(
                "SELECT * from stany where IN_OUT like 'out' AND Bindtype = 0")
            reply = 'true;GPIO_OlistT0;'
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2]) + \
                    ';'+str(row[3])+';'+str(row[6])+';'+str(row[8])+';'
        elif datalist[1] == 'Add_GPIO_out':
            idio = conndb.execute("INSERT INTO stany VALUES (null,?,2,?,'out',?,?,null,?)", (
                datalist[2], datalist[3], datalist[4], datalist[5], datalist[6])).lastrowid
            conndb.execute(
                "INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)", (datalist[7], str(idio), "ADDED"))
            reply = 'true;Add_GPIO_out;'
        elif datalist[1] == 'Edit_GPIO_out':
            conndb.execute("UPDATE stany set Stan=2, GPIO_BCM=?,Name=?, Edit_time=?, reverse=?, Bindtype=? where Id=?", (
                datalist[3], datalist[4], datalist[5], datalist[6], datalist[8], datalist[2]))
            conndb.execute(
                "INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)", (datalist[9], datalist[2], "EDITED"))
            pwmpins = datalist[3].split(',')
            pwmpins2 = datalist[7].split(',')
            for pin2 in pwmpins2:
                if pin2 not in pwmpins:
                    GPIO.cleanup(int(pin2))
            reply = 'true;Edit_GPIO_out;'
        elif datalist[1] == 'Delete_GPIO_out':
            break_ = int(datalist[2])
            conndb.execute(
                "DELETE from stany where Id=?", (datalist[2],))
            conndb.execute("UPDATE stany set Edit_time=? where Id in (SELECT Id FROM stany LIMIT 1)", (
                datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            conndb.execute(
                "DELETE from historia where Id_IO=?", (datalist[2],))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)",
                            (datalist[5], datalist[2], datalist[4]+" DELETED"))
            r2 = conndb.execute("DELETE FROM spoiwaLancuchow WHERE Out_id=?", (datalist[2],)).rowcount
            if r2 > 0:
                conndb.execute("UPDATE lancuchy set Edit_time=? where Id in (SELECT Id FROM lancuchy LIMIT 1)", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            r3 = conndb.execute("DELETE FROM akcje WHERE Out_id=?", (datalist[2],)).rowcount
            r4 = conndb.execute("DELETE FROM wyzwalaczeAkcji WHERE Id_s=? AND Warunek = 'i/o'", (datalist[2],)).rowcount
            if r3 > 0 or r4 > 0:
                conndb.execute("UPDATE akcje set Edit_time=? where Id in (SELECT Id FROM akcje LIMIT 1)", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            pwmpins = datalist[3].split(",")
            for pin in pwmpins:
                GPIO.cleanup(int(pin))
            reply = 'true;Delete_GPIO_out;'+datalist[2]+';'
        elif datalist[1] == 'GPIO_IEtime':
            cursor = conndb.execute(
                "SELECT Max(Edit_time) FROM stany where IN_OUT like 'in'")
            for row in cursor:
                reply = 'true;GPIO_IEtime;'+str(row[0])+';'
        elif datalist[1] == 'GPIO_Ilist':
            cursor = conndb.execute(
                "SELECT * from stany where IN_OUT like 'in'")
            reply = 'true;GPIO_Ilist;'
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(
                    row[3])+';'+str(row[6])+';'+str(row[7])+';'+str(row[8])+';'
        elif datalist[1] == 'Add_GPIO_in':
            id = conndb.execute("INSERT INTO stany VALUES (null,?,0,?,'in',?,?,?,?)", (
                datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datalist[7])).lastrowid
            conndb.execute(
                "INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)", (datalist[8], str(id), "ADDED"))
            if datalist[7] == '1':
                threading.Thread(target=inputLoop2, args=(
                    datalist[6], id, datalist[2], '0', datalist[5])).start()
            elif datalist[7] == '2':
                threading.Thread(target=inputLoop3, args=(
                    id, datalist[2], '0', datalist[5], datalist[6])).start()
            else:
                threading.Thread(target=inputLoop4, args=(
                    id, datalist[2], '0', datalist[5])).start()
            reply = 'true;Add_GPIO_in;'
        elif datalist[1] == 'Edit_GPIO_in':
            break_ = int(datalist[2])
            conndb.execute(
                "DELETE from stany where Id=?", (datalist[2],))
            conndb.execute(
                "DELETE from historia where Id_IO=?", (datalist[2],))
            id = conndb.execute("INSERT INTO stany VALUES (null,?,0,?,'in',?,?,?,?)", (
                datalist[3], datalist[4], datalist[5], datalist[6], datalist[7], datalist[8])).lastrowid
            conndb.execute(
                "INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)", (datalist[10], str(id), "EDITED"))
            if datalist[3] != datalist[9]:
                GPIO.cleanup(int(datalist[9]))
            if datalist[8] == '1':
                threading.Thread(target=inputLoop2, args=(
                    datalist[7], id, datalist[3], '0', datalist[6])).start()
            elif datalist[8] == '2':
                threading.Thread(target=inputLoop3, args=(
                    id, datalist[3], '0', datalist[6], datalist[7])).start()
            else:
                threading.Thread(target=inputLoop4, args=(
                    id, datalist[3], '0', datalist[6])).start()
            reply = 'true;Edit_GPIO_in;'
        elif datalist[1] == 'GPIO_Oname':
            cursor = conndb.execute(
                "SELECT Id,Name,GPIO_BCM,Reverse from stany where IN_OUT like 'out'")
            reply = 'true;GPIO_Oname;'
            for row in cursor:
                reply += str(row[0])+';'+str(row[1]) + \
                    ';'+str(row[2])+';'+str(row[3])+';'
        elif datalist[1] == 'GPIO_PEtime':
            cursor = conndb.execute("SELECT Max(Edit_time) FROM pwm")
            for row in cursor:
                reply = 'true;GPIO_PEtime;'+str(row[0])+';'
        elif datalist[1] == 'GPIO_Plist':
            cursor = conndb.execute("SELECT * from pwm")
            reply = 'true;GPIO_Plist;'
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(
                    row[3])+';'+str(row[4])+';'+str(row[5])+';'+str(row[6])+';'
        elif datalist[1] == 'GPIO_PDC':
            pwmpins = datalist[3].split(",")
            for pin in pwmpins:
                pwm[pin].ChangeDutyCycle(int(datalist[4]))
            reply = 'true;GPIO_PDC;'+datalist[4]+';'
        elif datalist[1] == 'GPIO_PDCu':
            conndb.execute("UPDATE pwm set DC=?,Edit_time=? where Id=?",
                            (datalist[4], datalist[5], datalist[2]))
            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)",
                            (datalist[6], datalist[2], "DC="+datalist[4]+"%"))
            reply = 'true;GPIO_PDCu;'+datalist[4]+';'+datalist[5]+';'
        elif datalist[1] == 'GPIO_PFRDC':
            pwmpins = datalist[3].split(",")
            for pin in pwmpins:
                pwm[pin].ChangeDutyCycle(int(datalist[5]))
                pwm[pin].ChangeFrequency(float(datalist[4]))
            conndb.execute("UPDATE pwm set FR=?,DC=?,Edit_time=? where Id=?",
                            (datalist[4], datalist[5], datalist[6], datalist[2]))
            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)", (
                datalist[7], datalist[2], "DC="+datalist[5]+"%,FR="+datalist[4]+"Hz"))
            reply = 'true;GPIO_PFRDC;' + \
                datalist[4]+';'+datalist[6]+';'+datalist[5]+';'
        elif datalist[1] == 'GPIO_PSS':
            pwmpins = datalist[3].split(",")
            for pin in pwmpins:
                if datalist[6] == '1':
                    pwm[pin].start(int(datalist[4]))
                    pwm[pin].ChangeFrequency(float(datalist[7]))
                    conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)", (datalist[8], datalist[2], "ON:DC="+datalist[4]+"%,FR="+datalist[7]+"Hz"))
                elif datalist[6] == '0':
                    pwm[pin].stop()
                    conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)", (datalist[8], datalist[2], "OFF"))
            conndb.execute("UPDATE pwm set DC=?,Edit_time=?,SS=? where Id=?",(datalist[4], datalist[5], datalist[6], datalist[2]))
            reply = 'true;GPIO_PSS;' + \
                datalist[4]+';'+datalist[5]+';'+datalist[6]+';'
        elif datalist[1] == 'Add_GPIO_pwm':
            pwmpins = datalist[2].split(',')
            for pin in pwmpins:
                pwm[pin] = GPIOPWM(int(pin), float(datalist[3]))
                pwm[pin].start(int(datalist[4]))
            idpwm = conndb.execute("INSERT INTO pwm VALUES (null,?,?,?,1,?,?,?)", (
                datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datalist[7])).lastrowid
            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)", (datalist[8], str(
                idpwm), "ADDED:DC="+datalist[4]+"%,FR="+datalist[3]+"Hz"))
            reply = 'true;Add_GPIO_pwm;'
        elif datalist[1] == 'Delete_GPIO_pwm':
            break_ = int(datalist[2])
            conndb.execute("DELETE from pwm where Id=?", (datalist[2],))
            conndb.execute("DELETE from historia where Id_Pwm=?", (datalist[2],))
            conndb.execute("UPDATE pwm set Edit_time=? where Id in (SELECT Id FROM pwm LIMIT 1)", (
                datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)",
                            (datalist[5], datalist[2], datalist[4]+" DELETED"))
            r2 = conndb.execute("DELETE FROM spoiwaLancuchow WHERE Pwm_id=?", (datalist[2],)).rowcount
            if r2 > 0:
                conndb.execute("UPDATE lancuchy set Edit_time=? where Id in (SELECT Id FROM lancuchy LIMIT 1)", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            r3 = conndb.execute("DELETE FROM akcje WHERE Pwm_id=?", (datalist[2],)).rowcount
            r4 = conndb.execute("DELETE FROM wyzwalaczeAkcji WHERE Id_s=? AND Warunek LIKE 'pwm%'", (datalist[2],)).rowcount
            if r3 > 0 or r4 > 0:
                conndb.execute("UPDATE akcje set Edit_time=? where Id in (SELECT Id FROM akcje LIMIT 1)", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            pwmpins = datalist[3].split(',')
            for pin in pwmpins:
                pwm[pin].stop()
                pwm.pop(pin)
                GPIO.cleanup(int(pin))
            reply = 'true;Delete_GPIO_pwm;'
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
                    pwm[pin2] = GPIOPWM(int(pin2), float(datalist[5]))
                    pwm[pin2].start(int(datalist[6]))
                else:
                    pwm[pin2].ChangeDutyCycle(int(datalist[6]))
                    pwm[pin2].ChangeFrequency(float(datalist[5]))
            conndb.execute("UPDATE pwm set GPIO_BCM=?, FR=?, DC=?, SS=1, Name=?, Reverse=?, Edit_time=? where Id=?", (
                datalist[4], datalist[5], datalist[6], datalist[7], datalist[8], datalist[9], datalist[2]))
            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(?,?,?)", (
                datalist[10], datalist[2], "EDITED:DC="+datalist[6]+"%,FR="+datalist[5]+"Hz"))
            reply = 'true;Edit_GPIO_pwm;'
        elif datalist[1] == 'Allpins_GPIO_pwm':
            reply = 'true;Allpins_GPIO_pwm;'
            cursor = conndb.execute("SELECT GPIO_BCM from pwm")
            for row in cursor:
                pins = row[0].split(',')
                for pin in pins:
                    reply += pin+';'
        elif datalist[1] == 'Allpins_GPIO_out':
            reply = 'true;Allpins_GPIO_out;'
            cursor = conndb.execute(
                "SELECT GPIO_BCM from stany where IN_OUT like 'out'")
            for row in cursor:
                pins = str(row[0]).split(',')
                for pin in pins:
                    reply += pin+';'
        elif datalist[1] == 'AllUsedPins_GPIO':
            reply = 'true;AllUsedPins_GPIO;'
            sqlExec ='''
                SELECT GPIO_BCM from stany WHERE IN_OUT like 'out' AND Id not like '{id_out}'
                UNION
                SELECT GPIO_BCM from stany WHERE IN_OUT like 'in' AND Id not like '{id_in}'
                UNION
                SELECT GPIO_BCM from pwm WHERE Id not like '{id_pwm}'
                UNION
                SELECT GPIO_BCM from sensory WHERE Id not like '{id_s}'
            '''.format(id_out = datalist[3] if datalist[2] == 'out' else '',id_in = datalist[3] if datalist[2] == 'in' else '',id_pwm = datalist[3] if datalist[2] == 'pwm' else '',id_s = datalist[3] if datalist[2] == 'sensor' else '')
            cursor = conndb.execute(sqlExec)
            for row in cursor:
                pins = str(row[0]).split(',')
                for pin in pins:
                    reply += pin+';'
        elif datalist[1] == 'Allpins_GPIO_in':
            reply = 'true;Allpins_GPIO_in;'
            cursor = conndb.execute(
                "SELECT GPIO_BCM from stany where IN_OUT like 'in'")
            for row in cursor:
                reply += str(row[0])+';'
        elif datalist[1] == 'GPIO_set':
            GPIOset(datalist[3], datalist[4])
            reply = 'true;GPIO_set;'+datalist[4]+';'+datalist[5]+';'
            gpiolist = datalist[3].split(",")
            for gpio in gpiolist:
                r1 = conndb.execute("UPDATE stany set Stan =2,Edit_time=? where (GPIO_BCM like ? and Id!=? and IN_OUT like 'out') or (GPIO_BCM like ? and Id!=? and IN_OUT like 'out');", (
                    datalist[5], "%"+gpio+",%", datalist[2], "%,"+gpio+"%", datalist[2])).rowcount
                r2 = conndb.execute("UPDATE stany set Stan =?,Edit_time=? where GPIO_BCM =? and Id!=? and IN_OUT like 'out' ;", (
                    datalist[4], datalist[5], gpio, datalist[2])).rowcount
            conndb.execute("UPDATE stany set Stan =?,Edit_time=? where Id=?",
                            (datalist[4], datalist[5], datalist[2]))
            stan = int(datalist[4])
            reverse = int(datalist[6])
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(?,?,?)", (datalist[7], datalist[2], "ON" if (
                (stan and not reverse) or (not stan and reverse)) else "OFF"))
            if r1 > 0 or r2 > 0:
                reply = 'true;GPIO_set;' + \
                    datalist[4]+';2000-01-01 00:00:00.000;'
        elif datalist[1] == 'GPIO_state':
            reply = 'true;GPIO_state;' + \
                str(datalist[2])+';'+str(GPIOstate(datalist[2]))+';'
        elif datalist[1] == 'HR_count':
            cursor = conndb.execute(
                "SELECT COUNT(*) FROM historia where Czas between ? and ?", (datalist[2], datalist[3]))
            for row in cursor:
                reply = 'true;HR_count;'+str(row[0])+';'
        elif datalist[1] == 'SENSOR_list':
            reply = 'true;SENSOR_list;'
            cursor = conndb.execute("SELECT *,(SELECT Value from sensoryHistoria h WHERE h.Id=s.Id ORDER BY Timestamp DESC LIMIT 1),(SELECT Timestamp from sensoryHistoria h WHERE h.Id=s.Id ORDER BY Timestamp DESC LIMIT 1) from sensory s")
            for row in cursor:
                reply += str(row[0])+";"+str(row[1])+";"+str(row[4])+";"+str(row[9])+";"+str(row[2])+";"+str(row[3])+";"+str(row[5])+";"+str(row[10])+";"
        elif datalist[1] == 'SENSOR_names':
            reply = 'true;SENSOR_names;'
            cursor = conndb.execute("SELECT * from sensory")
            for row in cursor:
                reply += str(row[0])+";"+str(row[1]) + \
                    ";"+str(row[5])+";"
        elif datalist[1] == 'SENSOR_update':
            reply = 'true;SENSOR_update;'
            conndb.execute("UPDATE sensory set Name =?,H_refresh_sec=?,H_keep_days=? where Id=?", (
                datalist[3], datalist[4], datalist[5], datalist[2]))
        elif datalist[1] == 'SENSOR_remove':
            reply = 'true;SENSOR_remove;'
            conndb.execute("DELETE from sensory where Id=?", (datalist[2],))
            r4 = conndb.execute("DELETE FROM wyzwalaczeAkcji WHERE Id_s=? AND Warunek LIKE 'sensor'", (datalist[2],)).rowcount
            if r3 > 0 or r4 > 0:
                conndb.execute("UPDATE akcje set Edit_time=? where Id in (SELECT Id FROM akcje LIMIT 1)", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
        elif datalist[1] == 'NOTIF_check':
            reply = 'true;NOTIF_check;'
            if datalist[3] == "i/o":
                reply += "0;"
                if datalist[4] == "ANY":
                    cursor = conndb.execute(
                        "SELECT * from historia h JOIN stany s ON h.Id_IO=s.Id WHERE h.Id_IO = ? AND h.Czas > ? ORDER BY h.Czas DESC", (datalist[2], datalist[6]))
                else:
                    cursor = conndb.execute(
                        "SELECT * from historia h JOIN stany s ON h.Id_IO=s.Id WHERE h.Id_IO = ? AND h.Czas > ? AND h.Stan = ? ORDER BY h.Czas DESC", (datalist[2], datalist[6], datalist[4]))
                for row in cursor:
                    reply += str(row[10])+';'+str(row[1]) + \
                        ';'+str(row[2])+';'+str(row[5])+';'
            elif datalist[3] == "sensor":
                if sensorsInit:
                    updateSensorHistory(datalist[2],conndb)
                    cursor = conndb.execute(
                            "SELECT * from sensoryHistoria h JOIN sensory s ON h.Id = s.Id WHERE h.Id = ? AND h.Timestamp > ? AND h.Value "+datalist[5]+" ? ORDER BY h.Timestamp DESC", (datalist[2], datalist[6], datalist[4]))
                    i = 0
                    for row in cursor:
                        if i == 0:
                            reply += str(row[8])+';'
                        reply += str(row[4])+';'+str(row[1]) + \
                            ';'+str(row[7])+';'+str(row[2])+';'
                        i = i+1
        elif datalist[1] == 'GPIO_OInames':
            cursor = conndb.execute("SELECT Id,Name from stany")
            reply = 'true;GPIO_OInames;'
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';'
        elif datalist[1] == 'GPIO_PWMnames':
            cursor = conndb.execute("SELECT Id,Name from pwm")
            reply = 'true;GPIO_PWMnames;'
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';'
        elif datalist[1] == 'GPIO_ASAEtime':
            cursor = conndb.execute("SELECT Max(Edit_time) FROM akcje")
            row = cursor.fetchone()
            reply = 'true;GPIO_ASAEtime;'+str(row[0])+';'
        elif datalist[1] == 'GPIO_ASAlist':
            cursor = conndb.execute("SELECT * from  akcje a left join stany s on a.Out_id = s.Id left join pwm p on a.Pwm_id = p.Id left join lancuchy l on a.Chain_id = l.Id")
            reply = 'true;GPIO_ASAlist;'
            for row in cursor:
                reply+=str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[4])+';'+str(row[5])+';'+str(row[6])+';'+str(row[7])+';'+str(row[8])+';'+str(row[9])+';'+str(row[10])+';'+str(row[17])+';'+str(row[20])+';'+str(row[28])+';'+str(row[12])+';'+str(row[13])+';'+str(row[33])+';'
                cursor1 = conndb.execute("SELECT * FROM wyzwalaczeAkcji w left join stany s on w.Id_s=s.Id left join pwm p on w.Id_s=p.Id left join sensory se on w.Id_s=se.Id  WHERE w.Id_a=? ORDER BY w.Lp",(str(row[0]),))
                for row1 in cursor1:
                    reply+=str(row1[0])+'$'+str(row1[2])+'$'+str(row1[3])+'$'+str(row1[4])+'$'+str(row1[5])+'$'+str(row1[6])+'$'+str(row1[10])+'$'+str(row1[13])+'$'+str(row1[21])+'$'+str(row1[25])+'$'+str(row1[29])+'$'
                reply+=';'
        elif datalist[1] == 'GPIO_ASA_Add':
            if datalist[3] == 'output':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, Out_id, Rodzaj, Out_stan, Edit_time, Log) VALUES(?,?,?,?,?,?,?)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[9]))
            elif datalist[3] == 'pwm':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, Pwm_id, Rodzaj, Pwm_ss, Pwm_fr,Pwm_dc, Edit_time, Log) VALUES(?,?,?,?,?,?,?,?,?)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6],datalist[7],datalist[8], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), datalist[9]))
            elif datalist[3] == 'chain':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, Chain_id, Rodzaj, Edit_time, Log) VALUES(?,?,?,?,?,?)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), datalist[9]))
            reply = 'true;GPIO_ASA_Add;'
        elif datalist[1] == 'GPIO_ASA_Update':
            if datalist[3] == 'output':
                conndb.execute("UPDATE akcje set Nazwa=?, Typ=?, Out_id=?, Rodzaj=?, Out_stan=?, Edit_time=?, Log=? where Id=?", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10], datalist[9]))
            elif datalist[3] == 'pwm':
                conndb.execute("UPDATE akcje set Nazwa=?, Typ=?, Pwm_id=?, Rodzaj=?, Pwm_ss=?, Pwm_fr=?, Pwm_dc=?, Edit_time=?, Log=? where Id=?", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6],datalist[7],datalist[8],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10],datalist[9]))
            elif datalist[3] == 'chain':
                conndb.execute("UPDATE akcje set Nazwa=?, Typ=?, Chain_id=?, Rodzaj=?, Edit_time=?, Log=? where Id=?", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10], datalist[9]))
            reply = 'true;GPIO_ASA_Update;'
        elif datalist[1] == 'GPIO_ASA_Delete':
            conndb.execute("DELETE from akcje where Id=?", (datalist[2],))
            conndb.execute("DELETE from wyzwalaczeAkcji where Id_a=?", (datalist[2],))
            conndb.execute("UPDATE akcje set Edit_time=? where Id in (SELECT Id FROM akcje LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            r2 = conndb.execute("DELETE FROM spoiwaLancuchow WHERE A_id=?", (datalist[2],)).rowcount
            if r2 > 0:
                conndb.execute("UPDATE lancuchy set Edit_time=? where Id in (SELECT Id FROM lancuchy LIMIT 1)", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            reply = 'true;GPIO_ASA_Delete;'
        elif datalist[1] == 'GPIO_ASA_AddTrigger':
            cursor = conndb.execute("SELECT Id FROM wyzwalaczeAkcji WHERE Id_a = ?",(datalist[2],))
            rowcount = len(cursor.fetchall())
            conndb.execute("INSERT INTO wyzwalaczeAkcji(Id_a, Id_s, Lp, Warunek, Operator, Dane) VALUES(?,?,?,?,?,?)", (
                datalist[2], datalist[3], (int(rowcount)+1), datalist[4], datalist[5], datalist[6]))
            conndb.execute("UPDATE akcje set Edit_time=? where Id = ?", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ASA_AddTrigger;'
        elif datalist[1] == 'GPIO_ASA_UpdateTrigger':
            conndb.execute("UPDATE wyzwalaczeAkcji set Id_s=?, Warunek=?, Operator=?, Dane=? where Id=?", (
                    datalist[3], datalist[4], datalist[5], datalist[6], datalist[7]))
            conndb.execute("UPDATE akcje set Edit_time=? where Id = ?", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ASA_UpdateTrigger;'
        elif datalist[1] == 'GPIO_ASA_DeleteTrigger':
            conndb.execute("DELETE from wyzwalaczeAkcji where Id=?", (datalist[2],))
            cursor = conndb.execute("SELECT Id FROM wyzwalaczeAkcji WHERE Id_a = ?",(datalist[3],))
            i=1
            for row in cursor:
                conndb.execute("UPDATE wyzwalaczeAkcji set Lp=? where Id=?", (i,row[0]))
                i+=1
            conndb.execute("UPDATE akcje set Koniunkcja=?, Edit_time=? where Id = ?", (None,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[3]))
            reply = 'true;GPIO_ASA_DeleteTrigger;'
        elif datalist[1] == 'GPIO_ASA_SetConj':
            conndb.execute("UPDATE akcje set Koniunkcja=?, Edit_time=? where Id = ?", (datalist[2],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[3]))
            reply = 'true;GPIO_ASA_SetConj;'
        elif datalist[1] == 'Server_restart':
            statusCode = os.system("systemctl status rgc.service")
            if statusCode == 0:
                os.system("systemctl restart rgc.service")
            reply = 'true;Server_restart;'
        elif datalist[1] == 'Server_reboot':
            os.system("reboot")
        elif datalist[1] == 'Server_status_code':
            statusCode = os.system("systemctl status rgc.service")
            reply = 'true;Server_status_code;'+str(statusCode)+";"
        elif datalist[1] == 'GPIO_ChainEtime':
            cursor = conndb.execute("SELECT Max(Edit_time) FROM lancuchy")
            row = cursor.fetchone()
            reply = 'true;GPIO_ChainEtime;'+str(row[0])+';'
        elif datalist[1] == 'GPIO_ChainList':
            cursor = conndb.execute("SELECT * FROM lancuchy")
            reply = 'true;GPIO_ChainList;'
            for row in cursor:
                reply+=str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'
                cursor1 = conndb.execute("SELECT * FROM spoiwaLancuchow s LEFT JOIN stany st ON s.Out_id = st.Id LEFT JOIN pwm p ON s.Pwm_id = p.Id LEFT JOIN akcje a ON s.A_id = a.Id WHERE s.Id_c = ? ORDER BY Lp",(str(row[0]),))
                for row1 in cursor1:
                    reply+=str(row1[0])+'$'+str(row1[1])+'$'+str(row1[2])+'$'+str(row1[3])+'$'+str(row1[4])+'$'+str(row1[5])+'$'+str(row1[6])+'$'+str(row1[7])+'$'+str(row1[8])+'$'+str(row1[9])+'$'+str(row1[10])+'$'+str(row1[11])+'$'+str(row1[15])+'$'+str(row1[26])+'$'+str(row1[39])+'$'
                reply+=';'
        elif datalist[1] == 'GPIO_ChainExecute':
            threading.Thread(target=chainExecude, args=(datalist[2], datalist[3])).start()
            reply = 'true;GPIO_ChainExecute;'
        elif datalist[1] == 'GPIO_ChainCancel':
            conndb.execute("UPDATE lancuchy set Status=0 WHERE Id=?",(datalist[2],))
            reply = 'true;GPIO_ChainCancel;'
        elif datalist[1] == 'GPIO_ChainAdd':
            conndb.execute("INSERT INTO lancuchy (Nazwa,Status,Edit_time) VALUES(?,?,?)",(datalist[2],0,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')))
            reply = 'true;GPIO_ChainAdd;'
        elif datalist[1] == 'GPIO_ChainUpdate':
            conndb.execute("Update lancuchy SET Nazwa=?,Edit_time=? WHERE Id=?",(datalist[3],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ChainUpdate;'
        elif datalist[1] == 'GPIO_ChainDelete':
            conndb.execute("DELETE FROM lancuchy WHERE Id=?",(datalist[2]))
            conndb.execute("DELETE FROM spoiwaLancuchow WHERE Id_c=?",(datalist[2]))
            conndb.execute("UPDATE lancuchy set Edit_time=? where Id in (SELECT Id FROM lancuchy LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            r1 = conndb.execute("DELETE FROM akcje WHERE Chain_id=?", (datalist[2],)).rowcount
            if r1 > 0:
                conndb.execute("UPDATE akcje set Edit_time=? where Id in (SELECT Id FROM akcje LIMIT 1)", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            reply = 'true;GPIO_ChainDelete;'
        elif datalist[1] == 'GPIO_ChainBondDelete':
            conndb.execute("DELETE FROM spoiwaLancuchow WHERE Id=?",(datalist[2]))
            cursor = conndb.execute("SELECT Id FROM spoiwaLancuchow WHERE Id_c=? ORDER BY Lp",(datalist[3],))
            i = 1
            for row in cursor:
                conndb.execute("UPDATE spoiwaLancuchow SET Lp=? WHERE Id=?",(str(i),row[0]))
                i+=1
            conndb.execute("UPDATE lancuchy SET Edit_time=? WHERE Id=?",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[3]))
            reply = 'true;GPIO_ChainBondDelete;'
        elif datalist[1] == 'GPIO_ActionsNames':
            cursor = conndb.execute("SELECT Id,Nazwa from akcje")
            reply = 'true;GPIO_ActionsNames;'
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';'
        elif datalist[1] == 'GPIO_ChainBondAdd':
            cursor = conndb.execute("SELECT Id FROM spoiwaLancuchow WHERE Id_c = ?",(datalist[2],))
            rowcount = len(cursor.fetchall())
            if datalist[3] == 'output':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, Out_id, Out_stan, Lp) VALUES(?,?,?,?,?,?)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6],(int(rowcount)+1)))
            elif datalist[3] == 'pwm':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, Pwm_id, Pwm_ss, Pwm_fr, Pwm_dc, Lp) VALUES(?,?,?,?,?,?,?,?)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datalist[7], datalist[8],(int(rowcount)+1)))
            elif datalist[3] == 'action':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, A_id, Lp) VALUES(?,?,?,?,?)", (
                    datalist[2], datalist[3], datalist[4], datalist[5],(int(rowcount)+1)))
            conndb.execute("UPDATE lancuchy SET Edit_time=? WHERE Id=?",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ChainBondAdd;'
        elif datalist[1] == 'GPIO_ChainBondUpdate':
            if datalist[3] == 'output':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=?, Dalay=?, Out_id=?, Out_stan=? WHERE Id=?", (
                    datalist[3], datalist[4], datalist[5], datalist[6], datalist[9]))
            elif datalist[3] == 'pwm':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=?, Dalay=?, Pwm_id=?, Pwm_ss=?, Pwm_fr=?, Pwm_dc=? WHERE Id=?", (
                    datalist[3], datalist[4], datalist[5], datalist[6], datalist[7], datalist[8],datalist[9]))
            elif datalist[3] == 'action':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=?, Dalay=?, A_id=? WHERE Id=?", (
                    datalist[3], datalist[4], datalist[5],datalist[9]))
            conndb.execute("UPDATE lancuchy SET Edit_time=? WHERE Id=?",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ChainBondUpdate;'
        elif datalist[1] == 'GPIO_ChainBondsOrder':
            bondidlplist = datalist[3].split("$")
            i = 0
            while i<len(bondidlplist):
                conndb.execute("UPDATE spoiwaLancuchow SET Lp=? WHERE Id=?",(bondidlplist[i],bondidlplist[i+1]))
                i+=2
            conndb.execute("UPDATE lancuchy SET Edit_time=? WHERE Id=?",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ChainBondsOrder;'
        elif datalist[1] == 'Chain_names':
            cursor = conndb.execute("SELECT Id,Nazwa from lancuchy")
            reply = 'true;Chain_names;'
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';'
        elif datalist[1] == 'Server_logs':
                logs = os.popen('journalctl -u rgc.service -r -n 200 --no-pager').read()
                reply = 'true;Server_logs;'+logs+";"
        elif datalist[1] == 'Server_logs_JSON':
                logs = os.popen('journalctl -u rgc.service -r -n 50 --no-pager --output=export --utc').read()
                logsArr = logs.splitlines()
                reply = 'true;Server_logs_JSON;'
                for log in logsArr:
                    singleLog = log.split('=')
                    if singleLog[0] in ['__REALTIME_TIMESTAMP','PRIORITY','MESSAGE']:
                        reply += singleLog[1].replace(';','$')+";"
        elif datalist[1] == 'Server_status':
            status = os.popen('systemctl status rgc.service').read()
            reply = 'true;Server_status;'+status+";"
        elif datalist[1] == 'Server_status_params':
            status = os.popen('systemctl show rgc.service --no-page').read()
            reply = 'true;Server_status_params;'
            paramsArr = status.splitlines()
            for param in paramsArr:
                singleParams = param.split("=")
                for sparam in singleParams:
                    reply+=sparam+";"
        elif datalist[1] == 'Server_info':
            reply = 'true;Server_info;'
            reply += os.uname()[1]+';'
            reply += str(os.getloadavg())+';'
            reply += str(TAG_VERSION)+';'
            reply += startTime+';'
            timeConf = os.popen('timedatectl status').read()
            timeConfLines = timeConf.splitlines()
            for line in timeConfLines:
                reply += line+';'

        elif datalist[1] == 'Server_update':
            statusCode = os.system("systemctl status rgc.service")
            if statusCode == 0:
                path = os.getcwd()+"/rgc-server.tar.gz"
                fh = open(path, "wb")
                fh.write(datalist[2].decode('base64'))
                fh.close()
                import tarfile
                tar = tarfile.open(path)
                tar.extractall()
                tar.close()
                conndb.close()
                os.system("systemctl restart rgc.service")
        elif datalist[1] == 'HR_sel':
            cursor = conndb.execute(
                "SELECT h.Id,Czas,Typ,case when s.Name is NULL AND l.Nazwa is NULL then p.Name when p.Name is NULL AND l.Nazwa is NULL then s.Name else l.Nazwa end as 'Name',h.Stan FROM historia h Left JOIN stany s ON s.Id = h.Id_IO left JOIN pwm p ON p.Id = h.Id_Pwm left JOIN lancuchy l ON l.Id = h.Id_c where Czas between ? and ? order by Czas DESC LIMIT ?", (datalist[2], datalist[3],datalist[5]))
            reply = 'true;HR_sel;'+datalist[4]+";"
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';' + \
                    str(row[2])+';'+str(row[3])+';'+str(row[4])+';'
        elif datalist[1] == 'HR_selByCat':
            if datalist[4] == 'i/o':
                cursor = conndb.execute("SELECT h.Id,Czas,Typ,s.Name,h.Stan FROM historia h JOIN stany s ON s.Id = h.Id_IO WHERE Czas between ? and ? order by Czas DESC", (datalist[2], datalist[3]))
            elif datalist[4] == 'pwm':
                cursor = conndb.execute("SELECT h.Id,Czas,Typ,p.Name,h.Stan FROM historia h JOIN pwm p ON p.Id = h.Id_Pwm WHERE Czas between ? and ? order by Czas DESC", (datalist[2], datalist[3]))
            elif datalist[4] == 'chain':
                cursor = conndb.execute("SELECT h.Id,Czas,Typ,l.Nazwa,h.Stan FROM historia h JOIN lancuchy l ON l.Id = h.Id_c WHERE Czas between ? and ? order by Czas DESC", (datalist[2], datalist[3]))
            elif datalist[4] == 'all':
                cursor = conndb.execute("SELECT h.Id,Czas,Typ,case when s.Name is NULL AND l.Nazwa is NULL then p.Name when p.Name is NULL AND l.Nazwa is NULL then s.Name else l.Nazwa end as 'Name',h.Stan FROM historia h Left JOIN stany s ON s.Id = h.Id_IO left JOIN pwm p ON p.Id = h.Id_Pwm left JOIN lancuchy l ON l.Id = h.Id_c where Czas between ? and ? order by Czas DESC", (datalist[2], datalist[3]))
            reply = 'true;HR_selByCat;'
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';' + \
                    str(row[2])+';'+str(row[3])+';'+str(row[4])+';'
        elif datalist[1] == 'SENSOR_history':
            cursor = conndb.execute("SELECT * from sensory s WHERE Id = ?", (datalist[2],))
            row = cursor.fetchone()
            reply = 'true;SENSOR_history;'+row[5]+";"
            cursor = conndb.execute("SELECT * from sensoryHistoria WHERE Id=? ORDER BY Timestamp DESC", (datalist[2],))
            for row in cursor:
                reply += str(row[1])+';'+str(row[2])+';'
        elif datalist[1] == 'SENSOR_refresh':
            reply = 'true;SENSOR_refresh;'+str(updateSensorHistory(datalist[2],conndb))+";"
        elif datalist[1] == 'SENSORS_history':
            reply = 'true;SENSORS_history;'
            cursor = conndb.execute("SELECT s.Id,s.Name,s.Unit,h.Timestamp,h.Value from sensoryHistoria h JOIN sensory s ON h.Id = s.Id  WHERE s.Id IN ("+datalist[2]+")  ORDER BY Timestamp DESC")
            for row in cursor:
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[4])+';'
        elif datalist[1] == 'LastVersion':
            jsonString = urllib2.urlopen("https://api.github.com/repos/arek125/remote-GPIO-control-server/releases/latest").read()
            lastRelease = json.loads(jsonString)
            reply = 'true;LastVersion;'+lastRelease['tag_name']+";"
        elif datalist[1] == 'ServerUpdateFromGH':
            try:
                jsonString = urllib2.urlopen("https://api.github.com/repos/arek125/remote-GPIO-control-server/releases/latest").read()
                lastRelease = json.loads(jsonString)
            except urllib2.URLError:
                log.error("Cannot update, no internet access ?")
                httpCode = 503
                reply = 'true;ServerUpdateFromGH;Cannot update, no internet access ?;'
            else:
                downURL = lastRelease['assets'][1]['browser_download_url']
                savedFile = open(os.getcwd()+"/rgc-server.tar.gz", 'w')
                savedFile.write(urllib2.urlopen(downURL).read())
                savedFile.close()
                import tarfile
                tar = tarfile.open(os.getcwd()+"/rgc-server.tar.gz")
                def members(tf):
                    l = len("rgc/")
                    for member in tf.getmembers():
                        if member.path.startswith("rgc/"):
                            member.path = member.path[l:]
                            yield member
                tar.extractall(members=members(tar))
                tar.close()
                os.system("systemctl restart rgc.service")
                reply = 'true;ServerUpdateFromGH;Update in progress...;'
        elif datalist[1] == 'GetMCL':
            with open('/lib/systemd/system/rgc.service') as search:
                for line in search:
                    line = line.rstrip()
                    if 'ExecStart=/usr/bin/python' in line:
                        reply = 'true;GetMCL;'+line.replace('ExecStart=/usr/bin/python','')+";"
        elif datalist[1] == 'UpdateMCL':
            import shutil
            with open('/lib/systemd/system/rgc.service') as input_file:
                with open('rgc.service', 'w') as temp_file:
                    for l in input_file:
                        if l.startswith('ExecStart'):
                            temp_file.write('ExecStart=/usr/bin/python ' + datalist[2]+'\n')
                        else:
                            temp_file.write(l)
            shutil.copy('rgc.service', '/lib/systemd/system/rgc.service')
            os.system("systemctl daemon-reload")
            os.system("systemctl restart rgc.service")
            reply = 'true;UpdateMCL;'
        else:
            reply = 'false;Conection OK, but no compabile method found, probably encryption error;'
            httpCode = 501
        conndb.commit()
    else:
        reply = 'false;Wrong password !;'
        httpCode = 401
    if debug: print "REPLY: "+reply
    if debug: print "SIZE: "+str(sys.getsizeof(reply))+"b"
    if PASSWORD != '' and passwalidation == True:
        reply = '1;'+encrypt(ENC_KEY, reply)+';'
    conndb.close()
    return (reply,httpCode)




class UDPRequestHandler(SocketServer.DatagramRequestHandler):
    def handle(self):
        if debug: print("THREAD:{} FOR USER:{}".format(threading.current_thread().name,self.client_address[0]))
        data = self.request[0].strip()
        if debug and PASSWORD: print 'RECIVED_ENC: '+data
        reply = requestMethod(data)[0]
        self.wfile.write(reply)

class TCPRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        data = ""
        while exitapp == False:
            line = self.rfile.readline().strip()
            data+=line
            if "#EOF#" in line: break
        if debug: print("THREAD:{} FOR USER:{}".format(threading.current_thread().name,self.client_address[0]))
        reply = requestMethod(data)[0]
        reply = zlib.compress(reply).encode('base64')
        if debug: print "SIZE: "+str(sys.getsizeof(reply))+"b"
        self.request.sendall(reply)

class HTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.path = '/www'+self.path
        parsedParams = urlparse.urlparse(self.path)
        if os.access('.' + os.sep + parsedParams.path, os.R_OK):
            SimpleHTTPRequestHandler.do_GET(self)
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            with open('www/index.html', 'r') as fin:
                self.copyfile(fin, self.wfile)

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        data = self.rfile.read(length)
        if data == 'authCheck':
            replyData = 'false' if PASSWORD=='' else 'true'
            self.send_response(200)
        else:
            reply = requestMethod(data)
            replyData = reply[0]
            self.send_response(reply[1]) #create header
        self.send_header("Content-Length", str(len(replyData)))
        self.end_headers()
        self.wfile.write(replyData) #send response

class ThreadedHTTPServer(SocketServer.ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


if __name__ == '__main__':
    print 'Server is starting...'
    print 'Please press Ctrl+C to end the program...'
    if '-db_path' in sys.argv:
        db_path = sys.argv[sys.argv.index('-db_path')+1]
    conndb = newDBConn()
    conndb.execute('PRAGMA journal_mode=wal')
    tableexist = conndb.execute(
        "SELECT * FROM sqlite_master WHERE name ='stany' and type='table';")
    if len(tableexist.fetchall()) == 0:
        print "Creating database..."
    else:
        cursor = conndb.execute('PRAGMA user_version')
        db_version = int(cursor.fetchone()[0])
        if db_version < 3:
            conndb.execute('ALTER TABLE historia ADD COLUMN Id_c INTEGER')

    conndb.execute('PRAGMA user_version={:d}'.format(CODE_VERSION))
    conndb.executescript('''CREATE TABLE IF NOT EXISTS `stany` (
            `Id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            `GPIO_BCM`    TEXT NOT NULL,
            `Stan`    INTEGER NOT NULL,
            `Name`    TEXT,
            `IN_OUT`    TEXT,
            `Edit_time`    TEXT,
            `Reverse`    INTEGER NOT NULL,
            `Bindid`    INTEGER,
            `Bindtype`    INTEGER
        );
        CREATE TABLE IF NOT EXISTS `pwm` (
            `Id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            `GPIO_BCM`	TEXT NOT NULL,
            `FR`	NUMERIC NOT NULL,
            `DC`	INTEGER NOT NULL,
            `SS`	INTEGER NOT NULL,
            `Name`	TEXT NOT NULL,
            `Reverse`	INTEGER NOT NULL,
            `Edit_time`    TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS `historia` (
            `Id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            `Czas`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `Typ`    TEXT,
            `Id_IO`    INTEGER,
            `Id_Pwm`    INTEGER,
            `Stan`    TEXT NOT NULL,
            `Id_c`    INTEGER
        );
        CREATE TABLE IF NOT EXISTS `sensory` (
            `Id`    TEXT NOT NULL PRIMARY KEY UNIQUE,
            `Name`    TEXT,
            `H_refresh_sec`    INTEGER NOT NULL DEFAULT 3600,
            `H_keep_days`    INTEGER NOT NULL DEFAULT 7,
            `Type`    TEXT NOT NULL,
            `Unit`    TEXT NOT NULL,
            `Model`    TEXT,
            `GPIO_BCM`    TEXT,
            `Data_name`    TEXT);
            CREATE TABLE IF NOT EXISTS `sensoryHistoria` (
            `Id`    TEXT NOT NULL,
            `Timestamp`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `Value`	NUMERIC NOT NULL
        );
        CREATE TABLE IF NOT EXISTS `akcje` (
            `Id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            `Typ`	TEXT NOT NULL,
            `Rodzaj`	INTEGER NOT NULL,
            `Koniunkcja`	TEXT,
            `Out_id`	NUMERIC,
            `Out_stan`	INTEGER,
            `Pwm_id`	INTEGER,
            `Pwm_fr`	INTEGER,
            `Pwm_dc`	INTEGER,
            `Pwm_ss`	INTEGER,
            `Nazwa`	TEXT,
            `Edit_time`	TEXT DEFAULT CURRENT_TIMESTAMP,
            `Chain_id`	INTEGER,
	        `Log`	INTEGER
        );
        CREATE TABLE IF NOT EXISTS `wyzwalaczeAkcji` (
            `Id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            `Id_a`	INTEGER NOT NULL,
            `Id_s`	TEXT,
            `Lp`	INTEGER NOT NULL,
            `Warunek`	TEXT NOT NULL,
            `Operator`	TEXT NOT NULL,
            `Dane`	TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS `lancuchy` (
            `Id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            `Status`	INTEGER NOT NULL DEFAULT 0,
            `Nazwa`	TEXT,
            `Edit_time`	TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS `spoiwaLancuchow` (
            `Id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            `Id_c`	INTEGER NOT NULL,
            `Lp`	INTEGER NOT NULL,
            `Dalay`	NUMERIC NOT NULL DEFAULT 1,
            `Typ`	TEXT NOT NULL,
            `A_id`	INTEGER,
            `Out_id`	NUMERIC,
            `Out_stan`	INTEGER,
            `Pwm_id`	INTEGER,
            `Pwm_fr`	INTEGER,
            `Pwm_dc`	INTEGER,
            `Pwm_ss`	INTEGER
        );
        ''')

    log.info('Server local time: '+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))
    startTime = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')

    i = 0
    sensorsInit = False
    for arg in sys.argv:
        if arg == '-port' or arg == '-mobileport':
            PORT = int(sys.argv[i+1])
        elif arg == '-wwwport':
            WWWPORT = int(sys.argv[i+1])
        elif arg == '-mode':
            MODE = sys.argv[i+1]
        elif arg == '-debug':
            debug = True
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
                    message = message + (bs - len(message) %
                                         bs) * chr(bs - len(message) % bs)
                    iv = Random.new().read(AES.block_size)
                    cipher = AES.new(key, AES.MODE_CBC, iv)
                    s = base64.b64encode(iv + cipher.encrypt(message))
                except:
                    s = "error"
                return s

            def decrypt(key, enc_message):
                try:
                    enc_message = base64.b64decode(enc_message)
                    iv = enc_message[:AES.block_size]
                    cipher = AES.new(key, AES.MODE_CBC, iv)
                    s = cipher.decrypt(enc_message[AES.block_size:])
                    s = s[:-ord(s[len(s)-1:])]
                except:
                    s = "error"
                return s
        elif arg == '-ds18b20':
            from ds18b20 import DS18B20
            DS = DS18B20()
            if DS.device_count() == 0:
                log.error("ds18b20 devices not detected")
            else:
                j = 0
                while j < DS.device_count():
                    conndb.execute("INSERT OR IGNORE INTO sensory(Id,Type,Unit,Data_name) VALUES(?,?,?,?)", (
                        DS.device_name(j), "ds18b20", "C", "temperature"))
                    j += 1
                conndb.commit()
        elif arg == '-dht':
            import Adafruit_DHT
            humidity, temperature = Adafruit_DHT.read_retry(
                int(sys.argv[i+1]), int(sys.argv[i+2]))
            if humidity is not None and temperature is not None:
                conndb.execute("INSERT OR IGNORE INTO sensory(Id,Type,Unit,Model,GPIO_BCM,Data_name) VALUES(?,?,?,?,?,?)", (
                    "DHT_"+sys.argv[i+1]+"_"+sys.argv[i+2]+"_T", "dht", "C", sys.argv[i+1], sys.argv[i+2], "temperature"))
                conndb.execute("INSERT OR IGNORE INTO sensory(Id,Type,Unit,Model,GPIO_BCM,Data_name) VALUES(?,?,?,?,?,?)", (
                    "DHT_"+sys.argv[i+1]+"_"+sys.argv[i+2]+"_H", "dht", "%", sys.argv[i+1], sys.argv[i+2], "humidity"))
                conndb.commit()
            else:
                log.error('DHT'+sys.argv[i+1]+" at pin:" +
                          sys.argv[i+2]+" not readable !")
        elif arg == '-tsl2561':
            from Adafruit_TSL2561 import Adafruit_TSL2561
            TSL = Adafruit_TSL2561()
            gain = stringToint(sys.argv[i+1])
            if gain <= 16 and gain > 0: TSL.set_gain(gain)
            else: TSL.enable_auto_gain(True)
            conndb.execute("INSERT OR IGNORE INTO sensory(Id,Type,Unit,Model,Data_name) VALUES(?,?,?,?,?)", (
                "I2C_0x39", "tsl2561", "lx", sys.argv[i+1], "illumination"))
            conndb.commit()

        i = i+1
    if ("-ds18b20" in sys.argv or "-dht" in sys.argv or "-tsl2561" in sys.argv) and not sensorsInit:
        sensorsInit = True
        sensors_timers = {}
        sensors_timers_const = {}

        def updateSensorHistory(id,cdb):
            cursor = cdb.execute("SELECT * from sensory s WHERE Id = ?", (id,))
            row = cursor.fetchone()
            value = getCurrentSensorValue(id,cdb)
            if value != -999:
                cdb.execute("INSERT INTO sensoryHistoria(Id,Value) VALUES(?,?)",
                                (row[0], value))
            cdb.commit()
            return value

        def getCurrentSensorValue(id,cdb):
            cursor = cdb.execute("SELECT * from sensory s WHERE Id = ?", (id,))
            row = cursor.fetchone()
            try:
                if row[4] == 'ds18b20':
                    return DS.tempC_byDeviceName(row[0])
                elif row[4] == 'dht':
                    if row[8] == 'temperature':
                        return Adafruit_DHT.read_retry(int(row[6]), int(row[7]))[1]
                    elif row[8] == 'humidity':
                        return Adafruit_DHT.read_retry(int(row[6]), int(row[7]))[0]
                elif row[4] == 'tsl2561':
                    return TSL.calculate_lux()
            except Exception as e:
                log.error("Error: "+e.message)
                return -999

        def sensorLoop(conndb3):
            if exitapp == False:
                c_sensors = conndb3.execute("SELECT * from sensory s")
                for row in c_sensors:
                    if row[0] in sensors_timers and int(row[2]) > 0:
                        if sensors_timers_const[row[0]] != int(row[2]):
                            sensors_timers[row[0]] = int(row[2])
                            sensors_timers_const[row[0]] = int(row[2])
                        elif sensors_timers[row[0]] <= 0:
                            sensors_timers[row[0]] = int(row[2])
                            updateSensorHistory(row[0],conndb3)
                            if int(row[3]) > 0:
                                conndb3.execute("DELETE from sensoryHistoria WHERE Timestamp < datetime('now', '-"+str(
                                    row[3])+" day') AND Id = '"+str(row[0])+"';")
                                conndb3.commit()
                        else:
                            sensors_timers[row[0]] -= 1
                    else:
                        sensors_timers[row[0]] = int(row[2])
                        sensors_timers_const[row[0]] = int(row[2])

    cursor1 = conndb.execute(
        "SELECT * from stany where IN_OUT like 'out' order by Edit_time ASC")
    for row in cursor1:
        log.info('OUTPUT: GPIO='+str(row[1])+' STATE='+str(row[2]))
        GPIOset(row[1], row[2]) if not row[8] else GPIOset(
            row[1], 0 if not row[6] else 1)

    cursor1 = conndb.execute("SELECT * from pwm")
    for row in cursor1:
        log.info('OUTPUT PWM: GPIO=' +
                 str(row[1])+' S/S='+str(row[4]) +
                 ' FR='+str(row[2])+' DC='+str(row[3]))
        pwmpins = row[1].split(",")
        for pin in pwmpins:
            pwm[pin] = GPIOPWM(int(pin), float(row[2]))
            if row[4] == 1:
                pwm[pin].start(int(row[3]))

    serverUDP = SocketServer.ThreadingUDPServer((HOST,PORT), UDPRequestHandler)
    serverUDP.max_packet_size = 8192*4
    serverUDP.allow_reuse_address = True
    serverUDP_thread = threading.Thread(target=serverUDP.serve_forever)
    serverUDP_thread.daemon = True
    serverTCP = SocketServer.ThreadingTCPServer((HOST, PORT),TCPRequestHandler)
    serverTCP.allow_reuse_address = True
    serverTCP_thread = threading.Thread(target=serverTCP.serve_forever)
    serverTCP_thread.daemon = True
    serverHTTP = ThreadedHTTPServer(('', WWWPORT), HTTPRequestHandler)
    serverHTTP.allow_reuse_address = True
    serverHTTP_thread = threading.Thread(target=serverHTTP.serve_forever)
    serverHTTP_thread.daemon = True

    import signal
    services_th = threading.Thread(target=services)
    services_th.daemon = True
    services_th.start()
    cursor = conndb.execute("SELECT * from stany where IN_OUT like 'in'")
    for row in cursor:
        log.info('INPUT: GPIO='+str(row[1])+' STATE='+str(row[2]))
        if row[8] == 1:
            threading.Thread(target=inputLoop2, args=(
                row[7], row[0], row[1], row[2], row[6])).start()
        elif row[8] == 2:
            threading.Thread(target=inputLoop3, args=(
                row[0], row[1], row[2], row[6], row[7])).start()
        else:
            threading.Thread(target=inputLoop4, args=(
                row[0], row[1], row[2], row[6])).start()
    if MODE != 'wwwOnly':
        serverUDP_thread.start()
        serverTCP_thread.start()
    if MODE != 'mobileOnly':
        serverHTTP_thread.start()
    if sensorsInit:
        cursor = conndb.execute("SELECT * from sensory s")
        for row in cursor: updateSensorHistory(row[0],conndb)
    conndb.close()
    def handler_stop_signals(signum, frame):
        print "...Ending..."
        serverUDP.shutdown()
        serverUDP.server_close()
        serverUDP_thread.join()
        serverTCP.shutdown()
        serverTCP.server_close()
        serverTCP_thread.join()
        serverHTTP.shutdown()
        serverHTTP.server_close()
        serverHTTP_thread.join()
        GPIO.cleanup()
        global exitapp
        exitapp = True

    signal.signal(signal.SIGINT, handler_stop_signals)
    signal.signal(signal.SIGTERM, handler_stop_signals)

    while not exitapp:
        time.sleep(1)
