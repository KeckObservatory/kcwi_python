#from . import Version
#Version.append('$Revision: 85432 $')
#del Version
"""
.. module:: PowerInit
"""

import ktl
import os, sys, time
import logging as lg
from datetime import datetime
import subprocess

from Helper import setupMonitoring, checkInitialValues,say, checkIfMoveIsPossible, changeMoveMode, checkSuccess, ProgressBar, AnimatedProgressBar, ProgressCallback, isServerUp

from Calibration import hatch, lamp_shutter, image_slicer, polarizer, cal_object, cal_mirror, polangle, hex_pupil

from Blue import focusb, is_in_filling_position

def bigmessage(message):
    line = "*" * len(message)
    sys.stdout.write(line+"*****\n")
    say(message)
    sys.stdout.write(line+"*****\n")    


def is_device_up(address,timeout):
    done = False
    cmd = ['ping','-c 2','-W 5',address]
    while not done and timeout:
        response = subprocess.Popen(cmd,stdout=subprocess.PIPE)
        stdout,stderr = response.communicate()
        if response.returncode == 0:
            say("%s is up" % (address))
            done = True
            return True
        else:
            sys.stdout.write(".")
            timeout -= 1
    if not done:
        say("Device %s failed to respond within %f seconds" % (address,timeout))
        return False


# standard width for terminals for progress bar
standardWidth = 80

def FPCamPower(power):

    """
    Closes camera and then powers up the FPCam

    Parameters
    ----------

    power: string
         Accepts the values of "on" of "off"

    Examples
    --------
    
    Turns on the FPCamera

    >>> PowerInit.FPCamPower(power="on")

    """
    if power not in ['on','off']:
        say("Please specify on or off")
        return


    # start keyword monitoring

    powerServer = 'kp1s'
    cameraServer = 'kfcs'
    try:
        pwstat1 = ktl.cache(powerServer,'PWSTAT1')
    except:
        raise RuntimeError("Failed to read power status. KP1S might not be running")
    try:
        closed = ktl.cache(cameraServer,'CLOSED')
        close = ktl.cache(cameraServer,'CLOSE')
        init = ktl.cache(cameraServer,'INIT')
        status = ktl.cache(cameraServer,'STATUS')
        binning = ktl.cache(cameraServer,'BINNING')
    except:
        raise RuntimeError("Failed to contact camera server. KFCS might not be running")

    monitoredKeywords = (pwstat1,closed,init, status)

    setupMonitoring(monitoredKeywords, wait=True)

    if power == 'on':
        
        # try to turn on the camera power
        if (pwstat1.ascii=="1"):
            say("FPCam is already on")
        else:
            pwstat1.write(1)
            time.sleep(2)
            result = pwstat1.ascii
            if int(result) != 1:
                say("ERROR: KP1S not allowing power to FPCam to be turned on")
                sys.exit(1)
            else:
                say("FPCam power is now on")

        # if the camera is not closed, it cannot be initialized
        say("Checking if the camera can be initialized")
        if int(closed.ascii) == 0:
            say("The camera is not closed. It cannot be initialized.")
            sys.exit(1)
        else:
            say("The camera is closed. Proceeding with initialization.")


        # wait for camera to become available

        say("Listening for FPCam ")
        fpcam_status = is_device_up("192.168.1.30",20)
        if fpcam_status != True:
            say("Error communicating with FPCam.")
            sys.exit(1)
        else:
            say("FPCam has been successfully detected on the network")
        time.sleep(2)

        # try to open camera connection
        say("Initializing FPCAM")

        if int(closed.ascii) == 1:
            say("Camera is closed. Attempting to open..")
            max_trials = 3
            trial = 1
            while trial<= max_trials:
                try:
                    init.write(1)
                    time.sleep(3)
                    status.waitFor("==OK",timeout=10)
                    if status == "OK":
                        say("Camera is ready")
                        break
                except:
                    say("Attempting to initialize camera again")
                    trial=trial+1
                    close.write(1)
                    time.sleep(1)
                    status.waitFor("==Closed", timeout=10)

        else:
            say("FP Camera is already open")


        say("Setting binning to 4x4")
        binning.write(4)
        return

    if power == 'off':
        
        # try to close camera connection
        
        if int(closed.ascii) != 1:
            close.write(1)
            time.sleep(3)
        if int(closed.ascii) != 1:
            say("ERROR: KFCS not allowing FPCam to close")
            sys.exit(1)
        say("Camera closed")

        # try to turn off the camera power
        
        pwstat1.write(0)
        time.sleep(2)
        result = pwstat1.ascii
        if int(result) != 0:
            say("ERROR: KP1S not allowing power to FPCam to be turned off")
            sys.exit(1)
        else:
            say("FPCam power is off")
            time.sleep(8)    
        return


