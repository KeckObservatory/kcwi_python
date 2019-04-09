#from . import Version
#Version.append('$Revision: 85432 $')
#del Version
"""
.. module:: Calibration
"""

import ktl
import os, sys, time
import logging as lg

from Helper import setupMonitoring, checkInitialValues,say, checkIfMoveIsPossible, changeMoveMode, checkSuccess, ProgressBar, AnimatedProgressBar, ProgressCallback

# timeout on starting the move
timeOutMove = 20
# timeout on completing the move
timeOutComplete = 60
# standard width for terminals (used for progress bar)
standardWidth = 80
   
def image_slicer(target=None, move=True, quiet=False):
    """
    Reads or set the image slicer

    Parameters
    ----------
    target : string
        Desired slicer. Values are: "Small", "Medium", "Large", "FPCam", "Aux"
    move : boolean
        Set to false to only modify the target without moving the slicer
    quiet : boolean
        Set to disable progress bar

    Examples
    --------
    Prints the name of the current slicer

    >>> Calibration.image_slicer()

    Insert the small image slicer

    >>> Calibration.image_slicer(target="Small")

    Modify the slicer target keyword but do not move

    >>> Calibration.image_slicer(target="Medium", move=False)

    """
    server = 'kcas'
    ifuname = ktl.cache(server, 'IFUNAME')   # current slicer
    ifutargn = ktl.cache(server, 'IFUTARGN') # target slicer
    ifumove = ktl.cache(server, 'IFUMOVE')   # initiate the move
    ifustatus = ktl.cache(server, 'IFUSTATUS') # values?

    monitoredKeywords = (ifuname, ifutargn, ifustatus, ifumove)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current slicer
    if target==None:
        slicer = ifuname.ascii
        lg.info("kcwiServer: Returning slicer value '%s'" %slicer)
        return slicer

    # if the requested target is the same as the current, do not move
    if target.upper()==ifuname.ascii.upper() and move==True:
        say("IFU: Target is the same as requested. No move needed.")
        slicer = ifuname.ascii
        return slicer

    # check if move is possible
    checkIfMoveIsPossible(ifustatus)

    # initiate the move
    ifutargn.write(target)
    say("Setting target to %s" % (target))

    # if move is True, then force a move
    if move==True:
        ifumove.write(1)

        # fmove expressions
        moving        = '$kcas.ifumove == 1'
        not_moving    = '$kcas.ifumove == 0'
        target_reached = '$kcas.ifuname == $kcas.ifutargn'

        moving = ktl.Expression(moving)
        not_moving = ktl.Expression(not_moving)
        target_reached = ktl.Expression(target_reached)

        # wait for moving
        result = moving.wait(timeout = timeOutMove)
        if not quiet:
            p = AnimatedProgressBar(end=100, width=standardWidth)
            ktl.monitor(server,'IFUPROG',ProgressCallback,p)

        if result == False:
            raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("Slicer", timeOutMove))

        # wait for not moving
        not_moving.wait(timeout=timeOutComplete+300)

        # check for successful move
        time.sleep(4)
        checkSuccess(statusKeyword=ifustatus, mechanism="Slicer", targetReachedExpression=target_reached, successStatus="OK")
        slicer = ifuname.ascii
        return slicer


