import SocketServer
import socket
import sys
import hashlib
from datetime import datetime
import _strptime
import os
import signal
import glob
import sqlite3
import threading
import time
import OPi.GPIO as GPIO
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
import subprocess
log = logging.getLogger('demo')
log.addHandler(JournalHandler())
log.setLevel(logging.INFO)
import base64
from Crypto import Random
from Crypto.Cipher import AES
import multiprocessing
import psycopg2
from psycopg2.extras import DictCursor
from ConfigParser import SafeConfigParser
import psutil
import traceback

def encrypt(key, message):
    try:
        bs = 16
        message = message + (bs - len(message) % bs) * chr(bs - len(message) % bs)
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

HOST = ''
parser = SafeConfigParser()
parser.read('rgc-config.ini')
PASSWORD = ''
MODE = parser.get('main','mode')
ENC_KEY = ''
CODE_VERSION = 8
TAG_VERSION = 3.4
startTime = None
DS = None
TSL = None
pwm = {k: [] for k in range(2)}
RF_TX_BCM = 0
RF_RX_BCM = 0
RANGE_SENSORS = {}
RE_COUNTERS = {}
GPIO_EVENTS_PINS = []
debug = parser.getboolean('main','debug')
strptime = datetime.strptime
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
exit_event = multiprocessing.Event()
doRestartAfterReply = -1
pms7003 = None

running_proceses = []
mesured_proceses = {}
def services():
    conn, conndbth = newDBConnP()
    global exit_event
    while not exit_event.is_set():
        conndbth.execute("SELECT * FROM akcje where Rodzaj > 0 OR Rodzaj = -1")
        rows = conndbth.fetchall()
        for row in rows:
            isRunning = False
            if row[17]:
                #if psutil.pid_exists(row[17]):
                if any(p.pid == row[17] for p in running_proceses):
                    isRunning = True
                #print row[10]+str(isRunning)+str(row[17])
            conndbth.execute("SELECT Id FROM wyzwalaczeAkcji WHERE Id_a = %s AND Warunek = 'in chain'",(str(row[0]),))
            rowChain = conndbth.fetchone()
            if not isRunning and rowChain is None: 
                p1 = multiprocessing.Process(target=action, args=(row[0],))
                p1.daemon = True
                p1.start()
                running_proceses.append(p1)
                conndbth.execute("UPDATE akcje set Pid=%s where Id=%s", (str(p1.pid),row[0]))
                time.sleep(0.01)
            elif rowChain is None and isRunning:
                try: pu = mesured_proceses[row[17]]
                except KeyError: mesured_proceses[row[17]] = pu = psutil.Process(row[17])
                cpuUsage = pu.cpu_percent()/psutil.cpu_count()
                conndbth.execute("UPDATE akcje set Cpu_usage=%s where Id=%s", (str(cpuUsage),row[0]))
        for p in running_proceses:
            #print str(p.pid)+str(p.is_alive())
            if not p.is_alive():running_proceses.remove(p)
        time.sleep(5)
    conndbth.close()
    conn.close()
    


def action(id,idCE = 0,changedBy="scheduled"):
    updateCD = 30
    startTime = time.time()
    trigger_timer = {}
    conn, conndb4 = newDBConnP()
    log = logging.getLogger('demo')
    log.addHandler(JournalHandler())
    log.setLevel(logging.ERROR)
    proc = multiprocessing.current_process()
    global exit_event
    while not exit_event.is_set():
        try:
            conndb4.execute("SELECT * FROM akcje WHERE Id = %s",(id,))
            row = conndb4.fetchone()
            if row is None: sys.exit()
            conndb4.execute("SELECT * FROM wyzwalaczeAkcji w left join sensory s on w.Id_s = s.Id left join stany st on w.Id_s = CAST(st.Id AS TEXT) left join pwm p on w.Id_s = CAST(p.Id AS TEXT) left join rf r on w.Id_s=CAST(r.Id AS TEXT) left join globalVariables v on w.Id_s=CAST(v.Id AS TEXT) WHERE w.Id_a = %s ORDER BY w.Lp",(row[0],))
            conditions = []
            conditionsLog = []
            conditionString = ''
            conditionStringLog = ''
            triggers = []
            for rowW in conndb4.fetchall():
                triggers.append(rowW[4])
                if rowW[4] == 'date':
                    conditions.append(eval("strptime('"+rowW[6]+"','%Y-%m-%d %H:%M')"+rowW[5]+"datetime.utcnow().replace(microsecond=0,second=0)"))
                    conditionsLog.append(rowW[4]+":"+rowW[6]+rowW[5]+datetime.utcnow().replace(microsecond=0,second=0).strftime('%Y-%m-%d %H:%M'))
                elif rowW[4] == 'hour':
                    triggerHour = datetime.strptime(rowW[6],'%H:%M')
                    currentHour = datetime.utcnow().replace(1900,1,1,microsecond=0,second=0)
                    conditions.append(eval('triggerHour'+rowW[5]+'currentHour'))
                    conditionsLog.append(rowW[4]+":"+triggerHour.strftime('%H:%M')+rowW[5]+currentHour.strftime('%H:%M'))
                elif rowW[4] == 'timer':
                    timelist = rowW[6].split(",")
                    if rowW[0] not in trigger_timer or trigger_timer[rowW[0]][0] != int(timelist[0])*1000:
                        trigger_timer[rowW[0]] = (int(timelist[0])*1000,int(timelist[1])*1000,int(round(time.time()*1000)))
                    timeS = trigger_timer[rowW[0]][1] - (int(round(time.time()*1000)) - trigger_timer[rowW[0]][2])
                    conditions.append(timeS <= 0)
                    conditionsLog.append(rowW[4]+":"+str(timeS) +'<=0')
                    if timeS > 0:
                        trigger_timer[rowW[0]] =(trigger_timer[rowW[0]][0],timeS,int(round(time.time()*1000)))
                        if updateCD <= 0:
                            conndb4.execute("UPDATE wyzwalaczeAkcji set Dane=%s where Id=%s", (str(trigger_timer[rowW[0]][0]/1000)+','+str(timeS/1000), rowW[0]))
                    else:
                        trigger_timer[rowW[0]] = (trigger_timer[rowW[0]][0],trigger_timer[rowW[0]][0],int(round(time.time()*1000)))
                elif rowW[4] == 'sensor':
                    sensorValue = getCurrentSensorValue(rowW[2],conndb4)
                    if sensorValue != None: 
                        conditions.append(eval(str(sensorValue)+rowW[5]+rowW[6]))
                        conditionsLog.append(rowW[4]+":"+str(sensorValue)+rowW[5]+rowW[6])
                    else: conditions.append(False)
                elif rowW[4] == 'weekday':
                    conditions.append(eval("datetime.now().weekday()"+rowW[5]+rowW[6]))
                    conditionsLog.append(rowW[4]+":"+str(datetime.now().weekday())+rowW[5]+rowW[6])
                elif rowW[4] == 'i/o':
                    planned = int(rowW[6])
                    cState = int(rowW[21])
                    reverse = int(rowW[25])
                    conditions.append(True if ((planned==cState and not reverse) or (planned==2 and planned==cState) or (planned!=cState and reverse and planned!=2)) else False)
                    conditionsLog.append("State equals" if ((planned==cState and not reverse) or (planned==2 and planned==cState) or (planned!=cState and reverse and planned!=2)) else "State not equals")
                elif rowW[4] == 'pwm state':
                    conditions.append(int(rowW[6]) == int(rowW[32]))
                    conditionsLog.append("State equals" if (int(rowW[6]) == int(rowW[32])) else "State not equals")
                elif rowW[4] == 'pwm fr':
                    conditions.append(eval(str(rowW[30])+rowW[5]+rowW[6]) and int(rowW[32] == 1))
                    conditionsLog.append(rowW[4]+":"+str(rowW[30])+"Hz"+rowW[5]+rowW[6]+"Hz")
                elif rowW[4] == 'pwm dc':
                    conditions.append(eval(str(rowW[31])+rowW[5]+rowW[6]) and int(rowW[32] == 1))
                    conditionsLog.append(rowW[4]+":"+str(rowW[31])+"%"+rowW[5]+rowW[6]+"%")
                elif rowW[4] == 'in chain':
                    conditions.append(eval(rowW[6]+rowW[5]+str(idCE != 0)))
                    conditionsLog.append('In chain run')
                elif rowW[4] == 'ping':
                    response = os.system("ping -c 1 -w 2 -t 2 "+rowW[2]+" > /dev/null 2>&1")
                    if response == 0: isPinging = True
                    else: isPinging = False
                    conditions.append(eval(rowW[6]+rowW[5]+str(isPinging)))
                    conditionsLog.append(rowW[2]+rowW[6]+rowW[5]+'Pinging:'+str(isPinging))
                elif rowW[4] == 'rfrecived':
                    conndb4.execute("select h.Id from rfHistoria h left join rf r on h.Id = r.Id where Type LIKE 'Recive' and Timestamp >= %s and h.Id = %s",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),rowW[2]))
                    conditions.append(eval(rowW[6]+rowW[5]+str(bool(conndb4.rowcount))))
                    conditionsLog.append(rowW[4]+":"+rowW[6]+rowW[5]+str(bool(conndb4.rowcount)))
                elif rowW[4] == 'cmd':
                    execCmd = execCustomCmd(conndb4,rowW[2],changedBy,False,True)
                    if execCmd[0]: 
                        conditions.append(eval(str(execCmd[1]).rstrip()+rowW[5]+rowW[6]))
                        conditionsLog.append(rowW[4]+":"+str(execCmd[1]).rstrip()+rowW[5]+rowW[6])
                    else: conditions.append(False)
                elif rowW[4] == 'var':
                    if rowW[47] == "String": conditions.append(eval("'"+str(rowW[46])+"'"+rowW[5]+"'"+str(rowW[6])+"'"))
                    elif rowW[47] == "Date": conditions.append(eval("strptime('"+rowW[46]+"','%Y-%m-%d %H:%M')"+rowW[5]+"strptime('"+rowW[6]+"','%Y-%m-%d %H:%M')"))
                    elif rowW[47] == "Time":
                        triggerHour = datetime.strptime(rowW[6],'%H:%M')
                        varHour = datetime.strptime(rowW[46],'%H:%M')
                        conditions.append(eval('varHour'+rowW[5]+'triggerHour'))
                    else: conditions.append(eval(str(rowW[46])+rowW[5]+rowW[6]))
                    conditionsLog.append(rowW[4]+":"+str(rowW[46])+rowW[5]+rowW[6])
                elif rowW[4] == 'i/o link':
                    res = callLinkedPi(rowW[7],'Get_GPIO;'+rowW[2],conndb4)
                    # print res
                    if res:
                        planned = int(rowW[6])
                        cState = int(res[4])
                        reverse = int(res[8])
                        conditions.append(True if ((planned==cState and not reverse) or (planned==2 and planned==cState) or (planned!=cState and reverse and planned!=2)) else False)
                        conditionsLog.append(rowW[4]+":"+"State equals" if ((planned==cState and not reverse) or (planned==2 and planned==cState) or (planned!=cState and reverse and planned!=2)) else "State not equals")
                    else: conditions.append(False)
                elif rowW[4] == 'sensor link':
                    res = callLinkedPi(rowW[7],'SENSOR_value;'+rowW[2],conndb4,1)
                    if res:
                        conditions.append(eval(res[2]+rowW[5]+rowW[6]))
                        conditionsLog.append(rowW[4]+":"+res[2]+rowW[5]+rowW[6])
                    else: conditions.append(False)
                elif rowW[4] == 'rfrecived link':
                    res = callLinkedPi(rowW[7],'GetRfRecivedNow;'+rowW[2],conndb4,1)
                    if res:
                        conditions.append(eval(rowW[6]+rowW[5]+str(bool(int(res[2])))))
                        conditionsLog.append(rowW[4]+":"+rowW[6]+rowW[5]+str(bool(int(res[2]))))
                    else: conditions.append(False)
                elif rowW[4] == 'var link':
                    res = callLinkedPi(rowW[7],'GetGlobalVar;'+rowW[2],conndb4,1)
                    if res:
                        if res[3] == 'String': conditions.append(eval("'"+str(res[2])+"'"+rowW[5]+"'"+str(rowW[6])+"'"))
                        elif res[3] == "Date": conditions.append(eval("strptime('"+res[2]+"','%Y-%m-%d %H:%M')"+rowW[5]+"strptime('"+rowW[6]+"','%Y-%m-%d %H:%M')"))
                        elif res[3] == "Time":
                            triggerHour = datetime.strptime(rowW[6],'%H:%M')
                            varHour = datetime.strptime(res[2],'%H:%M')
                            conditions.append(eval('varHour'+rowW[5]+'triggerHour'))
                        else: conditions.append(eval(res[2]+rowW[5]+rowW[6]))
                        conditionsLog.append(rowW[4]+":"+str(rowW[46])+rowW[5]+rowW[6])
                    else: conditions.append(False)
            # print str(id)+str(conditions)
            if len(conditions) > 0:
                if row[3] == None or not row[3]:
                    i=1
                    for cond in conditions:
                        if len(conditions)==i:
                            conditionString+=str(cond)
                        else:
                            conditionString+=str(cond)+" and "
                        i+=1
                    i=1
                    for cond in conditionsLog:
                        if len(conditionsLog)==i:
                            conditionStringLog+=str(cond)
                        else:
                            conditionStringLog+=str(cond)+" and "
                        i+=1
                else:
                    i=1
                    conditionString = row[3]
                    for cond in conditions:
                        conditionString = re.sub('#'+str(i)+'#', str(cond), conditionString)
                        i+=1
                    i=1
                    conditionStringLog = row[3]
                    for cond in conditionsLog:
                        conditionStringLog = re.sub('#'+str(i)+'#', str(cond), conditionStringLog)
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
                        lastExecTime = strptime(row[11],'%Y-%m-%d %H:%M:%S.%f').replace(microsecond=0,second=0)
                        currentTime = datetime.utcnow().replace(microsecond=0,second=0)
                        isThereTimeTrigger = False
                        if ('date' in triggers or 'hour' in triggers) and 'cmd' not in triggers and 'sensors' not in triggers and 'rfrecived' not in triggers:
                            isThereTimeTrigger = True
                        if (row[1] == 'output' and not isThereTimeTrigger) or (row[1] == 'output' and isThereTimeTrigger and lastExecTime != currentTime):
                            execuded = outputChange(int(row[5]),row[4],conndb4,changedBy,True if row[13] else False)
                        elif (row[1] == 'pwm' and not isThereTimeTrigger) or (row[1] == 'pwm' and isThereTimeTrigger and lastExecTime != currentTime):
                            execuded = pwmChange(row[9],row[8],row[7],row[6],conndb4,changedBy,True if row[13] else False)
                        elif (row[1] == 'chain' and not isThereTimeTrigger) or (row[1] == 'chain' and isThereTimeTrigger and lastExecTime != currentTime):
                            #if int(row[5]): threading.Thread(target=chainExecude, args=(row[12], changedBy, True if row[13] else False)).start()
                            if int(row[5]): chainExecude(row[12],changedBy, True if row[13] else False)
                            else: conndb4.execute("UPDATE lancuchy set Status=0 WHERE Id=%s",(row[12],))
                            execuded = True
                        elif (row[1] == 'rfsend' and not isThereTimeTrigger) or (row[1] == 'rfsend' and isThereTimeTrigger and lastExecTime != currentTime):
                            sendRfCode(conndb4,row[14],False,True if row[13] else False)
                            execuded = True
                        elif (row[1] == 'cmd' and not isThereTimeTrigger) or (row[1] == 'cmd' and isThereTimeTrigger and lastExecTime != currentTime):
                            execCustomCmd(conndb4,row[16],changedBy,True if row[13] else False)
                            execuded = True
                        elif (row[1] == 'var' and not isThereTimeTrigger) or (row[1] == 'var' and isThereTimeTrigger and lastExecTime != currentTime):
                            conndb4.execute("UPDATE globalVariables set Val=%s,Timestamp=%s where Id=%s",(str(row[20]),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(row[19])))
                            execuded = True
                        elif (row[1] == 'action_noe' and not isThereTimeTrigger) or (row[1] == 'action_noe' and isThereTimeTrigger and lastExecTime != currentTime):
                            conndb4.execute("UPDATE akcje set Rodzaj=%s, Edit_time=%s where Id=%s", (str(row[22]), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(row[21])))
                            execuded = True
                        elif (row[1] == 'chain_ec' and not isThereTimeTrigger) or (row[1] == 'chain_ec' and isThereTimeTrigger and lastExecTime != currentTime):
                            conndb4.execute("Update lancuchy SET Edit_time=%s,ExecCountdown=%s WHERE Id=%s",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(row[23]),str(row[12])))
                            execuded = True
                        if noe > 0 and execuded:
                            conndb4.execute("UPDATE akcje set Rodzaj=%s,Edit_time=%s where Id = %s", (str(noe-1),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),row[0]))
                        elif execuded:
                            conndb4.execute("UPDATE akcje set Edit_time=%s where Id = %s", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),row[0]))
                        if execuded and row[13]: conndb4.execute("INSERT INTO historia(Typ, Id_a, Stan) VALUES(%s,%s,%s)", (conditionStringLog, str(row[0]), row[1]))
                        # conndb4.commit()
                elif noe <= 0: break
            if row[15] is not None: sleepTime = float(row[15])
            else: sleepTime = 0.3
            if idCE != 0: break
            if updateCD <= 0: updateCD = 30
            updateCD -= (time.time()-startTime)
            startTime = time.time()
            time.sleep(sleepTime)
        except Exception as e:
            print e.message
            log.error(e.message)
            log.error(traceback.format_exc())
    conndb4.close()
    conn.close()
    sys.exit()