def kcwiPowerStatus():
   """ 
   Provides access to the power supplies status
   """
   kp1s = ktl.cache('kp1s')
   kp2s = ktl.cache('kp2s')
   kp3s = ktl.cache('kp3s')

   plugs = [1,2,3,4,5,6,7,8]
   p1={}
   p2={}
   p3={}

   for plug in plugs:
      p1[plug]=[kp1s['pwname'+str(plug)],kp1s['pwstat'+str(plug)],kp1s]
      p2[plug]=[kp2s['pwname'+str(plug)],kp2s['pwstat'+str(plug)],kp2s]
      p3[plug]=[kp3s['pwname'+str(plug)],kp3s['pwstat'+str(plug)],kp3s]

   say(datetime.now().strftime("%c"))
   say("")
   format = "%1s %-14s %1s\t| %1s %-14s %1s\t| %1s %-14s %1s"
   say(format % ('P','Serv. 1 - kp1s','on','P','Serv. 2 - kp2s','on','P','Serv. 3 - kp3s','on'))
   say("")
   for plug in plugs:
      say(format % (str(plug),p1[plug][0].read(),p1[plug][1].read(),\
                    str(plug),p2[plug][0].read(),p2[plug][1].read(),\
                    str(plug),p3[plug][0].read(),p3[plug][1].read()))

   return p1,p2,p3

def kcwiPower(serverNumber=None, plugNumber=None, action=None):
   
   p1,p2,p3 = kcwiPowerStatus()
   
   powers = [p1,p2,p3]

   if serverNumber == None:
      question = "Which server number ?"
      reply = "tmp"
      while reply not in ['1','2','3','']:
         reply = str(raw_input(question)).strip()
         if reply=='':
             say("No server specified, returning...")
             return
      server = reply   
   else:
      server = serverNumber
   
   if plugNumber == None:
      question = "Which plug number ?"
      reply = "tmp"
      while reply not in ['1','2','3','4','5','6','7','8','']:
         reply = str(raw_input(question)).strip()
         if reply=='':
             say("No plug specified, returning...")
             return
      plug = reply   
   else:
      plug = plugNumber

   if action == None:
      question = "on/off/cycle ?"
      reply = "tmp"
      while reply not in ['on','off','cycle','']:
         reply = str(raw_input(question)).lower().strip()
         if reply=='':
             say("No action specified, returning...")
             return
      action = reply.lower()


   name = powers[int(server)-1][int(plug)][0].read()
   status = powers[int(server)-1][int(plug)][1].read()


   if action == 'cycle':
       if int(status) == 0:
           say("")
           say("Cannot cycle a plug that is already off!")
           return
       else:
           say("%s: Cycling power of %s" % (powers[int(server)-1][int(plug)][2],name))
           say("Turning power off")
           powers[int(server)-1][int(plug)][1].write(0)
           time.sleep(5)
           say("Turning power on")
           powers[int(server)-1][int(plug)][1].write(1)
   else:

        if action == 'on':
            action = 1
        if action == 'off':
            action = 0

        say("%s: Changing status of %s (currently at %s) to %s" % (powers[int(server)-1][int(plug)][2],name, status,action))

        powers[int(server)-1][int(plug)][1].write(action)

   #p1,p2,p3 = kcwiPowerStatus()