def polarizer(target=None, move=True, quiet=False):
    """
    Reads or modify the position of the polarizer


    Parameters
    ----------
    target : string
        Desired position. Valid values are: "Sky", "Polar", "Lens"
        "Lens" refers to the hexagonal pupil

    move : boolean
        Set to false to only modify the target without moving the polarizer
    quiet : boolean
        Set to disable progress bar


    Examples
    --------
    Prints the position of the polarizer

    >>> Calibration.polarizer()

    Set the polarizer to Polar

    >>> Calibration.polarizer(target="Polar")

    Set the target for the polarizer to Sky but do not move

    >>> Calibration.polarizer(target="Sky", move=False)

    """

    server = 'kcas'
    calpname = ktl.cache(server, 'CALPNAME')   # current 
    calptargn = ktl.cache(server, 'CALPTARGN') # target 
    calpmove = ktl.cache(server, 'CALPMOVE')   # initiate the move
    calpstatus = ktl.cache(server, 'CALPSTATUS') # values?

    monitoredKeywords = (calpname, calptargn,calpmove,calpstatus)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current slicer
    if target==None:
        pupil = calpname.ascii
        lg.info("kcwiServer: Returning pupil lens value '%s'" % (pupil))
        return pupil

    # if the requested target is the same as the current, do not move
    if target.upper()==calpname.ascii.upper() and move==True:
        say("Pupil: Target is the same as requested. No move needed.")
        return

    # check if move is possible
    checkIfMoveIsPossible(calpstatus)

    # initiate the move
    calptargn.write(target)

    # if move is True, then force a move
    if move==True:
        calpmove.write(1)
        if not quiet:
            p = AnimatedProgressBar(end=100, width=standardWidth)
            ktl.monitor(server,'CALPPROG',ProgressCallback,p)
        # fmove expressions
        moving        = '$kcas.calpmove == 1'
        not_moving    = '$kcas.calpmove == 0'
        target_reached = '$kcas.calpname == $kcas.calptargn'

        moving = ktl.Expression(moving)
        not_moving = ktl.Expression(not_moving)
        target_reached = ktl.Expression(target_reached)

        # wait for moving
        result = moving.wait(timeout = timeOutMove)
        if result == False:
            raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("Cal Pupil", timeOutMove))

        # wait for not moving
        not_moving.wait(timeout=timeOutComplete)

        # check for successful move
        time.sleep(2)
        checkSuccess(statusKeyword=calpstatus, mechanism="Cal Pupil", targetReachedExpression=target_reached, successStatus="OK")

## POLARIZER
def polangle(angle=None, move=True, quiet=True):
    """
    Reads or modify the angle of the polarizer

    Parameters
    ----------
    angle : float
        Desired angle. 
    move : boolean
        Set to false to only modify the target without moving the polarizer angle
    quiet : boolean
        Set to disable progress bar

    Examples
    --------
    Prints the current polarizer angle

    >>> Calibration.polangle()

    Set the angle to 90 degrees

    >>> Calibration.polangle(target=90)

    Set the target angle for the polarizer to 180 but do not move

    >>> Calibration.polangle(target=180, move=False)

    """
    server = 'kcas'
    callangle = ktl.cache(server, 'CALLANGLE')   # current 
    calltarga = ktl.cache(server, 'CALLTARGA') # target 
    callmove = ktl.cache(server, 'CALLMOVE')   # initiate the move
    callstatus = ktl.cache(server, 'CALLSTATUS') # values?
    calltol = ktl.cache(server,'CALLTOL') # tolerance in counts for angle 
    callenc = ktl.cache(server,'CALLENC') # encoder value
    calltargenc = ktl.cache(server,'CALLTARGENC') # requested encoder value
    callprog = ktl.cache(server,'CALLPROG') # progress
    monitoredKeywords = (callangle, calltarga, callmove, callstatus, calltol, callenc, calltargenc)


    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current angle
    if angle==None:
        result = callangle.ascii
        lg.info("kcwiServer: Returning linear polarizer angle value '%s'" % (result))
        return result


    # if the requested target is the same as the current, do not move
    if abs(float(angle)-calltarga)<0.11 and move==True:
        say("Cal Angle: Target is the same as requested. Curangle '%s'." % (angle))
        return

    # check if move is possible
    checkIfMoveIsPossible(callstatus)

    # initiate the move
    calltarga.write(angle)

    # if move is True, then force a move
    if move==True:
        callmove.write(1)

        # fmove expressions
        moving        = '$kcas.callmove == 1'
        not_moving    = '$kcas.callmove == 0'
        #target_reached = 'abs($kcas.callangle - $kcas.calltarga) < 1'

        moving = ktl.Expression(moving)
        not_moving = ktl.Expression(not_moving)
        #target_reached = ktl.Expression(target_reached)

        # wait for moving
        result = moving.wait(timeout = timeOutMove)
        if not quiet:
            p = AnimatedProgressBar(end=100, width=standardWidth)
            ktl.monitor(server,'CALLPROG',ProgressCallback,p)


        if result == False:
            raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("Linear Polarizer", timeOutMove))

        # wait for not moving
        not_moving.wait(timeout=timeOutComplete)

        # check for successful move
        time.sleep(2)
        checkSuccess(statusKeyword=callstatus, mechanism="Linear Polarizer", targetReachedExpression=None, successStatus="OK")
        if abs(callenc - calltargenc) > calltol:
            say("Warning: The required encoder precision has NOT been reached")