def chainExecude(id,changedBy,log=True):
    conn, conndb = newDBConnP()
    def cancelIf():
        conndb.execute("SELECT Status from lancuchy WHERE Id=%s",(id,))
        row1 = conndb.fetchone()
        if row1[0] == 0: sys.exit()
    conndb.execute("SELECT * FROM spoiwaLancuchow s WHERE Id_c = %s ORDER BY Lp",(id,))
    chainBonds = conndb.fetchall()
    conndb.execute("SELECT Status,ExecCountdown from lancuchy WHERE Id=%s",(id,))
    sRow = conndb.fetchone()
    status = int(sRow[0])
    countdown = int(sRow[1])
    if status == 0:
        while (countdown > 0 or countdown == -1) and not exit_event.is_set():
            for row in chainBonds:
                if log and status == 0: conndb.execute("INSERT INTO historia(Typ, Id_c, Stan) VALUES(%s,%s,%s)", (changedBy, id, "START"))
                status = row[2]
                conndb.execute("UPDATE lancuchy SET Status=%s,Edit_time=%s WHERE Id=%s",(row[2],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),id))
                daley = float(row[3])
                while daley > 0 and not exit_event.is_set():
                    start_time = time.time()
                    cancelIf()
                    time.sleep(1)
                    daley = daley-(time.time() - start_time)
                cancelIf()
                if row[4] == 'output':
                    if row[14]: callLinkedPi(row[14],'outputChange;'+str(row[7])+';'+str(row[6])+';'+str(int(log))+';'+changedBy,conndb,15)
                    else: outputChange(int(row[7]),row[6],conndb,changedBy,log)
                elif row[4] == 'pwm':
                    if row[14]: callLinkedPi(row[14],'GPIO_PFRDC;'+str(row[8])+';0;'+str(row[9])+';'+str(row[10])+';0;'+str(row[11])+';'+str(int(log))+';'+changedBy,conndb,15)
                    else: pwmChange(row[11],row[10],row[9],row[8],conndb,changedBy,log)
                elif row[4] == 'action':
                    if row[14]: callLinkedPi(row[14],'ActionCheck;'+str(row[5])+';'+changedBy,conndb,15)
                    else: action(row[5],int(id),changedBy)
                elif row[4] == 'rfsend':
                    if row[14]: callLinkedPi(row[14],'SendRfCode;'+str(row[12])+';'+str(int(log))+';'+changedBy,conndb,15)
                    else: sendRfCode(conndb,row[12],False,log)
                elif row[4] == 'cmd':
                    if row[14]: callLinkedPi(row[14],'ExecCustomCmd;'+str(row[13])+';0;'+changedBy+';'+str(int(log)),conndb,15)
                    else: execCustomCmd(conndb,row[13],changedBy,log)
                elif row[4] == 'chain':
                    if int(row[7]) and row[14]: callLinkedPi(row[14],'GPIO_ChainExecute;'+str(row[16])+';'+changedBy,conndb,15)
                    elif int(row[7]) and not row[14]: chainExecude(row[16],changedBy,log)
                    elif not int(row[7]) and row[14]: callLinkedPi(row[14],'GPIO_ChainCancel;'+str(row[16])+';'+changedBy,conndb,15)
                    else: conndb.execute("UPDATE lancuchy set Status=0 WHERE Id=%s",(row[12],))
                elif row[4] == 'var':
                    if row[14]: callLinkedPi(row[14],'SetGlobalVar;'+str(row[17])+';'+str(row[18])+';'+changedBy+';'+str(int(log)),conndb,15)
                    else: conndb.execute("UPDATE globalVariables set Val=%s,Timestamp=%s where Id=%s",(str(row[18]),datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(row[17])))
                elif row[4] == 'action_noe':
                    if row[14]: callLinkedPi(row[14],'SetActionNOE;'+str(row[5])+';'+str(row[19])+';'+changedBy+';'+str(int(log)),conndb,15)
                    else: conndb.execute("UPDATE akcje set Rodzaj=%s, Edit_time=%s where Id=%s", (str(row[19]), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(row[5])))
                elif row[4] == 'chain_ec':
                    if row[14]: callLinkedPi(row[14],'SetChainEC;'+str(row[16])+';'+str(row[20])+';'+changedBy+';'+str(int(log)),conndb,15)
                    else: conndb.execute("Update lancuchy SET Edit_time=%s,ExecCountdown=%s WHERE Id=%s",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),str(row[20]),str(row[16])))
                if (len(chainBonds)) == row[2] and countdown == 1:
                    conndb.execute("UPDATE lancuchy SET Status=%s,Edit_time=%s WHERE Id=%s",(0,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),id))
                    if log: conndb.execute("INSERT INTO historia(Typ, Id_c, Stan) VALUES(%s,%s,%s)", (changedBy, id, "END"))
            if countdown != -1: countdown -= 1
    conndb.close()
    conn.close()

def execCustomCmd(conndb,id,changedBy,log=True,disableThreading=False):
    def afterExec(cmdProcess,inThread=False):
        output, errors = cmdProcess.communicate()
        if cmdProcess.returncode: 
            log.error(errors)
            return (False,errors)
        else: 
            if log: 
                conndb.execute("INSERT INTO Historia(Typ, Stan, Id_cmd) VALUES(%s,%s,%s)", (changedBy,output,id))
            return (True,output)
    conndb.execute("SELECT * from customCmds WHERE Id = %s", (id,))
    row = conndb.fetchone()
    cmdProcess = subprocess.Popen(row[2], stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=4096, shell=True)
    if row[3] or disableThreading: return afterExec(cmdProcess)
    else: 
        threading.Thread(target=afterExec, args=(cmdProcess,True)).start()
        return (True,'Exec started')
            
def outputChange(plannedState,id,cdb,changedBy,log=True):
    cdb.execute("SELECT * FROM Stany WHERE Id=%s",(id,))
    row = cdb.fetchone()
    currentState = int(row[2])
    Reverse = int(row[6])
    GPIO_BCM = row[1]
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
            cdb.execute("UPDATE stany set Stan =2,Edit_time=%s where (GPIO_BCM like %s and Id!=%s and IN_OUT like 'out') or (GPIO_BCM like %s and Id!=%s and IN_OUT like 'out');", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), "%"+gpio+",%", id, "%,"+gpio+"%", id))
            cdb.execute("UPDATE stany set Stan =%s,Edit_time=%s where GPIO_BCM =%s and Id!=%s and IN_OUT like 'out' ;", (set, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), gpio, id))
        cdb.execute("UPDATE stany set Stan =%s, Edit_time=%s where Id=%s", (set, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), id))
        if log: cdb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)", (changedBy, id, "ON" if ((set and not Reverse) or (not set and Reverse)) else "OFF"))
        return True
    else: return False

def pwmChange(planed_ss,planned_dc,planned_fr,id,cdb,changedBy,log=True):
    cdb.execute("SELECT * FROM Pwm WHERE Id=%s",(id,))
    row = cdb.fetchone()
    current_ss = row[4]
    current_dc = row[3]
    current_fr = row[2]
    pwmpins = row[1].split(",")
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
        cdb.execute("UPDATE pwm set FR=%s,DC=%s,Edit_time=%s,SS=%s where Id=%s",(planned_fr if (planned_fr)else current_fr,planned_dc if (planned_dc)else current_dc, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), set, id))
        if log: cdb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(%s,%s,%s)", (changedBy, id, ("OFF" if set==0 else "ON")+":DC="+(str(planned_dc) if planned_dc else str(current_dc))+"%,FR="+(str(planned_fr) if planned_fr else str(current_fr))+"Hz"))
        if debug: print 'BY SHEDULED:'+str(id)+(" OFF" if set==0 else " ON")+":DC="+(str(planned_dc) if planned_dc else str(current_dc))+"%,FR="+(str(planned_fr) if planned_fr else str(current_fr))+"Hz"
        return True
    else: return False

def GPIOset(pinout, onoff):
    pins = pinout.split(",")
    try:
        onoff = int(onoff)
    except ValueError:
        print 'Failure w/ value ' + str(onoff)
    if onoff < 2:
        for pin in pins:
            pin = int(pin)
            GPIO.output(pin, onoff)

def GPIOInitOut(pinout):
    pins = pinout.split(",")
    for pin in pins:
        pin = int(pin)
        GPIO.setup(pin, GPIO.OUT)

def GPIOinputSet(inpin, resistor, method, id, stan, reverse, time):
    channel = int(inpin)
    if resistor == 1: GPIO.setup(channel, GPIO.IN, GPIO.PUD_UP)
    elif resistor == 2: GPIO.setup(channel, GPIO.IN, GPIO.PUD_DOWN)
    else: GPIO.setup(channel, GPIO.IN)
    if(method == 'ined'):
        cb = debounceHandler(channel, lambda channel, id=id, reverse=reverse: inputCallback(channel, id, reverse),bouncetime=200 if not time else int(time))
        cb.daemon = True
        cb.start()
        GPIO.add_event_detect(channel, GPIO.BOTH, callback=cb)
    else:
        p1 = multiprocessing.Process(target=inputLoop, args=(id, channel, stan, reverse, time))
        p1.daemon = True
        p1.start()
        running_proceses.append(p1)

def GPIOPWM(inpin, fr):
    GPIO.setup(inpin, GPIO.OUT)
    return GPIO.PWM(inpin, fr)

def inputCallback(channel, id, reverse):
    conn, conndb = newDBConnP()
    #print str(GPIO.input(channel))+';'+str(reverse)+';'+str(channel)
    if GPIO.input(channel):
        conndb.execute("UPDATE stany set Stan =0,Edit_time=%s where Id=%s", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(id)))
        conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)",("input", id, "ON" if reverse else "OFF"))
    else: 
        conndb.execute("UPDATE stany set Stan =1,Edit_time=%s where Id=%s", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(id)))
        conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)",("input", id, "ON" if (not reverse) else "OFF"))
    conndb.close()
    conn.close()

class debounceHandler(threading.Thread):
    def __init__(self, pin, func, edge='both', bouncetime=200):
        super(debounceHandler,self).__init__()
        self.edge = edge
        self.func = func
        self.pin = pin
        self.bouncetime = float(bouncetime)/1000
        self.lastpinval = GPIO.input(self.pin)
        self.lock = threading.Lock()

    def __call__(self, *args):
        if not self.lock.acquire():
            return
        t = threading.Timer(self.bouncetime, self.read, args=args)
        t.start()

    def read(self, *args):
        pinval = GPIO.input(self.pin)
        if (
                ((pinval == 0 and self.lastpinval == 1) and
                 (self.edge in ['falling', 'both'])) or
                ((pinval == 1 and self.lastpinval == 0) and
                 (self.edge in ['rising', 'both']))
        ):
            self.func(*args)
        self.lastpinval = pinval
        self.lock.release()


def inputLoop(id, inpin, Stan, reverse, SleepTime):
    def exitLoop(conn,conndb):
        conndb.close()
        conn.close()
        sys.exit()
    inpin = int(inpin)
    Stan = int(Stan)
    if Stan == 0: stan = 2
    elif Stan == 1: stan = 4
    else: stan = 2
    conn, conndb = newDBConnP()
    sleepTime = 0.05
    if SleepTime: 
        if float(SleepTime) > 0: sleepTime = float(SleepTime)/1000
    global exit_event
    while not exit_event.is_set():
        conndb.execute("SELECT id FROM stany WHERE Id = %s",(id,))
        row = conndb.fetchone()
        if row is None:
            exitLoop(conn, conndb)
        if stan == 2:
            if GPIO.input(inpin) == 0:
                conndb.execute("UPDATE stany set Stan =1,Edit_time=%s where Id=%s", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(id)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)",("input", id, "ON" if (not reverse) else "OFF"))
                stan = 4
        if stan == 4:
            if GPIO.input(inpin) == 1:
                conndb.execute("UPDATE stany set Stan =0,Edit_time=%s where Id=%s", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), str(id)))
                conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)",("input", id, "ON" if reverse else "OFF"))
                stan = 2
        time.sleep(sleepTime)
    exitLoop(conn,conndb)

def newDBConnP():
    connectionString = "dbname='{}' user='{}' host='{}' password='{}'".format(parser.get('postgresql','db'),parser.get('postgresql','user'),parser.get('postgresql','host'),parser.get('postgresql','password'))
    conn = psycopg2.connect(connectionString)
    conn.set_session(autocommit=True)
    cur = conn.cursor(cursor_factory=DictCursor)
    return conn,cur