def kcwiTempStatus():
   """ 
   Provides access to the temperature status
   """
   kt1s=None
   kt2s=None
   
   if isServerUp('kt1s'):
       kt1s = ktl.cache('kt1s')
   else:
       say("Cannot establish connection to KT1S")
   if isServerUp('kt2s'):    
       kt2s = ktl.cache('kt2s') 
   else:
       say("Warning: Cannot establish connection to KT2S")

   sensors = [1,2,3,4,5,6,7,8]
   t1={}
   t2={}
   say(datetime.now().strftime("%c"))

   format = "%1s %-20s %10.3f %10.3f"
   say("%1s %-20s %7s %7s" % ('S','Location','C','K'))

   for sensor in sensors:
       if kt1s is not None:
           t1[sensor]=[kt1s['tmploc'+str(sensor)],kt1s['tmp'+str(sensor)],kt1s]
           T1 = float(t1[sensor][1].read())-273.15
           if T1+273.15>0:
               say(format % (str(sensor),t1[sensor][0].read(),T1,T1+273.15))
   for sensor in sensors:
       if kt2s is not None:
           t2[sensor]=[kt2s['tmploc'+str(sensor)],kt2s['tmp'+str(sensor)],kt2s]
           T2 = float(t2[sensor][1].read())-273.15
           if T2+273.15>0:
               say(format % (str(sensor),t2[sensor][0].read(),T2,T2+273.15))

   return t1,t2



def homeCalUnit():


    # is the galil alive?
    status = is_device_up('calgalil',10)
    if status == False:
        say("The calibration unit Galil is not responding")
        sys.exit(1)

    # is the server up?
    status = isServerUp('kcas')
    if status == False:
        say("The calibration server is not ready")
        sys.exit(1)

    # Start
    say("Starting initialization...")
    
    # Actuating shutters
    say("Actuating shutters")
    for repeat in range(2):
        lamp_shutter("fear","open")    
        time.sleep(2)
        lamp_shutter("fear","close")
        time.sleep(2)
        lamp_shutter("thar","open")    
        time.sleep(2)
        lamp_shutter("thar","close")
        time.sleep(2)

    # calibration unit
    kcas_service = ktl.cache('kcas')
    status = kcas_service('status')

    status.monitor()


    # build dictionary
    # keywords are : Name, homed_keyword, home_keyword, status_keyword
    kcas = {}
    kcas['ifu']  = ['IFU', 'ifuhomed','ifuhome','ifustatus']
    kcas['call'] = ['Polarizer','callhomed','callhome','callstatus']
    kcas['calh'] = ['Hex Pupil','calhhomed','calhhome','calhstatus']
    kcas['calm'] = ['Cal Mirror','calmhomed','calmhome','calmstatus']
    kcas['calp'] = ['Cal Lens','calphomed','calphome','calpstatus']
    kcas['calx'] = ['Cal X','calxhomed','calxhome','calxstatus']
    kcas['caly'] = ['Cal Y','calyhomed','calyhome','calystatus']

    for axis in kcas:

        name = kcas[axis][0]
        homed = kcas_service(kcas[axis][1])
        home = kcas_service(kcas[axis][2])
        homed.monitor()

        # check if axis is already homed
        if int(homed.read()) == 1:
            say("%s is already homed" % (name))
            continue

        # homing
        say("Homing %s" % (name))
        home.write(1)
        time.sleep(10)
        
        # check for status
        status.waitFor('==OK',timeout=300)
        homed.waitFor('== 1',timeout=300)
        if int(homed.read()) != 1:
            raise RuntimeError("Axis %s failed to home in  %d seconds"
                               % (name, 300))
    # set default vaules
    #image_slicer("Small", move=True)
    polarizer("Sky", move=True)
    cal_mirror("Sky", move=True)
    cal_object("Dark", move=True)
    polangle(60, move=True) # same as "B"
    hex_pupil("Flat", move=True)