# CAL MIRROR
def cal_mirror(position=None, move=True, quiet=False):
    """
    Reads or set the calibration mirror position

    Parameters
    ----------
    position : string
        Desired position. Valid values are "Mirror", "Sky", or "Filter"
    move : boolean
        Set to False to only set the target without moving
    quiet : boolean
        Set to disable progress bar

    Examples
    --------

    Set the current calibration mirror to Sky

    >>> Calibration.cal_mirror(position="Sky")

    Set the target for the calibration mirror to Filter but don't move it

    >>> Calibration.cal_mirror(position="Filter", move=False)

    """
    server = 'kcas'
    calmname = ktl.cache(server, 'CALMNAME')   # current 
    calmtargn = ktl.cache(server, 'CALMTARGN') # target 
    calmmove = ktl.cache(server, 'CALMMOVE')   # initiate the move
    calmstatus = ktl.cache(server, 'CALMSTATUS') # values?

    monitoredKeywords = (calmname, calmtargn, calmmove, calmstatus)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current slicer
    if position==None:
        result = calmname.ascii
        lg.info("kcwiServer: Returning calibration mirros position '%s'" % (result))
        return result

    # if the requested target is the same as the current, do not move
    if position.upper()==calmname.ascii.upper() and move==True:
        say("Cal Mirror: Target is the same as requested. No move needed.")
        return

    # check if move is possible
    checkIfMoveIsPossible(calmstatus)

    # initiate the move
    calmtargn.write(position)

    # if move is True, then force a move
    if move==True:
        calmmove.write(1)

        # fmove expressions
        moving        = '$kcas.calmmove == 1'
        not_moving    = '$kcas.calmmove == 0'
        target_reached = '$kcas.calmname == $kcas.calmtargn'

        moving = ktl.Expression(moving)
        not_moving = ktl.Expression(not_moving)
        target_reached = ktl.Expression(target_reached)

        # wait for moving
        result = moving.wait(timeout = timeOutMove)
        if result == False:
            raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("Calibration Mirror", timeOutMove))

        # wait for not moving
        not_moving.wait(timeout=timeOutComplete+120)

        time.sleep(2)
        checkSuccess(statusKeyword=calmstatus, mechanism="Calibration Mirror", targetReachedExpression=target_reached, successStatus="OK")
        say("%s successfully set to %s" % ("Calibration Mirror", position))