def callLinkedPi(id,data,conndb,timeout=5):
    try:
        conndb.execute("SELECT * FROM linkedPis WHERE Id = %s",(id,))
        row = conndb.fetchone()
        if row[3]:
            L_PASSWORD = hashlib.sha256(row[3].encode()).hexdigest()
            L_ENC_KEY = hashlib.md5(row[3].encode()).hexdigest()
            data = L_PASSWORD+";"+encrypt(L_ENC_KEY, data+";"+os.uname()[1])
        else: data = "1;"+data+";"+os.uname()[1]
        if row[4] == 'UDP':
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.sendto(data, (row[2],row[5]))
            response = sock.recvfrom(1024)[0].split(';')
            sock.close()
        else:
            req = urllib2.Request(row[2], data, {'Content-Type': 'raw'})
            f = urllib2.urlopen(req, timeout = timeout)
            response = f.read().split(';')
            f.close()
        if response[0] == 'false': raise Exception(response[1])
        if row[3]: response = decrypt(L_ENC_KEY,response[1]).split(';')
        #print response
        return response
    except Exception as e:
        log.error(e)
        return False


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
    conn,conndb = newDBConnP()
    global doRestartAfterReply
    if passwalidation == True:
        if datalist[1] == 'version_check':
            reply = 'true;version_check;'+str(CODE_VERSION)+';'
        elif datalist[1] == 'GPIO_OEtime':
            cursor = conndb.execute("SELECT Max(Edit_time) FROM stany where IN_OUT like 'out'")
            for row in conndb.fetchall():
                reply = 'true;GPIO_OEtime;'+str(row[0])+';'
        elif datalist[1] == 'GPIO_Olist':
            cursor = conndb.execute("SELECT * from stany where IN_OUT like 'out' ORDER BY Id DESC")
            reply = 'true;GPIO_Olist;'
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2]) +';'+str(row[3])+';'+str(row[6])+';'+str(row[8])+';'
        elif datalist[1] == 'Get_GPIO':
            conndb.execute("SELECT * from stany where Id = %s",(datalist[2],))
            row = conndb.fetchone()
            reply = 'true;Get_GPIO;'+";".join(map(str, row))+";"
        elif datalist[1] == 'GPIO_OlistT0':
            cursor = conndb.execute("SELECT * from stany where IN_OUT like 'out' AND Bindtype = 0 ORDER BY Id DESC")
            reply = 'true;GPIO_OlistT0;'
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[6])+';'+str(row[8])+';'
        elif datalist[1] == 'Add_GPIO_out':
            conndb.execute("INSERT INTO stany VALUES (DEFAULT,%s,2,%s,'out',%s,%s,null,%s) RETURNING Id", (datalist[2], datalist[3], datalist[4], datalist[5], datalist[6]))
            idio = conndb.fetchone()[0]
            GPIOInitOut(datalist[2])
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)", (datalist[7], str(idio), "ADDED"))
            reply = 'true;Add_GPIO_out;'
        elif datalist[1] == 'Edit_GPIO_out':
            conndb.execute("UPDATE stany set Stan=2, GPIO_BCM=%s,Name=%s, Edit_time=%s, reverse=%s, Bindtype=%s where Id=%s", (
                datalist[3], datalist[4], datalist[5], datalist[6], datalist[8], datalist[2]))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)", (datalist[9], datalist[2], "EDITED"))
            pwmpins = datalist[3].split(',')
            pwmpins2 = datalist[7].split(',')
            for pin2 in pwmpins2:
                if pin2 not in pwmpins:
                    GPIO.cleanup(int(pin2))
            reply = 'true;Edit_GPIO_out;'
        elif datalist[1] == 'Delete_GPIO_out':
            conndb.execute("DELETE from stany where Id=%s", (datalist[2],))
            conndb.execute("UPDATE stany set Edit_time=%s where Id in (SELECT Id FROM stany LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            conndb.execute("DELETE from historia where Id_IO=%s", (datalist[2],))
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)",(datalist[5], datalist[2], datalist[4]+" DELETED"))
            conndb.execute("DELETE FROM spoiwaLancuchow WHERE Out_id=%s", (datalist[2],))
            r2 = conndb.rowcount
            if r2 > 0:
                conndb.execute("UPDATE lancuchy set Edit_time=%s where Id in (SELECT Id FROM lancuchy LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            conndb.execute("DELETE FROM akcje WHERE Out_id=%s", (datalist[2],))
            r3 = conndb.rowcount
            conndb.execute("DELETE FROM wyzwalaczeAkcji WHERE Id_s=%s AND Warunek = 'i/o'", (datalist[2],))
            r4 = conndb.rowcount
            if r3 > 0 or r4 > 0:
                conndb.execute("UPDATE akcje set Edit_time=%s where Id in (SELECT Id FROM akcje LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            pwmpins = datalist[3].split(",")
            for pin in pwmpins:
                GPIO.cleanup(int(pin))
            if datalist[4] == 'ined':
                GPIO.remove_event_detect(int(datalist[3]))
            reply = 'true;Delete_GPIO_out;'+datalist[2]+';'
        elif datalist[1] == 'GPIO_IEtime':
            cursor = conndb.execute("SELECT Max(Edit_time) FROM stany where IN_OUT like 'in%'")
            for row in conndb.fetchall():
                reply = 'true;GPIO_IEtime;'+str(row[0])+';'
        elif datalist[1] == 'GPIO_Ilist':
            cursor = conndb.execute("SELECT * from stany where IN_OUT like 'in%' ORDER BY Id DESC")
            reply = 'true;GPIO_Ilist;'
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[6])+';'+str(row[7])+';'+str(row[8])+';'+row[4]+';'
        elif datalist[1] == 'Add_GPIO_in':
            conndb.execute("INSERT INTO stany VALUES (DEFAULT,%s,0,%s,%s,%s,%s,%s,%s) RETURNING Id", (datalist[2], datalist[3],datalist[8], datalist[4], datalist[5], (float(datalist[6])*1000), datalist[7]))
            id = conndb.fetchone()[0]
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)", (datalist[9], str(id), "ADDED"))
            GPIOinputSet(datalist[2],1 if not datalist[7] else int(datalist[7]), datalist[8], id, 0, int(datalist[5]), (float(datalist[6])*1000))
            reply = 'true;Add_GPIO_in;'
        elif datalist[1] == 'Edit_GPIO_in':
            conndb.execute("DELETE from stany where Id=%s", (datalist[2],))
            conndb.execute("DELETE from historia where Id_IO=%s", (datalist[2],))
            conndb.execute("INSERT INTO stany VALUES (DEFAULT,%s,0,%s,%s,%s,%s,%s,%s) RETURNING Id", (datalist[3], datalist[4],datalist[10], datalist[5], datalist[6], (float(datalist[7])*1000), datalist[8]))
            id = conndb.fetchone()[0]
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)", (datalist[11], str(id), "EDITED"))
            if(datalist[10] == 'ined'): GPIO.remove_event_detect(int(datalist[9]))
            GPIO.cleanup(int(datalist[9]))
            GPIOinputSet(datalist[3],1 if not datalist[8] else int(datalist[8]), datalist[10], id, 0, int(datalist[6]), (float(datalist[7])*1000))
            reply = 'true;Edit_GPIO_in;'
        elif datalist[1] == 'GPIO_Oname':
            cursor = conndb.execute("SELECT Id,Name,GPIO_BCM,Reverse from stany where IN_OUT like 'out' ORDER BY Id DESC")
            reply = 'true;GPIO_Oname;'
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1]) +';'+str(row[2])+';'+str(row[3])+';'
        elif datalist[1] == 'GPIO_PEtime':
            cursor = conndb.execute("SELECT Max(Edit_time) FROM pwm")
            for row in conndb.fetchall():
                reply = 'true;GPIO_PEtime;'+str(row[0])+';'
        elif datalist[1] == 'GPIO_Plist':
            cursor = conndb.execute("SELECT * from pwm ORDER BY Id DESC")
            reply = 'true;GPIO_Plist;'
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[4])+';'+str(row[5])+';'+str(row[6])+';'
        elif datalist[1] == 'GPIO_PDC':
            pwmpins = datalist[3].split(",")
            for pin in pwmpins:
                pwm[pin].ChangeDutyCycle(int(datalist[4]))
            reply = 'true;GPIO_PDC;'+datalist[4]+';'
        elif datalist[1] == 'GPIO_PDCu':
            conndb.execute("UPDATE pwm set DC=%s,Edit_time=%s where Id=%s",(datalist[4], datalist[5], datalist[2]))
            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(%s,%s,%s)",(datalist[6], datalist[2], "DC="+datalist[4]+"%"))
            reply = 'true;GPIO_PDCu;'+datalist[4]+';'+datalist[5]+';'
        elif datalist[1] == 'GPIO_PFRDC':
            pwmChange(int(datalist[7]),int(datalist[5]),float(datalist[4]),datalist[2],conndb,datalist[9],bool(int(datalist[8])))
            reply = 'true;GPIO_PFRDC;' + datalist[4]+';'+datalist[6]+';'+datalist[5]+';'
        elif datalist[1] == 'GPIO_PSS':
            pwmpins = datalist[3].split(",")
            for pin in pwmpins:
                if datalist[6] == '1':
                    pwm[pin].start(int(datalist[4]))
                    pwm[pin].ChangeFrequency(float(datalist[7]))
                    conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(%s,%s,%s)", (datalist[8], datalist[2], "ON:DC="+datalist[4]+"%,FR="+datalist[7]+"Hz"))
                elif datalist[6] == '0':
                    pwm[pin].stop()
                    conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(%s,%s,%s)", (datalist[8], datalist[2], "OFF"))
            conndb.execute("UPDATE pwm set DC=%s,Edit_time=%s,SS=%s where Id=%s",(datalist[4], datalist[5], datalist[6], datalist[2]))
            reply = 'true;GPIO_PSS;' + datalist[4]+';'+datalist[5]+';'+datalist[6]+';'
        elif datalist[1] == 'Add_GPIO_pwm':
            pwmpins = datalist[2].split(',')
            for pin in pwmpins:
                pwm[pin] = GPIOPWM(int(pin), float(datalist[3]))
                pwm[pin].start(int(datalist[4]))
            conndb.execute("INSERT INTO pwm VALUES (DEFAULT,%s,%s,%s,1,%s,%s,%s) RETURNING Id", (datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datalist[7]))
            idpwm = conndb.fetchone()[0]
            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(%s,%s,%s)", (datalist[8], str(idpwm), "ADDED:DC="+datalist[4]+"%,FR="+datalist[3]+"Hz"))
            reply = 'true;Add_GPIO_pwm;'
        elif datalist[1] == 'Delete_GPIO_pwm':
            conndb.execute("DELETE from pwm where Id=%s", (datalist[2],))
            conndb.execute("DELETE from historia where Id_Pwm=%s", (datalist[2],))
            conndb.execute("UPDATE pwm set Edit_time=%s where Id in (SELECT Id FROM pwm LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(%s,%s,%s)",(datalist[5], datalist[2], datalist[4]+" DELETED"))
            conndb.execute("DELETE FROM spoiwaLancuchow WHERE Pwm_id=%s", (datalist[2],))
            r2 = conndb.rowcount
            if r2 > 0:
                conndb.execute("UPDATE lancuchy set Edit_time=%s where Id in (SELECT Id FROM lancuchy LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            conndb.execute("DELETE FROM akcje WHERE Pwm_id=%s", (datalist[2],))
            r3 = conndb.rowcount
            conndb.execute("DELETE FROM wyzwalaczeAkcji WHERE Id_s=%s AND Warunek LIKE 'pwm%%'", (datalist[2],))
            r4 = conndb.rowcount
            if r3 > 0 or r4 > 0:
                conndb.execute("UPDATE akcje set Edit_time=%s where Id in (SELECT Id FROM akcje LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
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
            conndb.execute("UPDATE pwm set GPIO_BCM=%s, FR=%s, DC=%s, SS=1, Name=%s, Reverse=%s, Edit_time=%s where Id=%s", (datalist[4], datalist[5], datalist[6], datalist[7], datalist[8], datalist[9], datalist[2]))
            conndb.execute("INSERT INTO historia(Typ, Id_Pwm, Stan) VALUES(%s,%s,%s)", (datalist[10], datalist[2], "EDITED:DC="+datalist[6]+"%,FR="+datalist[5]+"Hz"))
            reply = 'true;Edit_GPIO_pwm;'
        elif datalist[1] == 'Allpins_GPIO_pwm':
            reply = 'true;Allpins_GPIO_pwm;'
            cursor = conndb.execute("SELECT GPIO_BCM from pwm")
            for row in conndb.fetchall():
                pins = row[0].split(',')
                for pin in pins:
                    reply += pin+';'
        elif datalist[1] == 'Allpins_GPIO_out':
            reply = 'true;Allpins_GPIO_out;'
            cursor = conndb.execute("SELECT GPIO_BCM from stany where IN_OUT like 'out'")
            for row in conndb.fetchall():
                pins = str(row[0]).split(',')
                for pin in pins: reply += pin+';'
        elif datalist[1] == 'AllUsedPins_GPIO':
            reply = 'true;AllUsedPins_GPIO;'
            sqlExec ='''
                (SELECT GPIO_BCM from stany WHERE IN_OUT like 'out' AND Id != {id_out})
                UNION
                (SELECT GPIO_BCM from stany WHERE IN_OUT like 'in%' AND Id != {id_in}) 
                UNION
                (SELECT GPIO_BCM from pwm WHERE Id != {id_pwm})
                UNION
                (SELECT GPIO_BCM from sensory WHERE Id NOT LIKE '{id_s}')
            '''.format(id_out = datalist[3] if datalist[2] == 'out' else 0,id_in = datalist[3] if datalist[2] == 'in' else 0,id_pwm = datalist[3] if datalist[2] == 'pwm' else 0,id_s = datalist[3] if datalist[2] == 'sensor' else '')
            if datalist[2] == 'out': sqlExec = sqlExec.split("\n",3)[3]
            cursor = conndb.execute(sqlExec)
            for row in conndb.fetchall():
                pins = str(row[0]).split(',')
                for pin in pins: reply += pin+';'
        elif datalist[1] == 'Allpins_GPIO_in':
            reply = 'true;Allpins_GPIO_in;'
            cursor = conndb.execute("SELECT GPIO_BCM from stany where IN_OUT like 'in%'")
            for row in conndb.fetchall():
                reply += str(row[0])+';'
        elif datalist[1] == 'ActionCheck':
            action(datalist[2],1,datalist[3])
            reply = 'true;ActionCheck;'
        elif datalist[1] == 'outputChange':
            outputChange(int(datalist[2]),datalist[3],conndb,datalist[5],bool(int(datalist[4])))
            reply = 'true;outputChange;'
        elif datalist[1] == 'GPIO_set':
            GPIOset(datalist[3], datalist[4])
            reply = 'true;GPIO_set;'+datalist[4]+';'+datalist[5]+';'
            gpiolist = datalist[3].split(",")
            for gpio in gpiolist:
                conndb.execute("UPDATE stany set Stan =2,Edit_time=%s where (GPIO_BCM like %s and Id!=%s and IN_OUT like 'out') or (GPIO_BCM like %s and Id!=%s and IN_OUT like 'out');", (datalist[5], "%"+gpio+",%", datalist[2], "%,"+gpio+"%", datalist[2]))
                r1 = conndb.rowcount
                conndb.execute("UPDATE stany set Stan =%s,Edit_time=%s where GPIO_BCM =%s and Id!=%s and IN_OUT like 'out' ;", (datalist[4], datalist[5], gpio, datalist[2]))
                r2 = conndb.rowcount
            conndb.execute("UPDATE stany set Stan =%s,Edit_time=%s where Id=%s",(datalist[4], datalist[5], datalist[2]))
            stan = int(datalist[4])
            reverse = int(datalist[6])
            conndb.execute("INSERT INTO historia(Typ, Id_IO, Stan) VALUES(%s,%s,%s)", (datalist[7], datalist[2], "ON" if ((stan and not reverse) or (not stan and reverse)) else "OFF"))
            if r1 > 0 or r2 > 0:
                reply = 'true;GPIO_set;' +datalist[4]+';2000-01-01 00:00:00.000;'
        elif datalist[1] == 'GPIO_state':
            GPIO.setup(int(datalist[2]), GPIO.OUT)
            reply = 'true;GPIO_state;' + str(datalist[2])+';'+str(GPIO.input(int(pin)))+';'
        elif datalist[1] == 'HR_count':
            cursor = conndb.execute("SELECT COUNT(*) FROM historia where Czas between %s and %s", (datalist[2], datalist[3]))
            for row in conndb.fetchall(): reply = 'true;HR_count;'+str(row[0])+';'
        elif datalist[1] == 'SENSOR_list':
            reply = 'true;SENSOR_list;'
            cursor = conndb.execute("SELECT *,(SELECT Value from sensoryHistoria h WHERE h.Id=s.Id ORDER BY Timestamp DESC LIMIT 1),(SELECT Timestamp from sensoryHistoria h WHERE h.Id=s.Id ORDER BY Timestamp DESC LIMIT 1) from sensory s")
            for row in conndb.fetchall():
                reply += str(row[0])+";"+str(row[1])+";"+str(row[4])+";"+str(row[10])+";"+str(row[2])+";"+str(row[3])+";"+str(row[5])+";"+str(row[11])+";"+str(row[9])+";"+str(row[7])+";"+str(row[8])+";"
        elif datalist[1] == 'SENSOR_value':
            value = getCurrentSensorValue(datalist[2],conndb)
            if value == None: reply = 'false;SENSOR_value;'+str(value)+";"
            else: reply = 'true;SENSOR_value;'+str(value)+";"
        elif datalist[1] == 'SENSOR_names':
            reply = 'true;SENSOR_names;'
            cursor = conndb.execute("SELECT * from sensory ORDER BY Id DESC")
            for row in conndb.fetchall():
                reply += str(row[0])+";"+str(row[1]) + ";"+str(row[5])+";"
        elif datalist[1] == 'SENSOR_update':
            reply = 'true;SENSOR_update;'
            conndb.execute("UPDATE sensory set Name =%s,H_refresh_sec=%s,H_keep_days=%s where Id=%s", (datalist[3], datalist[4], datalist[5], datalist[2]))
        elif datalist[1] == 'SENSOR_addCustom':
            conndb.execute("SELECT * from sensory where Type like 'custom'")
            cursor = conndb.fetchall()
            customNumber = len(cursor)+1
            while True:
                conndb.execute("SELECT * from sensory where Id = %s",('Custom'+str(customNumber),))
                cursor = conndb.fetchall()
                if len(cursor) == 0: break
                else: customNumber+=1
            conndb.execute("INSERT INTO sensory(Id,Name,H_refresh_sec,H_keep_days,Type,Unit,GPIO_BCM,Data_Name,Cmd_id) VALUES(%s,%s,%s,%s,'custom',%s,%s,%s,%s) RETURNING Id", ('Custom'+str(customNumber),datalist[2],datalist[3],datalist[4],datalist[5],datalist[6],datalist[7],datalist[8]))
            reply = 'true;SENSOR_addCustom;'+str(conndb.fetchone()[0])
            updateSensorHistory('Custom'+str(customNumber),conndb)
        elif datalist[1] == 'SENSOR_updateCustom':
            reply = 'true;SENSOR_updateCustom;'
            conndb.execute("UPDATE sensory set Name=%s,H_refresh_sec=%s,H_keep_days=%s,Unit=%s,GPIO_BCM=%s,Data_Name=%s,Cmd_id=%s where Id=%s", (datalist[3], datalist[4], datalist[5],datalist[6],datalist[7],datalist[8],datalist[9], datalist[2]))
        elif datalist[1] == 'SENSOR_remove':
            reply = 'true;SENSOR_remove;'
            conndb.execute("DELETE from sensory where Id=%s", (datalist[2],))
            conndb.execute("DELETE from sensoryHistoria WHERE Id=%s", (datalist[2],))
            conndb.execute("DELETE FROM wyzwalaczeAkcji WHERE Id_s=%s AND Warunek LIKE 'sensor'", (datalist[2],))
            if conndb.rowcount > 0:
                conndb.execute("UPDATE akcje set Edit_time=%s where Id in (SELECT Id FROM akcje LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
        elif datalist[1] == 'NOTIF_check':
            reply = 'true;NOTIF_check;'
            if datalist[3] == "i/o":
                reply += "0;"
                if datalist[4] == "ANY":
                    cursor = conndb.execute("SELECT * from historia h JOIN stany s ON h.Id_IO=s.Id WHERE h.Id_IO = %s AND h.Czas > %s ORDER BY h.Czas DESC", (datalist[2], datalist[6]))
                else:
                    cursor = conndb.execute("SELECT * from historia h JOIN stany s ON h.Id_IO=s.Id WHERE h.Id_IO = %s AND h.Czas > %s AND h.Stan = %s ORDER BY h.Czas DESC", (datalist[2], datalist[6], datalist[4]))
                for row in conndb.fetchall():
                    reply += str(row[12])+';'+str(row[1]) +';'+str(row[2])+';'+str(row[5])+';'
            elif datalist[3] == "sensor":
                updateSensorHistory(datalist[2],conndb)
                cursor = conndb.execute("SELECT * from sensoryHistoria h JOIN sensory s ON h.Id = s.Id WHERE h.Id = %s AND h.Timestamp > %s AND h.Value "+datalist[5]+" %s ORDER BY h.Timestamp DESC", (datalist[2], datalist[6], datalist[4]))
                i = 0
                for row in conndb.fetchall():
                    if i == 0: reply += str(row[8])+';'
                    reply += str(row[4])+';'+str(row[1]) + ';'+str(row[7])+';'+str(row[2])+';'
                    i = i+1
        elif datalist[1] == 'GPIO_OInames':
            cursor = conndb.execute("SELECT Id,Name from stany ORDER BY Id DESC")
            reply = 'true;GPIO_OInames;'
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1])+';'
        elif datalist[1] == 'GPIO_PWMnames':
            cursor = conndb.execute("SELECT Id,Name from pwm ORDER BY Id DESC")
            reply = 'true;GPIO_PWMnames;'
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1])+';'
        elif datalist[1] == 'GPIO_ASAEtime':
            cursor = conndb.execute("SELECT Max(Edit_time) FROM akcje")
            reply = 'true;GPIO_ASAEtime;'+str(conndb.fetchone()[0])+';'
        elif datalist[1] == 'startStopASA':
            conndb.execute("UPDATE akcje set Cpu_usage=0, Rodzaj=%s, Edit_time=%s where Id=%s", (datalist[3], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), datalist[2]))
            reply = 'true;startStopASA;'
        elif datalist[1] == 'GPIO_ASAlist':
            cursor = conndb.execute('SELECT a.id as "a_id", a.typ as "a_type", a.rodzaj as "a_noe", a.koniunkcja, a.out_id, a.out_stan, a.pwm_id, a.pwm_fr, a.pwm_dc, a.pwm_ss, a.nazwa as "a_name", s.name as "out_name",s.reverse as "out_reverse", p.name as "pwm_name",a.chain_id, a.log as "a_log",l.nazwa as "chain_name", a.rf_id, r.name as "rf_name", a.cmd_id, c.name as "cmd_name", a.refresh_rate, a.cpu_usage, a.v_id, a.v_val, v.name as "v_name", a.a_id, a.a_noe, a.chain_ec from akcje a left join stany s on a.Out_id = s.Id left join pwm p on a.Pwm_id = p.Id left join lancuchy l on a.Chain_id = l.Id left join rf r on a.Rf_id = r.Id left join customCmds c on a.Cmd_id = c.Id LEFT JOIN globalVariables v ON a.V_id = v.Id ORDER BY a.Id DESC')
            reply = 'true;GPIO_ASAlist;'
            for row in conndb.fetchall():
                reply += ";".join(map(str, [row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],row[13],row[14],row[15],row[16],row[17],row[18],row[19],row[20],row[21],row[22],row[23],row[24],row[25],row[26],row[27],row[28]]))+";"
                conndb.execute('SELECT w.id as "w_id",w.id_s as "w_sourceid",w.lp,w.warunek as "w_type",w.operator,w.dane as "w_data",s.name as "io_name",s.reverse,p.name as "pwm_name",se.name as "se_name",se.unit,r.name as "rf_name",c.name as "cmd_name",w.id_link,w.name_link,l.name as "link_dname", v.name as "v_name" FROM wyzwalaczeAkcji w left join stany s on w.Id_s=CAST(s.Id AS TEXT) left join pwm p on w.Id_s=CAST(p.Id AS text) left join sensory se on w.Id_s=se.Id left join rf r on w.Id_s=CAST(r.Id AS TEXT) left join customCmds c on w.Id_s=CAST(c.Id AS TEXT) left join linkedPis l on w.Id_link = l.Id left join globalVariables v on w.Id_s=CAST(v.Id AS TEXT) WHERE w.Id_a=%s ORDER BY w.Lp',(str(row[0]),))
                for row1 in conndb.fetchall():
                    reply+=str(row1[0])+'$'+str(row1[1])+'$'+str(row1[2])+'$'+str(row1[3])+'$'+str(row1[4])+'$'+str(row1[5])+'$'+str(row1[6])+'$'+str(row1[7])+'$'+str(row1[8])+'$'+str(row1[9])+'$'+str(row1[10])+'$'+str(row1[11])+'$'+str(row1[12])+'$'+str(row1[13])+'$'+str(row1[14])+'$'+str(row1[15])+'$'+str(row1[16])+'$'
                reply+=';'
        elif datalist[1] == 'GPIO_ASA_Add':
            if datalist[3] == 'output':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, Out_id, Rodzaj, Out_stan, Edit_time, Log, Refresh_rate) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[9],datalist[10]))
            elif datalist[3] == 'pwm':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, Pwm_id, Rodzaj, Pwm_ss, Pwm_fr,Pwm_dc, Edit_time, Log, Refresh_rate) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6],datalist[7],datalist[8], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), datalist[9],datalist[10]))
            elif datalist[3] == 'chain':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, Chain_id, Rodzaj, Edit_time, Log, Refresh_rate, Out_stan) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), datalist[9],datalist[10],datalist[6]))
            elif datalist[3] == 'rfsend':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, Rf_id, Rodzaj, Edit_time, Log, Refresh_rate) VALUES(%s,%s,%s,%s,%s,%s,%s)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), datalist[9],datalist[10]))
            elif datalist[3] == 'cmd':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, Cmd_id, Rodzaj, Edit_time, Log, Refresh_rate) VALUES(%s,%s,%s,%s,%s,%s,%s)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), datalist[9],datalist[10]))
            elif datalist[3] == 'var':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, V_id, Rodzaj, V_val, Edit_time, Log, Refresh_rate) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[9],datalist[10]))
            elif datalist[3] == 'action_noe':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, A_id, Rodzaj, A_noe, Edit_time, Log, Refresh_rate) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[9],datalist[10]))
            elif datalist[3] == 'chain_ec':
                conndb.execute("INSERT INTO akcje(Nazwa, Typ, Chain_id, Rodzaj, Chain_ec, Edit_time, Log, Refresh_rate) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[9],datalist[10]))
            reply = 'true;GPIO_ASA_Add;'
        elif datalist[1] == 'GPIO_ASA_Update':
            if datalist[3] == 'output':
                conndb.execute("UPDATE akcje set Nazwa=%s, Typ=%s, Out_id=%s, Rodzaj=%s, Out_stan=%s, Edit_time=%s, Log=%s, Refresh_rate=%s where Id=%s", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10],datalist[11], datalist[9]))
            elif datalist[3] == 'pwm':
                conndb.execute("UPDATE akcje set Nazwa=%s, Typ=%s, Pwm_id=%s, Rodzaj=%s, Pwm_ss=%s, Pwm_fr=%s, Pwm_dc=%s, Edit_time=%s, Log=%s, Refresh_rate=%s where Id=%s", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6],datalist[7],datalist[8],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10],datalist[11],datalist[9]))
            elif datalist[3] == 'chain':
                conndb.execute("UPDATE akcje set Nazwa=%s, Typ=%s, Chain_id=%s, Rodzaj=%s, Edit_time=%s, Log=%s, Refresh_rate=%s, Out_stan=%s where Id=%s", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10],datalist[11],datalist[6],datalist[9]))
            elif datalist[3] == 'rfsend':
                conndb.execute("UPDATE akcje set Nazwa=%s, Typ=%s, Rf_id=%s, Rodzaj=%s, Edit_time=%s, Log=%s, Refresh_rate=%s where Id=%s", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10],datalist[11], datalist[9]))
            elif datalist[3] == 'cmd':
                conndb.execute("UPDATE akcje set Nazwa=%s, Typ=%s, Cmd_id=%s, Rodzaj=%s, Edit_time=%s, Log=%s, Refresh_rate=%s where Id=%s", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10],datalist[11], datalist[9]))
            elif datalist[3] == 'var':
                conndb.execute("UPDATE akcje set Nazwa=%s, Typ=%s, V_id=%s, Rodzaj=%s, V_val=%s, Edit_time=%s, Log=%s, Refresh_rate=%s where Id=%s", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10],datalist[11], datalist[9]))
            elif datalist[3] == 'action_noe':
                conndb.execute("UPDATE akcje set Nazwa=%s, Typ=%s, A_id=%s, Rodzaj=%s, A_noe=%s, Edit_time=%s, Log=%s, Refresh_rate=%s where Id=%s", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10],datalist[11], datalist[9]))
            elif datalist[3] == 'chain_ec':
                conndb.execute("UPDATE akcje set Nazwa=%s, Typ=%s, Chain_id=%s, Rodzaj=%s, Chain_ec=%s, Edit_time=%s, Log=%s, Refresh_rate=%s where Id=%s", (
                    datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[10],datalist[11], datalist[9]))
            reply = 'true;GPIO_ASA_Update;'
        elif datalist[1] == 'GPIO_ASA_Delete':
            conndb.execute("DELETE from akcje where Id=%s", (datalist[2],))
            conndb.execute("DELETE from wyzwalaczeAkcji where Id_a=%s", (datalist[2],))
            conndb.execute("UPDATE akcje set Edit_time=%s where Id in (SELECT Id FROM akcje LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            conndb.execute("DELETE FROM spoiwaLancuchow WHERE A_id=%s", (datalist[2],))
            conndb.execute("DELETE from akcje where A_id=%s", (datalist[2],))
            conndb.execute("DELETE FROM historia WHERE Id_a=%s", (datalist[2],))
            if conndb.rowcount > 0:
                conndb.execute("UPDATE lancuchy set Edit_time=%s where Id in (SELECT Id FROM lancuchy LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            reply = 'true;GPIO_ASA_Delete;'
        elif datalist[1] == 'GPIO_ASA_AddTrigger':
            cursor = conndb.execute("SELECT Id FROM wyzwalaczeAkcji WHERE Id_a = %s",(datalist[2],))
            rowcount = conndb.rowcount
            conndb.execute("INSERT INTO wyzwalaczeAkcji(Id_a, Id_s, Lp, Warunek, Operator, Dane, Id_link, Name_link) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (
                datalist[2], datalist[3], (int(rowcount)+1), datalist[4], datalist[5], datalist[6],datalist[7] or None,datalist[8]))
            conndb.execute("UPDATE akcje set Edit_time=%s where Id = %s", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ASA_AddTrigger;'
        elif datalist[1] == 'GPIO_ASA_UpdateTrigger':
            conndb.execute("UPDATE wyzwalaczeAkcji set Id_s=%s, Warunek=%s, Operator=%s, Dane=%s, Id_link=%s, Name_link=%s where Id=%s", (datalist[3], datalist[4], datalist[5], datalist[6],datalist[8] or None,datalist[9], datalist[7]))
            conndb.execute("UPDATE akcje set Edit_time=%s where Id = %s", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ASA_UpdateTrigger;'
        elif datalist[1] == 'GPIO_ASA_DeleteTrigger':
            conndb.execute("DELETE from wyzwalaczeAkcji where Id=%s", (datalist[2],))
            cursor = conndb.execute("SELECT Id FROM wyzwalaczeAkcji WHERE Id_a = %s",(datalist[3],))
            i=1
            for row in conndb.fetchall():
                conndb.execute("UPDATE wyzwalaczeAkcji set Lp=%s where Id=%s", (i,row[0]))
                i+=1
            conndb.execute("UPDATE akcje set Koniunkcja=%s, Edit_time=%s where Id = %s", (None,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[3]))
            reply = 'true;GPIO_ASA_DeleteTrigger;'
        elif datalist[1] == 'GPIO_ASA_SetConj':
            conndb.execute("UPDATE akcje set Koniunkcja=%s, Edit_time=%s where Id = %s", (datalist[2],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[3]))
            reply = 'true;GPIO_ASA_SetConj;'
        elif datalist[1] == 'Server_restart':
            statusCode = os.system("systemctl status rgc.service")
            if statusCode == 0:
                doRestartAfterReply = 1
            reply = 'true;Server_restart;'
        elif datalist[1] == 'Server_reboot':
            doRestartAfterReply = 2
            reply = 'true;Server_restart;Rebooting now...'
        elif datalist[1] == 'Server_status_code':
            statusCode = os.system("systemctl status rgc.service")
            reply = 'true;Server_status_code;'+str(statusCode)+";"
        elif datalist[1] == 'GPIO_ChainEtime':
            cursor = conndb.execute("SELECT Max(Edit_time) FROM lancuchy")
            reply = 'true;GPIO_ChainEtime;'+str(conndb.fetchone()[0])+';'
        elif datalist[1] == 'GPIO_ChainList':
            cursor = conndb.execute("SELECT * FROM lancuchy ORDER BY Id DESC")
            reply = 'true;GPIO_ChainList;'
            for row in conndb.fetchall():
                reply+=str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[4])+';'+str(row[5])+';'
                #conndb.execute("SELECT * FROM spoiwaLancuchow s LEFT JOIN stany st ON s.Out_id = st.Id LEFT JOIN pwm p ON s.Pwm_id = p.Id LEFT JOIN akcje a ON s.A_id = a.Id LEFT JOIN rf r ON s.Rf_id = r.Id LEFT JOIN customCmds c ON s.Cmd_id = c.Id LEFT JOIN linkedPis l ON s.Link_id = l.Id LEFT JOIN globalVariables v ON s.V_id = v.Id WHERE s.Id_c = %s ORDER BY Lp",(str(row[0]),))
                conndb.execute('SELECT s.id as "b_id",s.id_c,lp,dalay,s.typ as "b_type",s.a_id,s.out_id,s.out_stan,s.pwm_id,s.pwm_fr,s.pwm_dc,s.pwm_ss,st.name as "out_name", p.name as "pwm_name", a.nazwa as "a_name", s.rf_id, r.name as "rf_name", s.cmd_id, c.name as "cmd_name",s.link_id,s.link_name,l.name as "link_dname",s.c_id,s.v_id,s.v_val,v.name as "v_name",s.a_noe,s.c_ec FROM spoiwaLancuchow s LEFT JOIN stany st ON s.Out_id = st.Id LEFT JOIN pwm p ON s.Pwm_id = p.Id LEFT JOIN akcje a ON s.A_id = a.Id LEFT JOIN rf r ON s.Rf_id = r.Id LEFT JOIN customCmds c ON s.Cmd_id = c.Id LEFT JOIN linkedPis l ON s.Link_id = l.Id LEFT JOIN globalVariables v ON s.V_id = v.Id WHERE s.Id_c = %s ORDER BY Lp',(str(row[0]),))
                for row1 in conndb.fetchall():
                    #reply+="$".join(map(str, [row1[0],row1[1],row1[2],row1[3],row1[4],row1[5],row1[6],row1[7],row1[8],row1[9],row1[10],row1[11],row1[22],row1[33],row1[46],row1[53],row1[54],row1[61],row1[62],row1[14],row1[15],row1[66],row1[16],row1[17],row1[18],row1[74]]))+"$"
                    reply+="$".join(map(str, [row1[0],row1[1],row1[2],row1[3],row1[4],row1[5],row1[6],row1[7],row1[8],row1[9],row1[10],row1[11],row1[12],row1[13],row1[14],row1[15],row1[16],row1[17],row1[18],row1[19],row1[20],row1[21],row1[22],row1[23],row1[24],row1[25],row1[26],row1[27]]))+"$"
                reply+=';'
        elif datalist[1] == 'GPIO_ChainExecute':
            threading.Thread(target=chainExecude, args=(datalist[2], datalist[4],True if int(datalist[3]) else False)).start()
            reply = 'true;GPIO_ChainExecute;'
        elif datalist[1] == 'GPIO_ChainCancel':
            conndb.execute("UPDATE lancuchy set Status=0 WHERE Id=%s",(datalist[2],))
            reply = 'true;GPIO_ChainCancel;'
        elif datalist[1] == 'GPIO_ChainAdd':
            conndb.execute("INSERT INTO lancuchy (Nazwa,Status,Edit_time,ExecCountdown,Log) VALUES(%s,%s,%s,%s,%s)",(datalist[2],0,datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[3],datalist[4]))
            reply = 'true;GPIO_ChainAdd;'
        elif datalist[1] == 'GPIO_ChainUpdate':
            conndb.execute("Update lancuchy SET Nazwa=%s,Edit_time=%s,ExecCountdown=%s,Log=%s WHERE Id=%s",(datalist[3],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[4],datalist[5],datalist[2]))
            reply = 'true;GPIO_ChainUpdate;'
        elif datalist[1] == 'GPIO_ChainDelete':
            conndb.execute("DELETE FROM lancuchy WHERE Id=%s",(str(datalist[2]),))
            conndb.execute("DELETE FROM spoiwaLancuchow WHERE Id_c=%s",(str(datalist[2]),))
            conndb.execute("DELETE FROM spoiwaLancuchow WHERE C_id=%s",(str(datalist[2]),))
            conndb.execute("UPDATE lancuchy set Edit_time=%s where Id in (SELECT Id FROM lancuchy LIMIT 1)", (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            conndb.execute("DELETE FROM akcje WHERE Chain_id=%s", (str(datalist[2]),))
            if conndb.rowcount > 0:
                conndb.execute("UPDATE akcje set Edit_time=%s where Id in (SELECT Id FROM akcje LIMIT 1)", (
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),))
            reply = 'true;GPIO_ChainDelete;'
        elif datalist[1] == 'GPIO_ChainBondDelete':
            conndb.execute("DELETE FROM spoiwaLancuchow WHERE Id=%s",(datalist[2],))
            cursor = conndb.execute("SELECT Id FROM spoiwaLancuchow WHERE Id_c=%s ORDER BY Lp",(datalist[3],))
            i = 1
            for row in conndb.fetchall():
                conndb.execute("UPDATE spoiwaLancuchow SET Lp=%s WHERE Id=%s",(str(i),row[0]))
                i+=1
            conndb.execute("UPDATE lancuchy SET Edit_time=%s WHERE Id=%s",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[3]))
            reply = 'true;GPIO_ChainBondDelete;'
        elif datalist[1] == 'GPIO_ActionsNames':
            cursor = conndb.execute("SELECT Id,Nazwa from akcje ORDER BY Id DESC")
            reply = 'true;GPIO_ActionsNames;'
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1])+';'
        elif datalist[1] == 'GPIO_ChainBondAdd':
            cursor = conndb.execute("SELECT Id FROM spoiwaLancuchow WHERE Id_c = %s",(datalist[2],))
            rowcount = conndb.rowcount
            if datalist[3] == 'output':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, Out_id, Out_stan, Lp, Link_id, Link_name) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (datalist[2], datalist[3], datalist[4], datalist[5], datalist[6],(int(rowcount)+1),datalist[9],datalist[10]))
            elif datalist[3] == 'pwm':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, Pwm_id, Pwm_ss, Pwm_fr, Pwm_dc, Lp, Link_id, Link_name) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (datalist[2], datalist[3], datalist[4], datalist[5], datalist[6], datalist[7], datalist[8],(int(rowcount)+1),datalist[9],datalist[10]))
            elif datalist[3] == 'action':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, A_id, Lp, Link_id, Link_name) VALUES(%s,%s,%s,%s,%s,%s,%s)", (datalist[2], datalist[3], datalist[4], datalist[5],(int(rowcount)+1),datalist[9],datalist[10]))
            elif datalist[3] == 'rfsend':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, Rf_id, Lp, Link_id, Link_name) VALUES(%s,%s,%s,%s,%s,%s,%s)", (datalist[2], datalist[3], datalist[4], datalist[5],(int(rowcount)+1),datalist[9],datalist[10]))
            elif datalist[3] == 'cmd':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, Cmd_id, Lp, Link_id, Link_name) VALUES(%s,%s,%s,%s,%s,%s,%s)", (datalist[2], datalist[3], datalist[4], datalist[5],(int(rowcount)+1),datalist[9],datalist[10]))
            elif datalist[3] == 'chain':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, C_id, Out_stan, Lp, Link_id, Link_name) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (datalist[2], datalist[3], datalist[4], datalist[5], datalist[6],(int(rowcount)+1),datalist[9],datalist[10]))
            elif datalist[3] == 'var':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, V_id, V_val, Lp, Link_id, Link_name) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (datalist[2], datalist[3], datalist[4], datalist[5], datalist[6],(int(rowcount)+1),datalist[9],datalist[10]))
            elif datalist[3] == 'action_noe':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, A_id, A_noe, Lp, Link_id, Link_name) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (datalist[2], datalist[3], datalist[4], datalist[5], datalist[6],(int(rowcount)+1),datalist[9],datalist[10]))
            elif datalist[3] == 'chain_ec':
                conndb.execute("INSERT INTO spoiwaLancuchow(Id_c, Typ, Dalay, C_id, C_ec, Lp, Link_id, Link_name) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (datalist[2], datalist[3], datalist[4], datalist[5], datalist[6],(int(rowcount)+1),datalist[9],datalist[10]))
            conndb.execute("UPDATE lancuchy SET Edit_time=%s WHERE Id=%s",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ChainBondAdd;'
        elif datalist[1] == 'GPIO_ChainBondUpdate':
            if datalist[3] == 'output':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=%s, Dalay=%s, Out_id=%s, Out_stan=%s, Link_id=%s, Link_name=%s WHERE Id=%s", (datalist[3], datalist[4], datalist[5], datalist[6],datalist[10],datalist[11], datalist[9]))
            elif datalist[3] == 'pwm':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=%s, Dalay=%s, Pwm_id=%s, Pwm_ss=%s, Pwm_fr=%s, Pwm_dc=%s, Link_id=%s, Link_name=%s WHERE Id=%s", (datalist[3], datalist[4], datalist[5], datalist[6], datalist[7], datalist[8],datalist[10],datalist[11],datalist[9]))
            elif datalist[3] == 'action':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=%s, Dalay=%s, A_id=%s, Link_id=%s, Link_name=%s WHERE Id=%s", (datalist[3], datalist[4], datalist[5],datalist[10],datalist[11],datalist[9]))
            elif datalist[3] == 'rfsend':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=%s, Dalay=%s, Rf_id=%s, Link_id=%s, Link_name=%s WHERE Id=%s", (datalist[3], datalist[4], datalist[5],datalist[10],datalist[11],datalist[9]))
            elif datalist[3] == 'cmd':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=%s, Dalay=%s, Cmd_id=%s, Link_id=%s, Link_name=%s WHERE Id=%s", (datalist[3], datalist[4], datalist[5],datalist[10],datalist[11],datalist[9]))
            elif datalist[3] == 'chain':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=%s, Dalay=%s, C_id=%s, Out_stan=%s, Link_id=%s, Link_name=%s WHERE Id=%s", (datalist[3], datalist[4], datalist[5], datalist[6],datalist[10],datalist[11], datalist[9]))
            elif datalist[3] == 'var':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=%s, Dalay=%s, V_id=%s, V_val=%s, Link_id=%s, Link_name=%s WHERE Id=%s", (datalist[3], datalist[4], datalist[5], datalist[6],datalist[10],datalist[11], datalist[9]))
            elif datalist[3] == 'action_noe':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=%s, Dalay=%s, A_id=%s, A_noe=%s, Link_id=%s, Link_name=%s WHERE Id=%s", (datalist[3], datalist[4], datalist[5], datalist[6],datalist[10],datalist[11], datalist[9]))
            elif datalist[3] == 'chain_ec':
                conndb.execute("UPDATE spoiwaLancuchow SET Typ=%s, Dalay=%s, C_id=%s, C_ec=%s, Link_id=%s, Link_name=%s WHERE Id=%s", (datalist[3], datalist[4], datalist[5], datalist[6],datalist[10],datalist[11], datalist[9]))
            conndb.execute("UPDATE lancuchy SET Edit_time=%s WHERE Id=%s",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ChainBondUpdate;'
        elif datalist[1] == 'GPIO_ChainBondsOrder':
            bondidlplist = datalist[3].split("$")
            i = 0
            while i<len(bondidlplist):
                conndb.execute("UPDATE spoiwaLancuchow SET Lp=%s WHERE Id=%s",(bondidlplist[i],bondidlplist[i+1]))
                i+=2
            conndb.execute("UPDATE lancuchy SET Edit_time=%s WHERE Id=%s",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;GPIO_ChainBondsOrder;'
        elif datalist[1] == 'Chain_names':
            cursor = conndb.execute("SELECT Id,Nazwa from lancuchy")
            reply = 'true;Chain_names;'
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1])+';'
        elif datalist[1] == 'Server_logs':
                logs = os.popen('journalctl -u rgc.service -r -n 200 --no-pager').read()
                reply = 'true;Server_logs;'+logs+";"
        elif datalist[1] == 'Server_logs_JSON':
                logs = os.popen('journalctl -u rgc.service -r --since "1 days ago" --no-pager --output=json --utc -p 0..5').read()
                logsArr = logs.splitlines()
                reply = 'true;Server_logs_JSON;'
                for log in logsArr:
                    singleLog = json.loads(log)
                    reply += singleLog['__REALTIME_TIMESTAMP']+";"+singleLog['PRIORITY']+";"+singleLog['MESSAGE'].replace(';','$')+";"
                    # singleLog = log.split('=')
                    # if singleLog[0] in ['__REALTIME_TIMESTAMP','PRIORITY','MESSAGE']:
                    #     reply += singleLog[1].replace(';','$')+";"
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
        elif datalist[1] == 'HR_sel':
            cursor = conndb.execute("SELECT h.Id,Czas,h.Typ,case when s.Name is NOT NULL then s.Name when p.Name is NOT NULL then p.Name when l.Nazwa is NOT NULL then l.Nazwa when a.Nazwa is NOT NULL then a.Nazwa else c.Name end as NameC,h.Stan FROM historia h Left JOIN stany s ON s.Id = h.Id_IO left JOIN pwm p ON p.Id = h.Id_Pwm left JOIN lancuchy l ON l.Id = h.Id_c left JOIN customCmds c ON c.Id = h.Id_cmd left JOIN akcje a ON a.Id = h.Id_a where Czas between %s and %s order by Czas DESC LIMIT %s", (datalist[2], datalist[3],datalist[5]))
            reply = 'true;HR_sel;'+datalist[4]+";"
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[4])+';'
        elif datalist[1] == 'HR_selByCat':
            if datalist[4] == 'i/o':
                cursor = conndb.execute("SELECT h.Id,Czas,Typ,s.Name,h.Stan FROM historia h JOIN stany s ON s.Id = h.Id_IO WHERE Czas between %s and %s order by Czas DESC LIMIT 1000", (datalist[2], datalist[3]))
            elif datalist[4] == 'pwm':
                cursor = conndb.execute("SELECT h.Id,Czas,Typ,p.Name,h.Stan FROM historia h JOIN pwm p ON p.Id = h.Id_Pwm WHERE Czas between %s and %s order by Czas DESC LIMIT 1000", (datalist[2], datalist[3]))
            elif datalist[4] == 'chain':
                cursor = conndb.execute("SELECT h.Id,Czas,Typ,l.Nazwa,h.Stan FROM historia h JOIN lancuchy l ON l.Id = h.Id_c WHERE Czas between %s and %s order by Czas DESC LIMIT 1000", (datalist[2], datalist[3]))
            elif datalist[4] == 'cmd':
                cursor = conndb.execute("SELECT h.Id,Czas,Typ,c.Name,h.Stan FROM historia h JOIN customCmds c ON c.Id = h.Id_cmd WHERE Czas between %s and %s order by Czas DESC LIMIT 1000", (datalist[2], datalist[3]))
            elif datalist[4] == 'action':
                cursor = conndb.execute("SELECT h.Id,Czas,h.Typ,a.Nazwa,h.Stan FROM historia h JOIN akcje a ON a.Id = h.Id_a WHERE Czas between %s and %s order by Czas DESC LIMIT 1000", (datalist[2], datalist[3]))
            elif datalist[4] == 'all':
                cursor = conndb.execute("SELECT h.Id,Czas,h.Typ,case when s.Name is NOT NULL then s.Name when p.Name is NOT NULL then p.Name when l.Nazwa is NOT NULL then l.Nazwa when a.Nazwa is NOT NULL then a.Nazwa else c.Name end as MainName,h.Stan FROM historia h Left JOIN stany s ON s.Id = h.Id_IO left JOIN pwm p ON p.Id = h.Id_Pwm left JOIN lancuchy l ON l.Id = h.Id_c left JOIN customCmds c ON c.Id = h.Id_cmd left JOIN akcje a ON a.Id = h.Id_a where Czas between %s and %s order by Czas DESC  LIMIT 1000", (datalist[2], datalist[3]))
            reply = 'true;HR_selByCat;'
            for row in conndb.fetchall():
                reply += str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(row[3])+';'+str(row[4])+';'
        elif datalist[1] == 'SENSOR_history':
            cursor = conndb.execute("SELECT * from sensory s WHERE Id = %s", (datalist[2],))
            row = conndb.fetchone()
            reply = 'true;SENSOR_history;'+row[5]+";"
            cursor = conndb.execute("SELECT * from sensoryHistoria WHERE Id=%s ORDER BY Timestamp DESC", (datalist[2],))
            for row in conndb.fetchall():
                reply += str(row[1])+';'+str(row[2])+';'
        elif datalist[1] == 'SENSOR_clearhistory':
            conndb.execute("DELETE from sensoryHistoria WHERE Id=%s", (datalist[2],))
            reply = 'true;SENSOR_clearhistory;'
        elif datalist[1] == 'SENSOR_refresh':
            value = updateSensorHistory(datalist[2],conndb)
            if value == None: reply = 'false;SENSOR_refresh;'+str(value)+";"
            else: reply = 'true;SENSOR_refresh;'+str(value)+";"
        elif datalist[1] == 'SENSORS_history':
            reply = 'true;SENSORS_history;'
            cursor = conndb.execute("SELECT s.Id,s.Name,s.Unit,h.Timestamp,h.Value from sensoryHistoria h JOIN sensory s ON h.Id = s.Id  WHERE s.Id IN ("+datalist[2]+")  ORDER BY Timestamp DESC")
            for row in conndb.fetchall():
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
                log.error("Cannot update, no internet access %s")
                httpCode = 503
                reply = 'true;ServerUpdateFromGH;Cannot update, no internet access %s;'
            else:
                downURL = lastRelease['assets'][1]['browser_download_url']
                savedFile = open(os.getcwd()+"/rgc-update.tar.gz", 'w')
                savedFile.write(urllib2.urlopen(downURL).read())
                savedFile.close()
                import tarfile
                import shutil
                tar = tarfile.open(os.getcwd()+"/rgc-update.tar.gz")
                shutil.rmtree(os.getcwd()+"/www")
                def members(tf):
                    l = len("rgc/")
                    for member in tf.getmembers():
                        if member.path.startswith("rgc/"):
                            member.path = member.path[l:]
                            yield member
                tar.extractall(members=members(tar))
                tar.close()
                doRestartAfterReply = 1
                reply = 'true;ServerUpdateFromGH;Update in progress...;'
        elif datalist[1] == 'SendRfCode':
            reply = sendRfCode(conndb,datalist[2],True)
        elif datalist[1] == 'GetRfCodes':
            cursor = conndb.execute("SELECT * from rf ORDER BY Id DESC")
            reply = 'true;GetRfCodes;'
            for row in conndb.fetchall():
                reply += ";".join(map(str, [row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7]]))+";"
        elif datalist[1] == 'GetRfPins':
            reply = 'true;GetRfPins;'+str(RF_RX_BCM)+";"+str(RF_TX_BCM)+";"
        elif datalist[1] == 'AddRfCode':
            conndb.execute("INSERT INTO rf(Name,Type,Code,PulseLength,Protocol,RepeatTransmit,BitLength) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING Id", (datalist[2],datalist[3],datalist[4],datalist[5],datalist[6],datalist[7],datalist[8]))
            reply = 'true;AddRfCode;'+str(conndb.fetchone()[0])
        elif datalist[1] == 'DeleteRfCode':
            conndb.execute("DELETE from rf where Id=%s", (datalist[2],))
            conndb.execute("DELETE from rfHistoria where Id=%s", (datalist[2],))
            conndb.execute("DELETE from akcje where Rf_id=%s", (datalist[2],))
            conndb.execute("DELETE from wyzwalaczeAkcji where Id_s=%s and Warunek='rfrecived'", (datalist[2],))
            conndb.execute("DELETE from spoiwaLancuchow where Rf_id=%s", (datalist[2],))
            reply = 'true;DeleteRfCode;'+datalist[2]
        elif datalist[1] == 'UpdateRfCode':
            conndb.execute("UPDATE rf set Name=%s,Type=%s,Code=%s,PulseLength=%s,Protocol=%s,RepeatTransmit=%s,BitLength=%s where Id=%s",(datalist[3],datalist[4],datalist[5],datalist[6],datalist[7],datalist[8],datalist[9],datalist[2]))
            reply = 'true;UpdateRfCode;'
        elif datalist[1] == 'GetRfHistory':
            cursor = conndb.execute("select * from rfHistoria h join rf r on r.Id = h.Id WHERE Timestamp between %s and %s order by Timestamp DESC",(datalist[2],datalist[3]))
            reply = 'true;GetRfHistory;'
            for row in conndb.fetchall():
                reply += ";".join(map(str, [row[6],row[7],row[8],row[0],row[2],row[3],row[4]]))+";"
        elif datalist[1] == 'SniffRfCodes':
            reply = 'true;SniffRfCodes'
            for el in reversed(snifferArr):
                reply+=";"+";".join(map(str, el))
        elif datalist[1] == 'GetRfRecivedNow':
            conndb.execute('select h.Id from rfHistoria h left join rf r on h.Id = r.Id where Type = "Recive" and Timestamp >= %s and h.Id = %s',(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),datalist[2]))
            reply = "true;GetRfRecivedNow;"+str(conndb.rowcount)+";"
        elif datalist[1] == 'ExecCustomCmd':
            execCmd = execCustomCmd(conndb,datalist[2],datalist[4])
            if execCmd[0]: 
                reply = 'true;ExecCustomCmd;'+execCmd[1]
            else: reply = 'false;'+execCmd[1]
        elif datalist[1] == 'GetCustomCmds':
            cursor = conndb.execute("SELECT * from customCmds ORDER BY Id DESC")
            reply = 'true;GetCustomCmds;'
            for row in conndb.fetchall():
                reply += ";".join(map(str, row))+";"
        elif datalist[1] == 'AddCustomCmd':
            conndb.execute("INSERT INTO customCmds(Name,Cmd,WaitForExec) VALUES(%s,%s,%s) RETURNING Id", (datalist[2],datalist[3],datalist[4]))
            reply = 'true;AddCustomCmd;'+str(conndb.fetchone()[0])
        elif datalist[1] == 'DeleteCustomCmd':
            conndb.execute("DELETE from customCmds where Id=%s", (datalist[2],))
            conndb.execute("DELETE from historia where Id_cmd=%s", (datalist[2],))
            conndb.execute("DELETE from akcje where Cmd_id=%s", (datalist[2],))
            conndb.execute("DELETE from sensory where Cmd_id=%s", (datalist[2],))
            conndb.execute("DELETE from wyzwalaczeAkcji where Id_s=%s and Warunek='cmd'", (datalist[2],))
            conndb.execute("DELETE from spoiwaLancuchow where Cmd_id=%s", (datalist[2],))
            reply = 'true;DeleteCustomCmd;'+datalist[2]
        elif datalist[1] == 'UpdateCustomCmd':
            conndb.execute("UPDATE customCmds set Name=%s,Cmd=%s,WaitForExec=%s where Id=%s",(datalist[3],datalist[4],datalist[5],datalist[2]))
            reply = 'true;UpdateCustomCmd;'
        elif datalist[1] == 'CallLinkedPi':
            res = callLinkedPi(datalist[2],datalist[3],conndb)
            if res: reply = ";".join(map(str, res))
            else: reply = 'false;Cannot connect linked pi !'
        elif datalist[1] == 'GetLinkedPis':
            cursor = conndb.execute("SELECT * from linkedPis ORDER BY Id DESC")
            reply = 'true;GetLinkedPis;'
            for row in conndb.fetchall():
                reply += ";".join(map(str, row))+";"
                if datalist[2] == '1':
                    res = callLinkedPi(row[0],"version_check;",conndb)
                    if res: reply += res[2]+";"
                    else: reply +='0'+";"
        elif datalist[1] == 'AddLinkedPi':
            conndb.execute("INSERT INTO linkedPis(Name,Url,Password,Mode,Port) VALUES(%s,%s,%s,%s,%s) RETURNING Id", (datalist[2],datalist[3],datalist[4],datalist[5],datalist[6]))
            reply = 'true;AddLinkedPi;'+str(conndb.fetchone()[0])
        elif datalist[1] == 'UpdateLinkedPi':
            conndb.execute("UPDATE linkedPis set Name=%s,Url=%s,Password=%s,Mode=%s,Port=%s where Id=%s",(datalist[3],datalist[4],datalist[5],datalist[6],datalist[7],datalist[2]))
            reply = 'true;UpdateLinkedPi;'
        elif datalist[1] == 'DeleteLinkedPi':
            conndb.execute("DELETE from linkedPis where Id=%s", (datalist[2],))
            conndb.execute("DELETE from wyzwalaczeAkcji where Id_link=%s", (datalist[2],))
            reply = 'true;DeleteLinkedPi;'+datalist[2]
        elif datalist[1] == "GetConfigSections":
            reply = 'true;GetConfigSections'
            for each_section in parser.sections():
                reply += ";"+each_section+";"
                kv = []
                for (each_key, each_val) in parser.items(each_section):
                    kv.append(each_key)
                    kv.append(each_val)
                reply+="$".join(map(str, kv))
        elif datalist[1] == "SetConfigSections":
            if PASSWORD == '': del datalist[-1]
            for x in range(2, len(datalist)-1, 3):
                parser.set(datalist[x], datalist[x+1], datalist[x+2])
            with open('rgc-config.ini', 'wb') as configfile:
                parser.write(configfile)
            reply = 'true;SetConfigSections;'
        elif datalist[1] == 'GetGlobalVars':
            cursor = conndb.execute("SELECT * from globalVariables ORDER BY Id DESC")
            reply = 'true;GetGlobalVars;'
            for row in conndb.fetchall():
                reply += ";".join(map(str, row))+";"
        elif datalist[1] == 'AddGlobalVar':
            conndb.execute("INSERT INTO globalVariables(Name,Val,Type) VALUES(%s,%s,%s) RETURNING Id", (datalist[2],datalist[3],datalist[4]))
            reply = 'true;AddGlobalVar;'+str(conndb.fetchone()[0])
        elif datalist[1] == 'DeleteGlobalVar':
            conndb.execute("DELETE from globalVariables where Id=%s", (datalist[2],))
            conndb.execute("DELETE from akcje where V_id=%s", (datalist[2],))
            conndb.execute("DELETE from wyzwalaczeAkcji where Id_s=%s and Warunek='var'", (datalist[2],))
            conndb.execute("DELETE from spoiwaLancuchow where V_id=%s", (datalist[2],))
            reply = 'true;DeleteGlobalVar;'+datalist[2]
        elif datalist[1] == 'UpdateGlobalVar':
            conndb.execute("UPDATE globalVariables set Name=%s,Val=%s,Type=%s,Timestamp=%s where Id=%s",(datalist[3],datalist[4],datalist[5],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;UpdateGlobalVar;'
        elif datalist[1] == 'SetGlobalVar':
            conndb.execute("UPDATE globalVariables set Val=%s,Timestamp=%s where Id=%s",(datalist[3],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;SetGlobalVar;'
        elif datalist[1] == 'GetGlobalVar':
            conndb.execute("SELECT Val,Type from globalVariables where Id=%s",(datalist[2],))
            row = conndb.fetchone()
            if len(row): reply = 'true;GetGlobalVar;'+str(row[0])+";"+str(row[1])+";"
            else: reply = 'false;GetGlobalVar;Global variable not defined;'
        elif datalist[1] == 'SetActionNOE':
            conndb.execute("UPDATE akcje set Rodzaj=%s, Edit_time=%s where Id=%s", (datalist[3], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[2]))
            reply = 'true;SetActionNOE;'
        elif datalist[1] == 'SetChainEC':
            conndb.execute("Update lancuchy SET Edit_time=%s, ExecCountdown=%s WHERE Id=%s",(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),datalist[3],datalist[2]))
            reply = 'true;SetChainEC;'
        else:
            reply = 'false;Connection OK, but no compabile method found, probably encryption error;'
            httpCode = 501
    else:
        reply = 'false;Wrong password !;'
        httpCode = 401
    if debug: print "REPLY: "+reply
    if debug: print "SIZE: "+str(sys.getsizeof(reply))+"b"
    if PASSWORD != '' and passwalidation == True:
        reply = '1;'+encrypt(ENC_KEY, reply)+';'
    conndb.close()
    conn.close()
    return (reply,httpCode)


def rebotOrRestartAfterReply():
    global doRestartAfterReply
    if doRestartAfterReply != -1:
        time.sleep(2)
        if doRestartAfterReply == 1: os.system("systemctl restart rgc.service")
        elif doRestartAfterReply == 2: os.system("reboot")

class UDPRequestHandler(SocketServer.DatagramRequestHandler):
    def handle(self):
        if debug: print("THREAD:{} FOR USER:{}".format(threading.current_thread().name,self.client_address[0]))
        data = self.request[0].strip()
        if debug and PASSWORD: print 'RECIVED_ENC: '+data
        reply = "false; Not found !"
        try:
            reply = requestMethod(data)[0]
        except Exception as e:
            log.error(e.message)
            log.error(traceback.format_exc())
            reply = "false;"+e.message
        self.wfile.write(reply)
        rebotOrRestartAfterReply()


class TCPRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        data = ""
        timeout = time.time() + 20   # 20 sec from now
        while not exit_event.is_set() and time.time() < timeout:
            line = self.rfile.readline().strip()
            data+=line
            if "#EOF#" in line: break
            time.sleep(0.001)
        if debug: print("THREAD:{} FOR USER:{}".format(threading.current_thread().name,self.client_address[0]))
        reply = "false; Not found !"
        try:
            reply = requestMethod(data)[0]
        except Exception as e:
            log.error(e.message)
            log.error(traceback.format_exc())
            reply = "false;"+e.message
        reply = zlib.compress(reply).encode('base64')
        if debug: print "SIZE: "+str(sys.getsizeof(reply))+"b"
        self.request.sendall(reply)
        rebotOrRestartAfterReply()

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
            reply = ("false; Not found !",404)
            try:
                reply = requestMethod(data)
            except Exception as e:
                log.error(e.message)
                log.error(traceback.format_exc())
                reply = ("false;"+e.message,500)
            replyData = reply[0]
            self.send_response(reply[1]) #create header
        self.send_header("Content-Length", str(len(replyData)))
        self.end_headers()
        self.wfile.write(replyData) #send response
        rebotOrRestartAfterReply()

class ThreadedHTTPServer(SocketServer.ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


if __name__ == '__main__':
    print 'Server is starting...'
    print 'Please press Ctrl+C to end the program...'
    manager = multiprocessing.Manager()
    conn, conndb = newDBConnP()
    conndb.execute('''CREATE TABLE IF NOT EXISTS stany (
            Id    SERIAL NOT NULL PRIMARY KEY,
            GPIO_BCM    TEXT NOT NULL,
            Stan    INTEGER NOT NULL,
            Name    TEXT,
            IN_OUT    TEXT,
            Edit_time    TEXT,
            Reverse    INTEGER NOT NULL,
            Bindid    INTEGER,
            Bindtype    INTEGER
        );
        CREATE TABLE IF NOT EXISTS pwm (
            Id	SERIAL NOT NULL PRIMARY KEY,
            GPIO_BCM	TEXT NOT NULL,
            FR	NUMERIC NOT NULL,
            DC	INTEGER NOT NULL,
            SS	INTEGER NOT NULL,
            Name	TEXT NOT NULL,
            Reverse	INTEGER NOT NULL,
            Edit_time    TEXT DEFAULT timezone('utc', now())
        );
        CREATE TABLE IF NOT EXISTS historia (
            Id    SERIAL NOT NULL PRIMARY KEY,
            Czas    TIMESTAMP DEFAULT timezone('utc', now()),
            Typ    TEXT,
            Id_IO    INTEGER,
            Id_Pwm    INTEGER,
            Stan    TEXT NOT NULL,
            Id_c    INTEGER,
            Id_cmd    INTEGER,
            Id_a    INTEGER
        );
        CREATE TABLE IF NOT EXISTS sensory (
            Id    TEXT NOT NULL PRIMARY KEY UNIQUE,
            Name    TEXT,
            H_refresh_sec    INTEGER NOT NULL DEFAULT 3600,
            H_keep_days    INTEGER NOT NULL DEFAULT 7,
            Type    TEXT NOT NULL,
            Unit    TEXT NOT NULL,
            Model    TEXT,
            GPIO_BCM    TEXT,
            Data_name    TEXT,
            Cmd_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS sensoryHistoria (
            Id    TEXT NOT NULL,
            Timestamp    TIMESTAMP DEFAULT timezone('utc', now()),
            Value	NUMERIC NOT NULL
        );
        CREATE TABLE IF NOT EXISTS akcje (
            Id	SERIAL NOT NULL PRIMARY KEY,
            Typ	TEXT NOT NULL,
            Rodzaj	INTEGER NOT NULL,
            Koniunkcja	TEXT,
            Out_id	NUMERIC,
            Out_stan	INTEGER,
            Pwm_id	INTEGER,
            Pwm_fr	INTEGER,
            Pwm_dc	INTEGER,
            Pwm_ss	INTEGER,
            Nazwa	TEXT,
            Edit_time	TEXT DEFAULT timezone('utc', now()),
            Chain_id	INTEGER,
	        Log	INTEGER,
            Rf_id INTEGER,
            Refresh_rate	NUMERIC,
            Cmd_id	INTEGER,
            Pid	INTEGER,
            Cpu_usage NUMERIC,
            V_id	INTEGER,
            V_val	TEXT,
            A_id    INTEGER,
            A_noe	INTEGER,
            Chain_ec	INTEGER
        );
        CREATE TABLE IF NOT EXISTS wyzwalaczeAkcji (
            Id	SERIAL NOT NULL PRIMARY KEY,
            Id_a	INTEGER NOT NULL,
            Id_s	TEXT,
            Lp	INTEGER NOT NULL,
            Warunek	TEXT NOT NULL,
            Operator	TEXT NOT NULL,
            Dane	TEXT NOT NULL,
            Id_link	INTEGER,
	        Name_link	TEXT
        );
        CREATE TABLE IF NOT EXISTS lancuchy (
            Id SERIAL NOT NULL PRIMARY KEY,
            Status	INTEGER NOT NULL DEFAULT 0,
            Nazwa	TEXT,
            Edit_time	TEXT DEFAULT timezone('utc', now()),
            ExecCountdown INTEGER DEFAULT 1,
            Log INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS spoiwaLancuchow (
            Id	SERIAL NOT NULL PRIMARY KEY,
            Id_c	INTEGER NOT NULL,
            Lp	INTEGER NOT NULL,
            Dalay	NUMERIC NOT NULL DEFAULT 1,
            Typ	TEXT NOT NULL,
            A_id	INTEGER,
            Out_id	NUMERIC,
            Out_stan	INTEGER,
            Pwm_id	INTEGER,
            Pwm_fr	INTEGER,
            Pwm_dc	INTEGER,
            Pwm_ss	INTEGER,
            Rf_id INTEGER,
            Cmd_id	INTEGER,
            Link_id	INTEGER,
	        Link_name	TEXT,
            C_id	INTEGER,
            V_id	INTEGER,
            V_val	TEXT,
            A_noe	INTEGER,
            C_ec	INTEGER
        );
        CREATE TABLE IF NOT EXISTS rf (
            Id	SERIAL NOT NULL PRIMARY KEY,
            Name	TEXT,
            Type	TEXT NOT NULL,
            Code	TEXT NOT NULL,
            PulseLength	INTEGER NOT NULL,
            Protocol	INTEGER,
            RepeatTransmit	INTEGER,
            BitLength	INTEGER
        );
        CREATE TABLE IF NOT EXISTS rfHistoria (
            Timestamp	TEXT NOT NULL DEFAULT(to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
            Id	INTEGER NOT NULL,
            PulseLength	INTEGER NOT NULL,
            Protocol	INTEGER,
            BitLength	INTEGER
        );
        CREATE TABLE IF NOT EXISTS customCmds (
            Id	SERIAL NOT NULL PRIMARY KEY,
            Name	TEXT,
            Cmd	TEXT NOT NULL,
            WaitForExec	INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS linkedPis (
            Id	SERIAL NOT NULL PRIMARY KEY,
            Name	TEXT,
            Url	TEXT NOT NULL,
            Password	TEXT,
            Mode	TEXT,
	        Port	INTEGER
        );
        CREATE TABLE IF NOT EXISTS globalVariables (
            Id	SERIAL NOT NULL PRIMARY KEY,
            Name	TEXT NOT NULL,
            Val	TEXT,
            Type	TEXT NOT NULL,
            Timestamp    TIMESTAMP DEFAULT timezone('utc', now())
        );
        ''')
    conndb.execute("ALTER TABLE lancuchy ADD COLUMN IF NOT EXISTS ExecCountdown INTEGER DEFAULT 1;")
    conndb.execute("ALTER TABLE spoiwaLancuchow ADD COLUMN IF NOT EXISTS C_id INTEGER;")
    conndb.execute("ALTER TABLE lancuchy ADD COLUMN IF NOT EXISTS Log INTEGER DEFAULT 1;")
    conndb.execute("ALTER TABLE spoiwaLancuchow ADD COLUMN IF NOT EXISTS V_id INTEGER;")
    conndb.execute("ALTER TABLE spoiwaLancuchow ADD COLUMN IF NOT EXISTS V_val TEXT;")
    conndb.execute("ALTER TABLE akcje ADD COLUMN IF NOT EXISTS V_id INTEGER;")
    conndb.execute("ALTER TABLE akcje ADD COLUMN IF NOT EXISTS V_val TEXT;")
    conndb.execute("ALTER TABLE spoiwaLancuchow ADD COLUMN IF NOT EXISTS A_noe INTEGER;")
    conndb.execute("ALTER TABLE akcje ADD COLUMN IF NOT EXISTS A_id INTEGER;")
    conndb.execute("ALTER TABLE akcje ADD COLUMN IF NOT EXISTS A_noe INTEGER;")
    conndb.execute("ALTER TABLE spoiwaLancuchow ADD COLUMN IF NOT EXISTS C_ec INTEGER;")
    conndb.execute("ALTER TABLE akcje ADD COLUMN IF NOT EXISTS Chain_ec INTEGER;")
    conndb.execute("ALTER TABLE historia ADD COLUMN IF NOT EXISTS Id_a INTEGER;")

    log.info('Server local time: '+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))
    startTime = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')

    if parser.getboolean('main','passwordEnabled'):
        PASSWORD = hashlib.sha256(parser.get('main','password').encode()).hexdigest()
        ENC_KEY = hashlib.md5(parser.get('main','password').encode()).hexdigest()
    if parser.getboolean('sensors','ds18b20'):
        from ds18b20 import DS18B20
        DS = DS18B20()
        if DS.device_count() == 0:
            log.error("ds18b20 devices not detected")
        else:
            j = 0
            while j < DS.device_count():
                conndb.execute("INSERT INTO sensory(Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING", (DS.device_name(j), "ds18b20", "C", "temperature"))
                j += 1
    else: conndb.execute("UPDATE sensory SET H_refresh_sec=0 WHERE Type LIKE 'ds18b20'")
    if parser.getboolean('sensors','dht'):
        import Adafruit_DHT
        dhtTypes = parser.get('sensors','dhtType').split(',')
        dhtGpios = parser.get('sensors','dhtGpio').split(',')
        for i, dtype in enumerate(dhtTypes):
            humidity, temperature = Adafruit_DHT.read_retry(int(dtype), int(dhtGpios[i]))
            if humidity is not None and temperature is not None:
                conndb.execute("INSERT INTO sensory(Id,Type,Unit,Model,GPIO_BCM,Data_name) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", (
                    "DHT_"+dtype+"_"+dhtGpios[i]+"_T", "dht", "C", dtype, dhtGpios[i], "temperature"))
                conndb.execute("INSERT INTO sensory(Id,Type,Unit,Model,GPIO_BCM,Data_name) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", (
                    "DHT_"+dtype+"_"+dhtGpios[i]+"_H", "dht", "%", dtype, dhtGpios[i], "humidity"))
            else:
                log.error('DHT'+dtype+" at pin:" + dhtGpios[i]+" not readable !")
    else: conndb.execute("UPDATE sensory SET H_refresh_sec=0 WHERE Type LIKE 'dht'")
    if parser.getboolean('sensors', 'tsl2561'):
        from Adafruit_TSL2561 import Adafruit_TSL2561
        TSL = Adafruit_TSL2561()
        gain = parser.getint('sensors','tsl2561Gain')
        if gain <= 16 and gain > 0: TSL.set_gain(gain)
        else: TSL.enable_auto_gain(True)
        conndb.execute("INSERT INTO sensory(Id,Type,Unit,Model,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ("I2C_0x39", "tsl2561", "lx", str(gain), "illumination"))
    else: conndb.execute("UPDATE sensory SET H_refresh_sec=0 WHERE Type LIKE 'tsl2561'")
    if parser.getboolean('sensors', 'rotaryEncoder'):
        tslClks = parser.get('sensors','rotaryEncoderClk').split(',')
        tslDts = parser.get('sensors','rotaryEncoderDt').split(',')
        tslMaxs = parser.get('sensors','rotaryEncoderMax').split(',')
        tslMins = parser.get('sensors','rotaryEncoderMin').split(',')
        def clockCallback(clk):
            if GPIO.input(clk) == 0:
                data = GPIO.input(RE_COUNTERS[clk][2])
                if data == 1:
                    if RE_COUNTERS[clk][0] < RE_COUNTERS[clk][4]: RE_COUNTERS[clk][0] += 1
                else:
                    if RE_COUNTERS[clk][0] > RE_COUNTERS[clk][3]: RE_COUNTERS[clk][0] -= 1
        for i, clk in enumerate(tslClks):
            RE_COUNTERS[int(clk)] = [int(tslMaxs[i])/2, int(clk),int(tslDts[i]),int(tslMins[i]),int(tslMaxs[i])] #ct clk dt min max
            conndb.execute("INSERT INTO sensory(Id,Type,Unit,GPIO_BCM,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ("RE_"+clk+"_"+tslDts[i], "rotary_encoder", "ct",clk+","+tslDts[i],"counter"))
            cursor = conndb.execute("SELECT Value FROM sensoryHistoria WHERE Id = %s ORDER BY Timestamp DESC LIMIT 1",("RE_"+clk+"_"+tslDts[i],))
            row = conndb.fetchone()
            if len(row):
                RE_COUNTERS[int(clk)][0] = int(row[0])
            GPIO.setup(int(clk), GPIO.IN)
            GPIO.setup(int(tslDts[i]), GPIO.IN)
            GPIO.add_event_detect(int(clk),GPIO.FALLING, callback=clockCallback,bouncetime=100)
            GPIO_EVENTS_PINS.append(int(clk))
    else: conndb.execute("UPDATE sensory SET H_refresh_sec=0 WHERE Type LIKE 'rotary_encoder'")
    if parser.getboolean('sensors', 'rangeSensor'):
        rsTriggers = parser.get('sensors','rangeSensorTrigger').split(',')
        rsEchos = parser.get('sensors','rangeSensorEcho').split(',')
        rsMaxes = parser.get('sensors','rangeSensorMaxValue').split(',')
        def getRSdistance(RS_TRIG_BCM,RS_ECHO_BCM,RS_MAX):
            GPIO.output(RS_TRIG_BCM, True)
            time.sleep(0.00001)
            GPIO.output(RS_TRIG_BCM, False)
            StartTime = time.time()
            StopTime = time.time()
            Timeout = datetime.now()
            while GPIO.input(RS_ECHO_BCM)==0:
                time_delta = datetime.now() - Timeout
                if time_delta.total_seconds() >= 0.1: return RS_MAX
                StartTime = time.time()
            Timeout = datetime.now()
            while GPIO.input(RS_ECHO_BCM)==1:
                time_delta = datetime.now() - Timeout
                if time_delta.total_seconds() >= 0.1: return RS_MAX
                StopTime = time.time()
            TimeElapsed = StopTime - StartTime
            distance = (TimeElapsed * 34300) / 2
            return round(distance, 1)
        for i, trigger in enumerate(rsTriggers):
            RANGE_SENSORS['RS_'+trigger+'_'+rsEchos[i]] = [int(trigger),int(rsEchos[i]),int(rsMaxes[i])]
            conndb.execute("INSERT INTO sensory(Id,Type,Unit,GPIO_BCM,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('RS_'+trigger+'_'+rsEchos[i], "range_sensor", "cm",trigger+","+rsEchos[i] ,"distance"))
            GPIO.setup(int(trigger), GPIO.OUT)
            GPIO.setup(int(rsEchos[i]), GPIO.IN)
            GPIO.output(int(trigger), False)
    else: conndb.execute("UPDATE sensory SET H_refresh_sec=0 WHERE Type LIKE 'range_sensor'")
    if parser.getboolean('rf',"reciver"):
        RF_RX_BCM = parser.getint('rf','reciverGpio')
        snifferArr = []
        def rfReciverLoop():
            p = subprocess.Popen(['./433Utils/RPi_utils/RFSniffer',str(RF_RX_BCM)], stdout=subprocess.PIPE, bufsize=1)
            conn, conndb = newDBConnP()
            while not exit_event.is_set():
                line = p.stdout.readline()
                if line != '':
                    if debug: print 'RF_Recive: '+line
                    data = line.rstrip().split("|")
                    if len(data) > 1:
                        snifferArr.append([data[0],data[2],data[1],data[3],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')])
                        if len(snifferArr) > 50: snifferArr.pop(0)
                        conndb.execute("SELECT * from rf WHERE Code=%s AND Type='Recive'",(data[0],))
                        row = conndb.fetchone()
                        if row:
                            conndb.execute("INSERT INTO rfHistoria(Id,PulseLength,Protocol,BitLength) VALUES(%s,%s,%s,%s)", (row[0],data[2],data[1],data[3]))
                    else: log.error(data)
                time.sleep(0.01)
            conndb.close()
            conn.close()
            p.kill()
    if parser.getboolean('rf','transmiter'):
        RF_TX_BCM = parser.getint('rf','transmiterGpio')
        def sendRfCode(conndb,id,wait,log=True):
            conndb.execute("SELECT * from rf WHERE Id = %s", (id,))
            row = conndb.fetchone()
            sendCodeProcess = subprocess.Popen(['./433Utils/RPi_utils/codesend',row[3],str(RF_TX_BCM),str(row[5]),str(row[4]),str(row[6])], stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
            if wait:
                output, errors = sendCodeProcess.communicate()
                if sendCodeProcess.returncode: return 'false;'+errors+';'
                else:
                    if log: conndb.execute("INSERT INTO rfHistoria(Id,PulseLength,Protocol,BitLength) VALUES(%s,%s,%s,%s)", (id,row[4],row[5],row[7]))
                    if debug: print 'RF_Send: '+output
                    return 'true;SendRfCode;'+output
            else:
                if log: conndb.execute("INSERT INTO rfHistoria(Id,PulseLength,Protocol,BitLength) VALUES(%s,%s,%s,%s)", (id,row[4],row[5],row[7]))
                return sendCodeProcess
    if parser.has_option('sensors','PMS7003'):
        if parser.getboolean('sensors','PMS7003'):
            from PMS7003 import PMS7003
            pms7003 = PMS7003(parser.getboolean('sensors','PMS7003passiveMode'),parser.get('sensors','PMS7003serialPort'),parser.getboolean('sensors','PMS7003factoryPMvalues'),parser.getboolean('sensors','PMS7003atmosphericPMvalues'),parser.getboolean('sensors','PMS7003particleCount'))
            if pms7003.serialPort.isOpen(): 
                if pms7003.factoryPMvalues:
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('PM1 Factory concentration','concPM1_0_CF1', "PMS7003", "ug/m3", "air quality"))
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('PM2.5 Factory concentration','concPM2_5_CF1', "PMS7003", "ug/m3", "air quality"))
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('PM10 Factory concentration','concPM10_0_CF1', "PMS7003", "ug/m3", "air quality"))
                if pms7003.atmosphericPMvalues:
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('PM1 Atmospheric concentration','concPM1_0_ATM', "PMS7003", "ug/m3", "air quality"))
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('PM2.5 Atmospheric concentration','concPM2_5_ATM', "PMS7003", "ug/m3", "air quality"))
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('PM10 Atmospheric concentration','concPM10_0_ATM', "PMS7003", "ug/m3", "air quality"))
                if pms7003.particleCount:
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('Particle count (diameter 0.3 um)','rawGt0_3um', "PMS7003", "per 0.1l", "air quality"))
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('Particle count (diameter 0.5 um)','rawGt0_5um', "PMS7003", "per 0.1l", "air quality"))
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('Particle count (diameter 1.0 um)','rawGt1_0um', "PMS7003", "per 0.1l", "air quality"))
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('Particle count (diameter 2.5 um)','rawGt2_5um', "PMS7003", "per 0.1l", "air quality"))
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('Particle count (diameter 5.0 um)','rawGt5_0um', "PMS7003", "per 0.1l", "air quality"))
                    conndb.execute("INSERT INTO sensory(Name,Id,Type,Unit,Data_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ('Particle count (diameter 10 um)','rawGt10_0um', "PMS7003", "per 0.1l", "air quality"))
            else: log.error("Unable to open serial port")
        else: conndb.execute("UPDATE sensory SET H_refresh_sec=0 WHERE Type LIKE 'PMS7003'")
    else:
        parser.set('sensors','PMS7003','no')
        parser.set('sensors','PMS7003serialPort','/dev/serial0')
        parser.set('sensors','PMS7003passiveMode','no')
        parser.set('sensors','PMS7003factoryPMvalues','yes')
        parser.set('sensors','PMS7003atmosphericPMvalues','yes')
        parser.set('sensors','PMS7003particleCount','yes')
        with open('rgc-config.ini', 'wb') as configfile:
            parser.write(configfile)

    sensors_timers = {}
    sensors_timers_const = {}

    def updateSensorHistory(id,cdb):
        cdb.execute("SELECT * from sensory s WHERE Id = %s", (id,))
        row = cdb.fetchone()
        value = getCurrentSensorValue(id,cdb)
        if value != None: cdb.execute("INSERT INTO sensoryHistoria(Id,Value) VALUES(%s,%s)",(row[0], value))
        return value

    def getCurrentSensorValue(id,cdb):
        cdb.execute("SELECT * from sensory s WHERE Id = %s", (id,))
        row = cdb.fetchone()
        try:
            if row[4] == 'ds18b20':
                return DS.tempC_byDeviceName(row[0])
            elif row[4] == 'dht':
                time.sleep(1)
                if row[8] == 'temperature':
                    return round(float(Adafruit_DHT.read_retry(int(row[6]), int(row[7]))[1]),2)
                elif row[8] == 'humidity':
                    return round(float(Adafruit_DHT.read_retry(int(row[6]), int(row[7]))[0]),2)
            elif row[4] == 'tsl2561':
                return TSL.calculate_lux()
            elif row[4] == 'rotary_encoder':
                clk = int(row[0].split('_')[1])
                return RE_COUNTERS[clk][0]
            elif row[4] == 'range_sensor':
                global RANGE_SENSORS
                return getRSdistance(RANGE_SENSORS[row[0]][0],RANGE_SENSORS[row[0]][1],RANGE_SENSORS[row[0]][2])
            elif row[4] == 'PMS7003':
                refreshTime = 30 if parser.getboolean('sensors', 'PMS7003passiveMode') else 3
                if pms7003.lastRead == None:
                    pms7003.readValues()
                elif (time.time() - pms7003.lastRead) > refreshTime:
                    pms7003.readValues()
                if pms7003.lastValues['err']: log.error(pms7003.lastValues['errMessage'])
                return pms7003.lastValues[row[0]]
            elif row[4] == 'custom':
                execCmd = execCustomCmd(cdb,row[9],'',False,True)
                if execCmd[0]: return float(execCmd[1])
                else: raise ValueError(execCmd[1])
        except Exception as e:
            print(e.message)
            log.error(e.message)
            return None

    def sensorLoop():
        startTime = time.time()
        global exit_event
        def sensorTick(startTime,conndb3):
            conndb3.execute("SELECT * FROM sensory s WHERE H_refresh_sec > 0")
            for row in conndb3.fetchall():
                if row[0] in sensors_timers and int(row[2]) > 0:
                    if sensors_timers_const[row[0]] != int(row[2]):
                        sensors_timers[row[0]] = int(row[2])
                        sensors_timers_const[row[0]] = int(row[2])
                    elif sensors_timers[row[0]] <= 0:
                        sensors_timers[row[0]] = int(row[2])
                        updateSensorHistory(row[0],conndb3)
                        if int(row[3]) > 0:
                            conndb3.execute("DELETE from sensoryHistoria WHERE Timestamp < (NOW() - INTERVAL '"+str(row[3])+" DAY') AND Id = '"+str(row[0])+"';")
                    else:
                        sensors_timers[row[0]] -= (time.time()-startTime)
                else:
                    sensors_timers[row[0]] = int(row[2])
                    sensors_timers_const[row[0]] = int(row[2])
        conn, conndb = newDBConnP()
        while not exit_event.is_set():
            try: 
                sensorTick(startTime,conndb)
            except Exception as e:
                print e.message
                log.error("Error: "+e.message)
            startTime = time.time()
            time.sleep(1)
        conndb.close()
        conn.close()
                

    conndb.execute("SELECT * from stany where IN_OUT like 'out' order by Edit_time ASC")
    for row in conndb.fetchall():
        log.info('OUTPUT: GPIO='+str(row[1])+' STATE='+str(row[2]))
        GPIOInitOut(row[1])
        GPIOset(row[1], row[2]) if not row[8] else GPIOset(row[1], 0 if not row[6] else 1)

    conndb.execute("SELECT * from pwm")
    for row in conndb.fetchall():
        log.info('OUTPUT PWM: GPIO=' +str(row[1])+' S/S='+str(row[4]) +' FR='+str(row[2])+' DC='+str(row[3]))
        pwmpins = row[1].split(",")
        for pin in pwmpins:
            pwm[pin] = GPIOPWM(int(pin), float(row[2]))
            if row[4] == 1: pwm[pin].start(int(row[3]))
    try:
        serverUDP = SocketServer.ThreadingUDPServer((HOST,parser.getint('main','mobilePort')), UDPRequestHandler)
        serverUDP.max_packet_size = 8192*4
        serverUDP.allow_reuse_address = True
        serverUDP_thread = threading.Thread(target=serverUDP.serve_forever)
        serverUDP_thread.daemon = True
        serverTCP = SocketServer.ThreadingTCPServer((HOST, parser.getint('main','mobilePort')),TCPRequestHandler)
        serverTCP.allow_reuse_address = True
        serverTCP_thread = threading.Thread(target=serverTCP.serve_forever)
        serverTCP_thread.daemon = True
        serverHTTP = ThreadedHTTPServer(('', parser.getint('main','wwwPort')), HTTPRequestHandler)
        serverHTTP.allow_reuse_address = True
        serverHTTP_thread = threading.Thread(target=serverHTTP.serve_forever)
        serverHTTP_thread.daemon = True
        conndb.execute("SELECT Id,(SELECT Value from sensoryHistoria h WHERE h.Id=s.Id ORDER BY Timestamp DESC LIMIT 1) from sensory s")
        for row in conndb.fetchall(): 
            if not row[1]: updateSensorHistory(row[0],conndb)
        services_th = threading.Thread(target=services)
        services_th.daemon = True
        services_th.start()
        if RF_RX_BCM:
            rfReciverLoop_th = threading.Thread(target=rfReciverLoop)
            rfReciverLoop_th.daemon = True
            rfReciverLoop_th.start()
        sensors_th = threading.Thread(target=sensorLoop)
        sensors_th.daemon = True
        sensors_th.start()
        conndb.execute("SELECT * from stany where IN_OUT like 'in%'")
        for row in conndb.fetchall():
            log.info('INPUT: GPIO='+str(row[1])+' STATE='+str(row[2]))
            # threading.Thread(target=inputLoop, args=(row[0], row[1], row[2], row[6])).start()
            GPIOinputSet(row[1],1 if not row[8] else int(row[8]),row[4], row[0], row[2], row[6], row[7])
            # if(row[4] == 'in'):
            #     cb = debounceHandler(int(row[1]), lambda channel, id=row[0], Stan=row[2], reverse=row[6]: inputCallback(channel, id, Stan, reverse),bouncetime=200 if not row[7] else int(row[7]))
            #     cb.daemon = True
            #     cb.start()
            #     GPIO.add_event_detect(int(row[1]), GPIO.BOTH, callback=cb)
            # else:
            #     p1 = multiprocessing.Process(target=inputLoop, args=(row[0], row[1], row[2], row[6], row[7]))
            #     p1.daemon = True
            #     p1.start()
            #     running_proceses.append(p1)
            #GPIO.add_event_detect(int(row[1]), GPIO.BOTH, lambda channel, id=row[0], Stan=row[2], reverse=row[6]: inputCallback(channel, id, Stan, reverse), bouncetime=50)
        if MODE != 'wwwOnly':
            serverUDP_thread.start()
            serverTCP_thread.start()
        if MODE != 'mobileOnly':
            serverHTTP_thread.start()
        conndb.close()
        conn.close()
        print "Server started !"
        def handler_stop_signals():
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
            for pin in GPIO_EVENTS_PINS:
                GPIO.remove_event_detect(pin)
            GPIO.cleanup()
            global exit_event
            exit_event.set()
            global running_proceses
            for p in running_proceses:
                if p.is_alive():
                    p.terminate()
                    p.join()
            for proc in psutil.process_iter():
                for conns in proc.connections(kind='inet'):
                    if MODE != "wwwOnly":
                        if conns.laddr.port == parser.getint('main','mobilePort'):
                            proc.send_signal(signal.SIGTERM)
                    elif MODE != "mobileOnly":
                        if conns.laddr.port == parser.getint('main','wwwPort'):
                            proc.send_signal(signal.SIGTERM)
            sys.exit(0)

        while not exit_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        handler_stop_signals()