def homeRotator():

    # is the galil alive?
    status = is_device_up('rotgalil',10)
    if status == False:
        say("The rotator Galil is not responding")
        sys.exit(1)

    # is the server up?
    status = isServerUp('kros')
    if status == False:
        say("The rotation server is not ready")
        sys.exit(1)

    # Start
    say("Starting initialization...")

    kros_service = ktl.cache('kros')

    settrckmode = kros_service('settrckmode')
    try:
        settrckmode.write(0)
    except:
        say("ERROR: Failed to turn off track mode.")
        sys.exit(1)

    # Preliminary homing
    rothome = kros_service('rothome')
    try:
        rothome.write(1)
    except:
        say("ERROR: Failed to start KROS Preliminary homing.")
        sys.exit(1)
    time.sleep(2)

    # wait for status to be ok
    status = kros_service('status')
    status.monitor()
    status.waitFor('=="OK"', timeout=120)
    if status.read()!="OK":
        say("ERROR: Failed to execute KROS Preliminary homing.")
        sys.exit(1)

    # read current angle
    rotang = kros_service('rotang')
    say("KROS: Preliminary homing successuful. Rotator at about: %s deg." % (rotang.read()))

    # Slew to final homing location
    rotmode = kros_service("rotmode")
    try:
        rotmode.write("3")
    except:
        say("ERROR: Failed to set rotator to slew mode.")
        sys.exit(1)
    rottargang = kros_service('rottargang')
    try:
        rottargang.write("2.0")
    except Exception as e:
        say("ERROR: Failed to slew to secondary angle.")
        say("ERROR is %s" % (e))
        sys.exit(1)
    status.monitor()
    say("Waiting for status to be OK...")
    status.waitFor('=="OK"', timeout=120)
    say("Status is ok")
    time.sleep(5)
    status.waitFor('=="OK"', timeout=120)
    if status.read() != "OK":
        say("ERROR: Failed to complete slew to secondary angle.")
        say("Status is %s" % (status.read()))
        sys.exit(1)
    say("At secondary angle")
    # FINAL HOMING
    try:
        rotmode.write("1")
    except:
        say("ERROR: Failed to set rotator to track mode.")
        sys.exit(1)    
    say("KROS: Set to track mode")
    try:
        rothome.write("1")
    except:
        say("ERROR: Failed to start KROS final homing.")
        sys.exit(1)  
    
    say("KROS: Final homing started.")
    time.sleep(2)
    status.waitFor('=="OK"', timeout=120)
    if status.read()!="OK":
        say("ERROR: Failed to execute KROS final homing.")
        sys.exit(1)

    say("At secondary angle")


    encerror = kros_service('encerror')
    encerror.write("0")
    say("KROS: Final homing successuful. Rotator at about: %s deg." % (rotang.read()))


def setupRotatorTracking():
        
    # is the server up?
    status = isServerUp('kros')
    if status == False:
        say("The rotation server is not ready")
        sys.exit(1)  

    kros = ktl.cache('kros')
    #lockall = kros['lockall']
    rotsetup = kros['rotsetup']
    rotservo = kros['rotservo']
    rotfrctrk = kros['rotfrctrk']
    rotcor = kros['rotcor']

    # it is a k-mirror, so set rotcor to -0.5
    # number updated 170410 based on FPC images
    rotcor.write(-0.5)

    #lockall.write(0)
    rotsetup.write(1)
    rotservo.write(1)
    rotfrctrk.write(1)
    
    


def homeKBES():
    server = ktl.cache('kbes')

    say("Homing blue exchanger rotator")
    server['grhome'].write(1)

    # wait for the rotator to start moving
    say("Waiting for grating rotator to start moving")
    moving = ktl.Expression('$kbes.grstatus==Moving')
    moving.wait(timeout=20)
    say("Grating rotator is moving")
    notMoving = ktl.Expression('$kbes.grstatus=="Move complete"')
    say("Waiting for grating rotator to stop moving")
    notMoving.wait(timeout=300)
    say("The grating rotator has stopped moving")
    say("Checking if the grating rotator is initialized")
    homed = ktl.Expression('$kbes.grhomed==1')
    homed.wait(timeout=300)
    say("Grating rotator successfully initialized")

def homeKBMS():
    server = ktl.cache('kbms')

    say("Homing blue focus state")
    server['fochome'].write(1)

    # wait for the rotator to start moving
    say("Waiting for blue focus stage to start moving")
    moving = ktl.Expression('$kbms.focstatus==Moving')
    moving.wait(timeout=20)
    say("Blue focus stage is moving")
    notMoving = ktl.Expression('$kbms.focstatus==OK')
    say("Waiting for blue focus stage to stop moving")
    notMoving.wait(timeout=300)
    say("The blue focus stage has stopped moving")
    say("Checking if the blue focus stage is initialized")
    homed = ktl.Expression('$kbms.fochomed==1')
    homed.wait(timeout=300)
    say("Blue focus stage successfully initialized")

    