# HEX_PUPIL
def hex_pupil(position=None, move=True, quiet=False):
    """
    Reads or set the hex pupil position

    Parameters
    ----------
    position : string
        Desired position. Valid values are "Home", "Flat", "Point", "Zero"
    move : boolean
        Set to False to only set the target without moving
    quiet : boolean
        Set to disable progress bar

    Examples
    --------

    Set the current hex pupil

    >>> Calibration.hex_pupil(position="Flat")

    Set the target for the hex pupil to Flat but don't move it

    >>> Calibration.hex_pupil(position="Flat", move=False)

    """
    server = 'kcas'
    calhname = ktl.cache(server, 'CALHNAME')   # current 
    calhtargn = ktl.cache(server, 'CALHTARGN') # target 
    calhmove = ktl.cache(server, 'CALHMOVE')   # initiate the move
    calhstatus = ktl.cache(server, 'CALHSTATUS') # values?

    monitoredKeywords = (calhname, calhtargn, calhmove, calhstatus)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current slicer
    if position==None:
        result = calhname.ascii
        lg.info("kcwiServer: Returning hex pupil position '%s'" % (result))
        return result

    # if the requested target is the same as the current, do not move
    if position.upper()==calhname.ascii.upper() and move==True:
        say("Hex Pupil: Target is the same as requested. No move needed.")
        return

    # check if move is possible
    checkIfMoveIsPossible(calhstatus)

    # initiate the move
    calhtargn.write(position)

    # if move is True, then force a move
    if move==True:
        calhmove.write(1)

        # fmove expressions
        moving        = '$kcas.calhmove == 1'
        not_moving    = '$kcas.calhmove == 0'
        target_reached = '$kcas.calhname == $kcas.calhtargn'

        moving = ktl.Expression(moving)
        not_moving = ktl.Expression(not_moving)
        target_reached = ktl.Expression(target_reached)

        # wait for moving
        result = moving.wait(timeout = timeOutMove)
        if result == False:
            raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("Hex Pupil", timeOutMove))

        # wait for not moving
        not_moving.wait(timeout=timeOutComplete)

        time.sleep(2)
        checkSuccess(statusKeyword=calhstatus, mechanism="Hex Pupil", targetReachedExpression=target_reached, successStatus="OK")
        say("%s successfully set to %s" % ("Hex Pupil", position))

# CAL XY
def cal_object(position=None, move=True, quiet=False):
    """
    Reads or set the calibration object

    Parameters
    ----------
    position : string
        Desired position. Valid values are:
        Pin300, Pin500
        FinBars, MedBarsA, MedBarsB, LrgBarsA, LrgBarsB
        DiagLin, HorLin
        FlatA, FlatB
        Dark, Tpat, MIRA

    move : boolean
        Set to False to only set the target without moving
    quiet : boolean
        Set to disable progress bar

    Examples
    --------

    Set the current calibration object stage to Pin300

    >>> Calibration.cal_object(position="Pin300")

    """
    server = 'kcas'
    calxname = ktl.cache(server, 'CALXNAME')   # current 
    calxtargn = ktl.cache(server, 'CALXTARGN') # target 
    calxmove = ktl.cache(server, 'CALXMOVE')   # initiate the move
    calxstatus = ktl.cache(server, 'CALXSTATUS') # values?
    calyname = ktl.cache(server, 'CALYNAME')   # current 
    calytargn = ktl.cache(server, 'CALYTARGN') # target 
    calymove = ktl.cache(server, 'CALYMOVE')   # initiate the move
    calystatus = ktl.cache(server, 'CALYSTATUS') # values?

    calxtargenc = ktl.cache(server, 'CALXTARGENC') # target encoder
    calxenc = ktl.cache(server, 'CALXENC')   # current encoder
    calxtol = ktl.cache(server, 'CALXTOL') # encoder tolerance
    calytargenc = ktl.cache(server, 'CALYTARGENC') # target 
    calyenc = ktl.cache(server, 'CALYENC')   # initiate the move
    calytol = ktl.cache(server, 'CALYTOL') # encoder tolerance

    monitoredKeywords = (calxname, calxtargn, calxmove, calxstatus, calyname, calytargn, calymove, calystatus, calxtargenc, calxenc, calxtol, calytargenc, calyenc, calytol)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current slicer
    if position==None:
        resultx = calxname.ascii
        resulty = calyname.ascii
        if resultx == resulty:
            lg.info("kcwiServer: Returning CAL Object position '%s'" % (resultx))
            return resultx
        else:
            return "Inconsistent values"


    # if the requested target is the same as the current, do not move
    if position==calxname.ascii and position==calyname.ascii and move==True:
        say("Cal XY: Target is the same as requested. No move needed.")
        return

    # check if move is possible
    checkIfMoveIsPossible(calxstatus)
    checkIfMoveIsPossible(calystatus)

    # initiate the move
    calxtargn.write(position)
    calytargn.write(position)

    # if move is True, then force a move
    if move==True:
        # fmove expressions
        movingx        = '$kcas.calxmove == 1'
        not_movingx    = '$kcas.calxmove == 0'
        target_reachedx = '$kcas.calxname == $kcas.calxtargn'
        movingy        = '$kcas.calymove == 1'
        not_movingy    = '$kcas.calymove == 0'
        target_reachedy = '$kcas.calyname == $kcas.calytargn'

        movingx = ktl.Expression(movingx)
        not_movingx = ktl.Expression(not_movingx)
        target_reachedx = ktl.Expression(target_reachedx)
        movingy = ktl.Expression(movingy)
        not_movingy = ktl.Expression(not_movingy)
        target_reachedy = ktl.Expression(target_reachedy)

        # wait for moving
        say("Moving X stage...")