def homeServer(serverDict, mode=None):
    
    if mode == 'report':

        if len(serverDict)==0:
            return 0

        stagesToHome = 0

        # check status
        for key in serverDict:
            stage = serverDict[key]
            homed = int(stage[1].read())
            if homed==0:
                stagesToHome = stagesToHome+1
            say("%-20s %1d" % (stage[3],homed))
        return stagesToHome

    if mode == None:

        if len(serverDict)==0:
            return

        # home
        for key in serverDict:
            stage = serverDict[key]
            homed = int(stage[1].read())
            if True: #homed==0:
                say("Homing stage .. %s" % (stage[3]))
                stage[2].write("1")
                stage_homed = '$'+str(stage[0])+"."+str(stage[1].name)+'=='+str(1)
                stage_homed = ktl.Expression(stage_homed)
                stage_homed.wait(timeout=180)
                say("Stage: %s successfully homed" % (stage[3]))
                time.sleep(5)
                


def kcwiHome():
    """
    Check the homing status of a list of stages
    """

    #from multiprocessing import Pool, Process
    import threading

    #return
    # start building the dictionaries (one per server)
    kbms_dict = {}
    kbes_dict = {}

    # kbms
    kbms = ktl.cache('kbms')
    fochomed = kbms['fochomed']
    fochome  = kbms['fochome']

    # kbes
    kbes = ktl.cache('kbes')
    grhomed = kbes['grhomed']
    grhome = kbes['grhome']


    # other servers...


    # now build the dictionary
    # format is "server",keyword_status, keyword_home,Name


    kbms_dict['foc'] = ['kbms',fochomed,fochome, "Blue camera focus"]

    kbes_dict['grot'] = ['kbes',grhomed,grhome,"Blue grating rotator"]


    # servers list

    servers = [kbms_dict, kbes_dict]

    # report status
    stagesToHome=[]
    say("%-20s %s" % ("Stage","Homed"))
    
    for server in servers:

        stagesToHome.append(homeServer(server, mode='report'))


    if sum(stagesToHome)>0:
        say("Some of the KCWI stages need to be homed")
        question = "Would you like to home them (Y/N)?"
        reply = ""
        while reply not in ['y','n','Y','N']:
            reply = str(raw_input(question)).lower().strip()

    if sum(stagesToHome)==0:
        say("All the KCWI stages are homed")
        question = "Would you like to home them anyway (Y/N)?"
        reply = ""
        while reply not in ['y','n','Y','N']:
            reply = str(raw_input(question)).lower().strip()

    if reply in ['y','Y']:
            say("Homing stages (all servers in parallel)")
            #p = Pool()
            #p.map(homeServer,servers)
            #p.close()
            #p = Process(target=homeServer, args=servers)
            #p.start()
            #p.join()
            threads=[]
            for server in servers:
                t = threading.Thread(target=homeServer, args=(server,))
                threads.append(t)
                t.start()
                t.join()

            #for server in servers:
            #    homeServer(server)


    else:
        say("All stages are homed")


    focusb("-1.85",move=True)




    
def kcwiPowerDown():

    finalMessage = ""
    host = os.environ['HOST']
    user = os.environ['USER']


    if is_in_filling_position == True:
        bigmessage("KCWI is in CRYO FILL position and cannot be shutdown")
        sys.exit(0)

    say("User %s" % (user))
    say("Host %s" % (host))
    if host != 'kcwiserver' or user != 'kcwirun':
        bigmessage("Warning: This script can only be run as 'kcwirun' on 'kcwiserver'")
        sys.exit(0)


    say("You are initiating a power down of KCWI")
    bigmessage("This script will shutdown the software and the mechanisms")

    question= "Are you sure you want to continue (y/n) ?"
    reply = ""
    while reply not in ['y','n']:
          reply = str(raw_input(question)).lower().strip()
          if reply=='n':
                say("Ok. Exiting...")
                sys.exit(0)


    #bigmessage("Checking status of Exchanger stages")
    #kcwiHome()

    bigmessage("Step 1 : Park Blue Exchanger")
    from Blue import filterb,gratingb
    try:
        filterb(target="None",move=True)
        gratingb(target="None",move=True)
    except:
        say("There was a problem parking the blue exchanger")
        say("Most likely, this is because the stages are not homed correctly")
        say("The script can continue but it would be a good idea to email your SA for tonight")
        finalMessage += "Please let SA know that the blue exchanger could not be parked\n"

    say("Verify that Blue Exchanger is parked")
    filter_result = filterb()
    if filter_result != "None":
        say("The blue side filter is not in the park position")
        say("Most likely, this is because the stages are not homed correctly")
        say("The script can continue but it would be a good idea to email your SA for tonight")
        finalMessage += "Please let SA know that the blue filter could not be parked\n"
        time.sleep(10)
    else:
        say("Filter: Parked")
    grating_result = gratingb()
    if filter_result != "None":
        say("The blue side filter is not in the park position")
        say("Most likely, this is because the stages are not homed correctly")
        say("The script can continue but it would be a good idea to email your SA for tonight")
        finalMessage += "Please let SA know that the blue grating could not be parked\n"
        time.sleep(10)
    else:
        say("Grating: Parked")
    
    bigmessage("Step 2: Turn off Vac-Ion high voltage")
    hvon = ktl.cache("kbvs","HVON")
    highvoltage = hvon.read()
    if hvon == 1:
        pumpstop = ktl.cache("kbvs","PUMPSTOP")
        pumpstop.write(1)
    say("Verify that Vac-Ion pump is off")
    highvoltage = hvon.read()
    if highvoltage != "0":
        say("The Vac-Ion pump is still on")
        say("Please turn off the Vac-Ion pump manually and try again")
        say("The command is:")
        say("> modify -s kbvs pumpstop=1")
        sys.exit(0)
    else:
        say("Vac-Ion: OFF")

    bigmessage("Step 3: Close the front hatch (if it is powered on)")

    hatch_power = ktl.cache('kp1s','pwstat7')
    if hatch_power.read() == "1":
        hatch("close")
        hatch_status = hatch()
        if hatch_status != "0":
            say("The hatch is not closed")
            say("Please close the hatch manually and try again")
            say("The command is:")
            say("> hatch close")
            sys.exit(0)
        else:
            say("Hatch: Closed")
    else:
        bigmessage("The hatch is powered down, and might still be opened. Please check manually.")
        finalMessage += "Please let SA know that the hatch might still be open\n"

    bigmessage("Step 4: Close GUIs")
    p = subprocess.Popen("ctx | grep Gui",shell=True,stdout=subprocess.PIPE)
    data = p.stdout.read()
    lines = data.split("\n")
    for line in lines:
        elements = line.split()
        if len(elements)>0:
            if elements[0] != "":
                say("Closing GUI: %s" % (elements[3]))
                p1 = subprocess.Popen(["kill","-15",elements[1]])
                p1_status = p1.wait()
                say("Return status: %s" % (str(p1_status)))
                if p1_status > 0:
                    bigmessage("One of the GUIs cannot be closed")
                    say("Please close the GUI manually after running the script")
                    say("The gui is %s and it is run as %s with PID %s\n" % (elements[3],elements[0],elements[1]))
                    finalMessage += "Run this: \n"
                    finalMessage += "> ssh -l %s kcwiserver kill -15 %s\n" % (elements[0],elements[1])
                    time.sleep(5)
    bigmessage("Step 5: Stop Watch Rotator Daemon")
    p = subprocess.Popen("kcwi stop watchrot", shell=True)
    p.wait()

    bigmessage("Step 6: Stop Keygrabber")
    p = subprocess.Popen("kcwi stop keygrabber", shell=True)
    p.wait()

    bigmessage("Step 7: Stop Global Server")
    p = subprocess.Popen("kcwi stop kcwi", shell=True)
    p.wait()

    bigmessage("Step 8: Power down the detector")
    ccdpower = ktl.cache("kbds","CCDPOWER")
    ccdpower.write(0)
    say("Verify that the power is off")
    if ccdpower.read() != "0":
        bigmessage("Failed to turn off CCD power")
        say("Please turn off CCD power manually and try again")
        say("The command is:")
        say("> modify -s kbds ccdpower=0")
        say("If this does not work, somebody might be using the detector. Please call an SA.")
        sys.exit(0)
    else:
        say("CCD power: OFF")

    bigmessage("Step 9: Shut down servers (except power servers)")
    for server in ["kbds","kfcs","kros","kcas","kbms","kbes","kbgs","kbvs","kt1s","kt2s"]:
        p = subprocess.Popen(["kcwi","stop",server])
        

    bigmessage("Step 10: Power down mechanisms")
    # hatch
    bigmessage("         Power down hatch")
    kcwiPower(1,7,"off")
    # cal lamps
    bigmessage("         Power down calibration lamps")
    kcwiPower(3,1,"off")
    # galils
    bigmessage("         Power down GALILs")
    kcwiPower(2,7,"off")
    kcwiPower(3,8,"off")
    kcwiPower(1,2,"off")
    # detector
    bigmessage("         Power down Detector")
    kcwiPower(2,2,"off")
    # pressure
    bigmessage("         Power down pressure gauge and VacIon")
    kcwiPower(1,5,"off")
    kcwiPower(1,6,"off")
    #shutter
    bigmessage("         Power down shutter")
    kcwiPower(1,8,"off")
    # lantronix
    bigmessage("         Power down Lantronix terminal server")
    kcwiPower(2,5,"off")
    # lakeshore
    bigmessage("         Power down Lakeshore temperature controller")
    kcwiPower(2,4,"off")
    kcwiPower(1,4,"off")
    # autofill system
    bigmessage("         Power down AutoFill system")
    kcwiPower(2,3,"off")
    # glycol pump
    bigmessage("         Power down Glycol pump")
    kcwiPower(1,3,"off")
    # focal plane camera
    bigmessage("         Power down Focal Plane Camera")
    kcwiPower(1,1,"off")


    bigmessage("Step 11: Shut down power servers")
    for server in ["kp1s","kp2s","kp3s"]:
        p = subprocess.Popen(["kcwi","stop",server])
        p.wait()


    say("Power down sequence is finished")
    bigmessage("You can power down the electronics cabinet")

    if finalMessage != "":
        say("There were a few issues that require attention:")
        sys.stdout.write(finalMessage)