#       if calxname != position:
        if abs( int(calxtargenc.read())-int(calxenc.read())) > calxtol:
            calxmove.write(1)
            time.sleep(2)

            #print calxenc
            #print calxtargenc
            #print movingx 
#           result = movingx.wait(timeout = timeOutMove)
#  The above line has been causing problems. removed 160903 (temporarily?)
            result = True
            if not quiet:
                p = AnimatedProgressBar(end=100, width=standardWidth)
                ktl.monitor(server,'CALXPROG',ProgressCallback,p)
            if result == False:
                raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("CAL X", timeOutMove))
            # wait for not moving
            not_movingx.wait(timeout=timeOutComplete)
            time.sleep(5)
        else:
            say("X stage move is not needed")

        # wait for moving
        say("Moving Y stage...")
#       if calyname != position:
        if abs( int(calytargenc.read()) - int(calyenc.read())) > calytol:
            calymove.write(1)

            result = movingy.wait(timeout = timeOutMove)
            if not quiet:
                p = AnimatedProgressBar(end=100, width=standardWidth)
                ktl.monitor(server,'CALYPROG',ProgressCallback,p)
            if result == False:
                raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("CAL Y", timeOutMove))
            # wait for not moving
            not_movingy.wait(timeout=timeOutComplete)

            time.sleep(5)
        else:
            say("Y stage move is not needed")

        #checkSuccess(statusKeyword=calxstatus, mechanism="CAL X", targetReachedExpression=target_reachedx, successStatus="OK")
        #say("%s successfully set to %s" % ("CAL X", position))
        #checkSuccess(statusKeyword=calystatus, mechanism="CAL Y", targetReachedExpression=target_reachedy, successStatus="OK")
        #say("%s successfully set to %s" % ("CAL Y", position))
        return calxname.ascii


# CAL LAMPS
def lamp(lamp=None, action=None):
    """
    Turn on/off or query status of calibration lamps

    Parameters
    ----------
    lamp : string
        Lamp name. Valid values are "thar","fear","continuum|led", and "all"
        Abbreviated and capitalized names are ok.

    action: on/off/status
        On:  Turns on
        Off: Turns off
        If action is missing, the status is returned.

    Examples
    --------

    Turn on the Iron Argon lamp:

    >>> Calibration.lamp("fear","on")

    """
    server = 'kcas'
    #lamp0name = ktl.cache(server, 'LAMP0NAME')   
    #lamp1name = ktl.cache(server, 'LAMP1NAME')   
    #lamp3name = ktl.cache(server, 'LAMP3NAME')   
    lamp0status = ktl.cache(server, 'LAMP0STATUS')   
    lamp1status = ktl.cache(server, 'LAMP1STATUS')   
    lamp3status = ktl.cache(server, 'LAMP3STATUS')   
    lampsoff = ktl.cache(server,'LAMPSOFF')
    
    monitoredKeywords = (lamp0status, lamp1status, lamp3status, lampsoff)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # capitalize

    if lamp is not None:
        lamp =  lamp.upper()
    if action is not None:
        action = action.upper()

    # decide which keywords to use

    if lamp in ("THAR","THA","TH","T","1", "thar","tha","th","t"):
        statusKeyword = lamp1status
    if lamp in ("FEAR","FEA","FE","F","0","fear","fea","fe","f"):
        statusKeyword = lamp0status
    if lamp in ("CONTINUUM","CONT","CON","LED","3", "continuum","cont","con","led"):
        statusKeyword = lamp3status

    # act
    statusArray = (lamp0status,lamp1status,lamp3status)

    if action == "ON":
        if lamp == "ALL":
            say("Turning on all lamps")
            for statusKeyword in statusArray :

                statusKeyword.write(1)

        else:
            say("Turning on %s lamp" % (lamp))

            statusKeyword.write(1)


    if action == "OFF":
        if lamp == "ALL":
            say("Turning off all lamps")
            for statusKeyword in statusArray:
                statusKeyword.write(0)
        else:
            say("Turning off %s lamp" % (lamp))
            statusKeyword.write(0)

    if action != "None":
        time.sleep(3)

    # get status
    
    if action == None and lamp != None:

        if lamp == "ALL":
            say("Cannot retrieve status of multiple lamps")
            return

        status = statusKeyword.read()
        return status

# CAL LAMPS SHUTTER
def lamp_shutter(lamp=None, action=None):
    """
    Open/Close or query status of calibration lamps shutter

    Parameters
    ----------
    lamp : string
        Lamp name. Valid values are "thar","fear","continuum|led", and "all"
        Abbreviated and capitalized names are ok.

    action: open/close/status
        Open
        Close
        If action is missing, the status is returned.

    Examples
    --------

    Open the Iron Argon lamp shutter:

    >>> Calibration.lamp_shutter("fear","open")

    """
    server = 'kcas'

    lamp0shstat = ktl.cache(server, 'LAMP0SHSTAT')   
    lamp1shstat = ktl.cache(server, 'LAMP1SHSTAT')   
    
    monitoredKeywords = (lamp0shstat,lamp1shstat)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # capitalize

    lamp = lamp.upper()
    action = action.upper()

    # decide which keywords to use

    if lamp in ("THAR","THA","TH","T","1"):
        statusKeyword = lamp1shstat
    if lamp in ("FEAR","FEA","FE","F","0"):
        statusKeyword = lamp0shstat

    if action != "":
        time.sleep(3)

    if action == "OPEN":
        statusKeyword.write(1)

    if action == "CLOSE":
        statusKeyword.write(0)

    # get status
    
    if action == "":

        status = statusKeyword.read()
        return status

                

def hatch(status=None):
    """
    Open or close the instrument hatch

    Parameters
    ----------
    status : string
        open or close

    Examples
    --------
    Open the instrument hatch

    >>> Calibration.hatch(status="open")


    """
    server = 'kcas'
    hatchstatus = ktl.cache(server, 'HATCHSTATUS')
    hatchpos = ktl.cache(server,"HATCHPOS")

    monitoredKeywords = (hatchstatus, hatchpos)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)
    #hatchstatus.monitor()

    # if called with an empty string, return the current slicer
    if status==None:
        return hatchstatus.read()

    # initiate the move
    if status in ["open","OPEN",1,"1","Open"]:
        requested = 1
    if status in ["close","CLOSE",0,"0","Closed"]:
        requested = 0

    # if the requested position is the same as the current, do not move
    if requested==int(hatchstatus.ascii):
        say("Hatch: Target is the same as requested. No move needed.")

    # check if move is possible
    # probably not necessary for the hatch
    #checkIfMoveIsPossible(ifustatus)

    hatchstatus.write(requested)
    say("Setting Hatch to %s" % (status))

    target_reached = '$kcas.hatchstatus == '+str(requested)

    target_reached = ktl.Expression(target_reached)

    # wait for target reached
    target_reached.wait(timeout=10)

    return hatchstatus