def kcwiPowerUp():
    say("#################################################################################")
    say("You are initiating a power up of KCWI")
    say("This script will the mechanisms")
    say("Before running this script, make sure that is instrument has power")
    say("and that the electronic cabinet switch is turned on")
    say("#################################################################################")
    question= "Are you sure you want to continue (y/n) ?"
    reply = ""
    while reply not in ['y','n']:
          reply = str(raw_input(question)).lower().strip()
          if reply=='n':
                say("Ok. Exiting...")
                sys.exit(0)


    bigmessage("Step 1: Verify communication with private network")
    is_device_up("kcwiprivate",30)

    bigmessage("Step 2: Verify communication with Eaton power strips")
    is_device_up("eaton",30)
    is_device_up("eaton2",30)
    is_device_up("eaton3",30)

    bigmessage("Step 3: Start power servers")
    for server in ['kp1s','kp2s','kp3s']:
        p = subprocess.Popen(['kcwi','start',server])
        p.wait()
        time.sleep(5)
        try:
            test = ktl.cache(server,"LASTALIVE")
        except:
            bigmessage("%s could not be started" % (server))
            bigmessage("Please start %s manually and try again" % (server))
            sys.exit(0)


    bigmessage("Step 4: Power up electronics and mechanisms")
    bigmessage("        Power up Lakeshore temperature controller")
    # lakeshore
    kcwiPower(2,4,"on")
    is_device_up("lakeshore",30)
    kcwiPower(1,4,"on")
    is_device_up("lakeshore2",30)
    # lantronix
    bigmessage("        Power up Lantronix terminal server")    
    kcwiPower(2,5,"on")
    bigmessage("        Checking if Lantronix is online")
    lantronix_alive = False
    lantronix_alive = is_device_up("lantronix",30)
    max_trials = 3
    trials = 1
    while lantronix_alive is not True:        
        bigmessage("Lantronix did not boot in 30 seconds. Trying a power cycle..(trial %d of %d)" % (trials,max_trials))
        kcwiPower(2,5,"cycle")
        lantronix_alive= is_device_up("lantronix",30)
        trials = trials + 1
        if trials>=max_trials:
            say("The Lantronix did not power up correctly. Please inform an SA")
            break

    # autofill
    bigmessage("        Power up AutoFill system")
    kcwiPower(2,3,"on")
    # pressure
    bigmessage("        Power up pressure gauge and Ion Pump")
    kcwiPower(1,5,"on")
    kcwiPower(1,6,"on")
    bigmessage("        Power up detector controller")
    # detector
    kcwiPower(2,2,"on")
    bigmessage("        Power up shutter")
    # shutter 
    kcwiPower(1,8,"on")
    bigmessage("        Power up GALILs")
    # galils
    kcwiPower(1,2,"on")
    is_device_up("magiqgalil",30)
    kcwiPower(2,7,"on")
    kcwiPower(3,8,"on")
    bigmessage("        Checking if BMS is online")
    is_device_up("bmsgalil",30)
    bigmessage("        Checking if BEX is online")
    galil_alive = False
    galil_alive = is_device_up("bexgalil",30)
    max_trials = 3
    trials = 1
    while galil_alive is not True:        
        say("BEX Galil did not boot in 30 seconds. Trying a power cycle..(trial %d of %d)" % (trials,max_trials))
        kcwiPower(2,7,"cycle")
        galil_alive= is_device_up("bexgalil",30)
        trials = trials + 1
        if trials>=max_trials:
            say("The blue exchanger Galil is not on. Please inform an SA")
            break

    # glycol pump
    bigmessage("        Power up glycol pump")
    kcwiPower(1,3,"on")
    # heat exchanger
    bigmessage("        Power up heat exchanger for electronic cabinet")
    kcwiPower(2,1,"on")
    # cal lamps
    bigmessage("        Power up calibration lamps")
    kcwiPower(3,1,"on")

    # start kcas server to be able to talk to the galil
    say("Start Calibration server to command the hatch CLOSED")
    p=subprocess.Popen('kcwi start kcas',shell=True)
    p.wait()
    time.sleep(10)
    

    # send close command to the hatch galil before powering up the hatch
    say("Commanding hatch CLOSED")
    hatch("open")
    hatch("close")

    # hatch
    bigmessage("        Power up Hatch controller")
    kcwiPower(1,7,"on")

    bigmessage("Step 5: start low level software")
    p = subprocess.Popen(['kcwiStartLLSoftware'])
    p.wait()

    bigmessage("Step 6: Turn on Vac-Ion high voltage")
    say("        Checking for safe pressure to turn on Ion Pump")
    pgpress = ktl.cache("kbgs","PGPRESS")
    pressure = float(pgpress.read())
    if pressure>0.001:
        say("The pressure in the dewar is too high. The current pressure (%s) exceeds the limit of 0.001." % (pressure))
        say("The Ion Pump will *NOT* be turned on.")
        say("This is an urgent condition: please inform an SA as soon as possible")
    else:
        pumpstart = ktl.cache("kbvs","PUMPSTART")
        pumpstart.write(1)
        time.sleep(5)
        say("Verify that Vac-Ion pump is on")
        hvon = ktl.cache("kbvs","HVON")
        if hvon.read() != "1":
               bigmessage("The Vac-Ion pump is still off")
               say("Please turn on the Vac-Ion pump manually and try again")
               say("The command is:")
               say("> modify -s kbvs pumpstart=1")
               say(" and the status of the pump can be verified with:")
               say("> show -s kbvs hvon")
               say("which should report > 1 < ")
               say("This is an urgent condition: please inform an SA as soon as possible if the pump cannot be started")
               sys.exit(0)
        else:
               say("Vac-Ion: ON")


    bigmessage("Step 7: Power up the detector")
    ccdpower = ktl.cache("kbds","CCDPOWER")
    ccdpower.write(1)
    say("Verify that the power is on")
    if ccdpower.read() != "1":
        say("Failed to turn on CCD power")
        say("Please turn on CCD power manually and try again")
        say("The command is:")
        say("> modify -s kbds ccdpower=1")
        sys.exit(0)
    else:
        say("CCD power: ON")

    bigmessage("KCWI is powered up. Please run testAll to verify functionality.")
    say("Most of the calibration and BMS stages are not initialized.")
    say("If the instrument is on sky today, run kcwiHomeStages and kcwiHomeCalUnit.")


        

