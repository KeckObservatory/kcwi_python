
#from . import Version
#Version.append('$Revision: 85432 $')
#del Version
"""
.. module:: Blue
"""

import ktl
import os, sys, time
import logging as lg
import math
#from multiprocessing import Process
import threading

from KCWI.Helper import setupMonitoring, checkInitialValues,say, checkIfMoveIsPossible, changeMoveMode, checkSuccess, ProgressBar, AnimatedProgressBar, ProgressCallback



def is_in_filling_position():
    kbms = ktl.cache('kbms')
    
    artfilling = kbms['artfilling']
    artlocked = kbms['artlocked']

    status = False

    if artfilling.read() == "1" or artlocked.read() == "1":
        status = True

    return status



# timeout on starting the move
timeOutMove = 20
# timeout on completing the move
timeOutComplete = 60
# standard width for terminals for progress bar
standardWidth = 80

class grating(object):
    """Grating class that contains our knowledge of the gratings"""

    gid = None      # grating id number
    name = None     # grating name
    corang = None   # correction angle (0 or 180)
    tip = None      # correction for 170508 realignment
    rho = None      # lines/micron
    d0 = None       # sine fit zeropoint  (for peak wave)
    d1 = None       # sine fit slope      (for peak wave)
    alpha = None    # angle of incidence (degrees)
    beta = None     # angle of diffraction (degrees)
    camang = None   # camera physical angle (degrees)
    grangle = None  # grating physical angle (degrees)
    cwave = None    # central wavelength (Angstroms)
    pwave = None    # peak wavelength (Angstroms)

    # Class constructor
    def __init__(self, name=None, gnum=None):

        # Mapping between names and id numbers
        grids = {"BH3": 1, "BL": 2, "BH2": 3, "BM": 4, "BH1": 5}

        # Properties of the gratings
        grprops = {1: {"name": "BH3", "corang": 180.0, "tip": 0.17, 
                       "rho": 2.8017, "d0": 7.714e-2, "d1": 1.344e-4}, 
                   2: {"name": "BL", "corang": 0.0, "tip": 0.17, 
                       "rho": 0.870,  "d0": 9.392e-2, "d1": 3.896e-5},
                   3: {"name": "BH2", "corang": 180.0, "tip": 0.17,
                       "rho": 3.2805, "d0": 8.721e-2, "d1": 1.560e-4},
                   4: {"name": "BM", "corang": 0.0, "tip": 0.17,
                       "rho": 1.901, "d0": 8.315e-2, "d1": 9.123e-5},
                   5: {"name": "BH1", "corang": 180.0, "tip": 0.17,
                       "rho": 3.3,"d0": 1.e-2,    "d1": 1.e-4}}

        # Handle both name and id entry
        gid = None
        # index on grating name (case insensitive)
        if name is not None:
            gid = grids[name.upper()]
        # index on grating id number, with range check
        elif gnum is not None:
            if gnum < 1 or gnum > 5:
                say("GRATING (object): illegal gnum = %d" % gnum)
            else:
                gid = gnum
        # Nothing entered
        else:
            say("GRATING (object): no grating specified")

        # Ready to populate grating data structure
        if gid is not None:
            self.gid = gid
            self.name = grprops[gid]['name']
            self.corang = grprops[gid]['corang']
            self.rho = grprops[gid]['rho']
            self.d0 = grprops[gid]['d0']
            self.d1 = grprops[gid]['d1']
            self.tip = 0.17

    # alpha depends only on grating angle
    def calc_alpha(self, grangle):
        return grangle - (self.corang + 13.0) + self.tip

    # set object alpha with range checking
    def set_alpha(self, alpha, quiet=False):
        if alpha > 56.1 and not quiet:
            say("GRATING: Warning - possible vignetting!")
        if alpha > 60.:
            say("GRATING: Error - alpha limited to 60 degrees!")
            alpha = 60.
        self.alpha = alpha
        # peak wavelength depends only on alpha
        pwave = self.calc_pwave(alpha)
        self.set_pwave(pwave)

    # beta depends on alpha and camera angle
    def calc_beta(self, alpha, camang):
        return camang - alpha + self.tip

    # set object beta with range checking
    def set_beta(self, beta, quiet=False):
        if abs(self.alpha - beta) < 6.5 and not quiet:
            say("GRATING: Warning - possible ghosting!")
        self.beta = beta
        # central wavelength depends on alpha and beta
        cwave = self.calc_cwave(self.alpha, beta)
        self.set_cwave(cwave)

    # set object grating angle
    def set_grangle(self, grangle):
        self.grangle = grangle

    # set object camera angle with range checking
    def set_camang(self, camang):
        if camang > 106.:
            say("GRATING: Error - camera angle limited to 106 degrees!")
            camang = 106.
        self.camang = camang

    # central wavelength depends on alpha and beta
    def calc_cwave(self, alpha, beta):
        dpr = 180.0 / math.pi
        return ( ( math.sin(alpha/dpr) + math.sin(beta/dpr) ) / 
                self.rho ) * 10000.

    # set object central wavelength
    def set_cwave(self, cwave):
        self.cwave=cwave

    # peak wavelength depends only on alpha
    def calc_pwave(self, alpha):
        dpr = 180.0 / math.pi
        return ( math.sin(alpha/dpr) - self.d0 ) / self.d1

    # set object peak wavelength
    def set_pwave(self, pwave):
        self.pwave = pwave

    def calc_from_wavelengths(self, cwave, pwave=None):
        """
        Calculate grating parameters using wavelength inputs.

        Parameters
        ----------
        cwave : float
            Desired central wavelength in Angstroms

        Keywords
        --------
        pwave : float
            Desired peak wavelength in Angstroms

        Examples
        --------

        g = Blue.grating('bh2')
        g.calc_from_wavelengths(4400., pwave=4300.)

        If pwave is not specified, it will be set to cwave

        No return values: see get_wavelengths and get_angles
        """
        cwave = float(cwave)
        if pwave is None:
            pwave = cwave
        else:
            pwave = float(pwave)
        salpha = pwave * self.d1 + self.d0
        self.set_alpha(math.degrees(math.asin(salpha)))
        # in case alpha was limited, recalculate salpha
        salpha = math.sin(math.radians(self.alpha))
        self.set_beta(math.degrees(math.asin( cwave * 1.e-4 * self.rho -
                      salpha)), quiet=True)
        self.set_grangle(self.alpha + self.corang + 13.0 - self.tip)
        self.set_camang(self.beta + self.alpha - self.tip)
        # in case camang was limited, recalculate beta
        self.set_beta(self.camang - self.alpha + self.tip)

    def get_wavelengths(self):
        """
        Returns central and peak wavelengths:

        Parameters
        ----------
        None

        Returns
        -------
        float   Central wavelength in Angstroms
        float   Peak wavelength in Angstroms
        """
        return self.cwave, self.pwave

    def calc_from_angles(self, alpha=None, beta=None, 
                         grangle=None, camang=None):
        """
        Calculate grating parameters using angle inputs.

        Keywords
        --------
        alpha : float
            Angle of incidence in degrees (paired with beta)
        beta : float
            Angle of diffraction in degrees (paired with alpha)
        grangle : float
            Grating angle in degrees (paired with camang)
        camang : float
            Camera articulation angle in degrees (paired with grangle)

        Examples
        --------

        g = Blue.grating('bh2')
        g.calc_from_angles(50.7, 42.0)   # using alpha and beta
        g.calc_from_angles(grangle=243.7, camang=92.7)   # using instrument angles

        No return values: see get_wavelengths and get_angles
        """
        if alpha is not None and beta is not None:
            self.set_alpha(alpha)
            self.set_grangle(self.alpha + (self.corang + 13.0) - self.tip)
            self.set_camang(self.alpha + beta - self.tip)
            self.set_beta(self.camang - self.alpha + self.tip)
        elif grangle is not None and camang is not None:
            self.set_camang(camang)
            self.set_grangle(grangle)
            self.set_alpha(grangle - (self.corang + 13.0) + self.tip)
            self.set_beta(self.camang - self.alpha + self.tip)
        else:
            say("GRATING: Error - must specify either alpha and beta, ")
            say("       or grangle and camang")

    def get_angles(self):
        """
        Returns alpha, beta, grangle, and camang:

        Returns
        -------
        float   Angle of incidence in degrees
        float   Angle of diffraction in degrees
        float   Grating angle in degrees
        float   Camera angle in degrees
        """
        return self.alpha, self.beta, self.grangle, self.camang



def cwaveb(cwave=None, pwave=None, move=True, quiet=False):
    """
    Show or set the central (and optionally the peak) wavelength

    Parameters
    ----------
    cwave : float
        Desired central wavelength in Angstroms    
    pwave : float
        Peak wavelength (if desired and different from cwave)
    move : boolean
        Set to false to only modify the target without moving the stages
    quiet : boolean
        Set to true to disable progress bar

    Examples
    --------

    set the central wavelength to 6700 Angstrom

    >>> Blue.cwaveb(cwave=6700)
    """

    server = 'kcwi'
    cwavetarg = ktl.cache(server,'BCWAVETARG')
    pwavetarg = ktl.cache(server,'BPWAVETARG')

    monitoredKeywords = (cwavetarg, pwavetarg)
    setupMonitoring(monitoredKeywords, wait=True)


    # retrieve the name of the current grating

    currentgrating = gratingb()

    if currentgrating == None or currentgrating == 'None':
        say("There is no grating in the beam")
        return

    # instantiate a grating object

    g = grating(currentgrating)

    if cwave is not None and is_in_filling_position() != False:
        say("KCWI might be in filling position, moves are not allowed")
        return


    if cwave is not None:
        # update target

        cwavetarg.write(cwave)
        if pwave is not None:
            pwavetarg.write(pwave)
        else:
            pwavetarg.write(cwave)

        # calculate the required angles

        g.calc_from_wavelengths(cwave=cwave, pwave=pwave)

        # camera angle
        p1 = threading.Thread(target = camangleb, args = (g.camang, True, quiet))

        # grating angle
    
        p2 = threading.Thread(target = grangleb, args = (g.grangle, True, quiet))
        p1.start()
        say("Camera motion started")
        p2.start()
        say("Grating motion started")
        p1.join()
        p2.join()

        # return values

        return cwave #, pwave #, g.camang, g.grangle

    else:

        # the function was called without a requested wavelength, 
        # so we return the calculated wavelength based on angles

        camangle = float(camangleb())
        grangle = float(grangleb())

        g.calc_from_angles(camang=camangle, grangle=grangle)

        return g.cwave #, g.pwave, camangle, grangle

def pwaveb(pwave=None, cwave=None, move=True, quiet=False):
    """
    Show or set the peak wavelength

    Parameters
    ----------
    cwave : float
        Desired central wavelength in Angstroms    
    pwave : float
        Peak wavelength 
    move : boolean
        Set to false to only modify the target without moving the stages
    quiet : boolean
        Set to true to disable progress bar

    Examples
    --------

    set the peak wavelength to 6700 Angstrom

    >>> Blue.pwaveb(pwave=6700)
    """

    server = 'kcwi'
    cwavetarg = ktl.cache(server,'BCWAVETARG')
    pwavetarg = ktl.cache(server,'BPWAVETARG')

    monitoredKeywords = (cwavetarg, pwavetarg)
    setupMonitoring(monitoredKeywords, wait=True)

    # retrieve the name of the current grating

    currentgrating = gratingb()

    if currentgrating == None or currentgrating == 'None':
        say("There is no grating in the beam")
        return

    # instantiate a grating object

    g = grating(currentgrating)

    if pwave is not None and is_in_filling_position() != False:
       say("KCWI might be in filling position, moves are not allowed")
       return

    if pwave is not None:

        pwavetarg.write(pwave)

        cwave = cwaveb()

        # calculate the required angles

        g.calc_from_wavelengths(cwave=cwave, pwave=pwave)

        # use multiprocesing to run camera and grating at the same time

        # camera angle
        camangleb(angvalue=g.camang, move=move, quiet=quiet)
        # grating angle
        grangleb(angvalue=g.grangle, move=move, quiet=quiet)
        
        # return values

        return pwave #, pwave #, g.camang, g.grangle

    else:

        # the function was called without a requested wavelength,
        # so we return the calculated wavelength based on angles

        camangle = float(camangleb())
        grangle = float(grangleb())

        g.calc_from_angles(camang=camangle, grangle=grangle)

        return g.pwave #, g.pwave, camangle, grangle



def goib(nexp, dark=False):

    """
    Take an exposure or a sequence of exposures with the blue camera.

    Parameters
    ----------
    nexp : int
        Desired number of exposure. 
    dark : boolean
        If True, do not open shutter
    imtype : string
        twiflat will set the parameters for a sky flat

    Examples
    --------
    
    Take a single exposure with the blue camera

    >>> Blue.goib(1)

    """

    numberOfExposures = int(nexp)

    # start keyword monitoring

    server = 'kbds'
    try:
        exposeip = ktl.cache(server,'EXPOSIP')
        rdoutip = ktl.cache(server,'RDOUTIP')
        loutfile = ktl.cache(server,'LOUTFILE')
        startex = ktl.cache(server,'STARTEX')
        todisk = ktl.cache(server,'TODISK')
        ttime = ktl.cache(server,'TTIME')
        autoshut = ktl.cache(server,'AUTOSHUT')
        frameno = ktl.cache(server,'FRAMENO')
        imtype = ktl.cache(server,'IMTYPE')
        groupidk = ktl.cache(server,'GROUPID')
    except:
        raise RuntimeError("Failed to read detector keywords. KBDS might not be running")

    # get the date obs
    try:
        dateobsk = ktl.cache('dcs','DATE-OBS')
        dateobs = dateobsk.read()
    except:
        dateobs = 'UNKNOWN'
        

    monitoredKeywords = (exposeip, rdoutip, loutfile, startex,
                         todisk, ttime, autoshut, frameno,imtype, groupidk)

    setupMonitoring(monitoredKeywords, wait=True)

    n = 0

    td = int(todisk['ascii'])

    # create GROUPID keyword
    groupid = "%s-%d" % (dateobs,frameno)
    groupidk.write(groupid)

    if not td:
        say("WARNING: todisk keyword prevents saving images")

        
    if dark==True and float(ttime.read())>0:
        say("Disabling autoshutter: images will be dark")
        imtype.write('DARK')
        autoshut.write(0)

    if float(ttime.read()) == 0:
        say("Exposure time is zero: images will be biases")
        imtype.write('BIAS')

    while n < numberOfExposures:

          # wait for current exposure to end
        startex.waitFor('==0')
        exposeip.waitFor('==0')
        rdoutip.waitFor('==0')
        loutstart=loutfile['ascii']
        cond = "!='"+loutfile['ascii']+"'"
        ctim = time.asctime()
        exposureTime = ttime
        imno = frameno

        say ('%s: Taking %.3f s exposure %d of %d (image # %d)' % 
             (ctim, exposureTime, int(n+1), int(numberOfExposures), imno))

        # start a new exposure

        startex.write(1)

        # wait for exposure to start
        exposeip.waitFor('==1',timeout=20)
        say("Exposing")

        # what is the exposure time?
        exposureTime=float(ttime['ascii'])

        # wait for readout
        rdoutip.waitFor('==1',timeout=exposureTime+10)
        say("Reading out")

        # wait for readout
        rdoutip.waitFor('==0',timeout=450)
        say("Readout complete")

        # only test if writing to disk
        if td:
            # wait for last file to change
            loutfile.waitFor(cond, timeout=120)

            say('Last file is: '+loutfile['ascii'])

        n=n+1

        say('Exposure sequence complete')


        if dark==True:
            autoshut.write(1)


def goifpc(nexp=1):

    """
    Take an exposure or a sequence of exposures with the focal plane camera. 
    If the keywords sequence and trigtime are set, then takes a sequence.

    Parameters
    ----------
    nexp : int
        Desired number of exposure. 

    Examples
    --------
    
    Take a single exposure with the blue camera

    >>> Blue.goifpc(1)

    """
    numberOfExposures = nexp

    # start keyword monitoring

    server = 'kfcs'
    try:
            loutfile = ktl.cache(server,'LASTFILE')
            startex = ktl.cache(server,'STARTEX')
            stopex = ktl.cache(server,'STOPEX')
            ttime = ktl.cache(server,'EXPTIME')
            status = ktl.cache(server,'STATUS')
            trigtime = ktl.cache(server,'TRIGTIME')
            sequence = ktl.cache(server,'SEQUENCE')
            counter = ktl.cache(server,'COUNTER')
            closed = ktl.cache(server,'CLOSED')
    except:
            raise RuntimeError("Failed to read detector keywords. KFCS might not be running")


    monitoredKeywords = (loutfile, startex, stopex, ttime, status,
                         trigtime, sequence, counter, closed)

    setupMonitoring(monitoredKeywords, wait=True)

    n = 0
    errcnt = 0

    # is FPC open (not closed)?

    if closed == 0:

        # main loop

        while n< numberOfExposures and errcnt < 2:

            # wait for current exposure to end
            status.waitFor('!=Busy')

            exposureTime = ttime
            imno = counter
            ctim = time.asctime()

            say ('%s: Taking %.3f s exposure %d of %d (image # %d)' %
                    (ctim, exposureTime, n+1, numberOfExposures, imno))

            # start a new exposure

            startex.write(1)

            say("Exposing")

            # what is the wait time?
            seq = sequence
            triggerTime = trigtime

            waitTime = (exposureTime+triggerTime)*seq

            if waitTime < 1:
                    waitTime = 1
            time.sleep(waitTime+1)


            status.waitFor('!=Busy')

            stat = status
            
            if stat == 'OK':
                say('Last file is: ' + loutfile['ascii'])
                say("Readout complete")
                n += 1
            else:
                say("Error reading out, aborting!")
                stopex.write(1)
                errcnt += 1

        say('Exposure sequence complete')
    else:
        say('Cannot take exposure, camera closed.')

def binningb(binning=None, get_server=False):
    """
    Reads or sets the blue channel science camera binninb

    Parameters
    ----------
    binning : string
        Desired binning mode. Available values are '1,1','2,2'. Future: '1,2', '2,1'

    Examples
    --------
    Prints the current binning mode

    >>> Blue.binningb()

    Set the binning mode

    >>> Blue.binningb(binning='2,2')

    """
    

    if get_server == True:
        return "kbds"


    binningKeyword = ktl.cache('kbds','BINNING')
    ppreclrKeyword = ktl.cache('kbds','PPRECLR')
    ampmodeKeyword = ktl.cache('kbds','AMPMODE')
    ccdmodeKeyword = ktl.cache('kbds','CCDMODE')
    gainmulKeyword = ktl.cache('kbds','GAINMUL')

    # save current values (because changing binning will reset them)
    ampmode_current = ampmodeKeyword.read()
    ccdmode_current = ccdmodeKeyword.read()
    gainmul_current = gainmulKeyword.read()

    availableModes = ['2,2','1,1'] #,'1,2','2,1']
    current = binningKeyword.read()
    if binning==None:
        return current
        
    elif binning in availableModes:
        if binning != current:
            binningKeyword.write(binning)
            # The following two lines are a kludge
            # They should be removed once the kbds server is fixed
            # JDN 2017-apr-05
            time.sleep(2)
            ppreclrKeyword.write(1)
            say ('BINNING set to %s' % (binning))
            say ('Resetting ccd mode keywords to previous values')
            ampmodeKeyword.write(ampmode_current)
            ccdmodeKeyword.write(ccdmode_current)
            gainmulKeyword.write(gainmul_current)

        else:
            say("Binning: Target equals current, no change needed.")

        current = binningKeyword.read()
        return current

    else:
        raise ValueError('BINNING %s is not supported' % (binning))

def ampmodeb(ampmode=None):

    """
    Reads or sets the blue channel science camera amplifer mode

    Available modes are:

    0 : quad (ALL)
    1 : single C 
    2 : single E
    3 : single D
    4 : single F
    5 : single B
    6 : single G
    7 : single A
    8 : single H
    9 : dual (A&B)
    10 : dual (C&D)

    Parameters
    ----------
    ampmode : int
        Desired amplifier mode 

    Available modes are:
    1 : single C 
    2 : single E
    3 : single D
    4 : single F
    5 : single B
    6 : single G
    7 : single A
    8 : single H
    9 : dual (A&B)
    10 : dual (C&D)

    Examples
    --------
    Prints the current amplifier mode

    >>> Blue.ampmodeb()

    Set the amplifier mode

    >>> Blue.ampmodeb(ampmode=2)

    """

    ampmodeKeyword = ktl.cache('kbds','AMPMODE')
    availableModes = [0,1,2,3,4,5,6,7,8,9,10]
    current = ampmodeKeyword.read()
    if ampmode==None:
        return current

    elif int(ampmode) in availableModes:
        if int(ampmode) != int(current):
            ampmodeKeyword.write(ampmode)
            say('AMPMODE set to %s' % (ampmode))
        else:
            say("Ampmode: Target equals current, no change needed.")

        current = ampmodeKeyword.read()
        return current

    else:
        raise ValueError('AMPMODE %s is not supported' % (ampmode))

def binningfpc(binning=None):
    """
    Reads or sets the focal plane camera binninb

    Parameters
    ----------
    binning : string
        Desired binning mode. Available values are 1,2,4 and so on

    Examples
    --------
    Prints the current binning mode

    >>> Blue.binningfpc()

    Set the binning mode

    >>> Blue.binningfpc(binning='2')

    """
    
    binningKeyword = ktl.cache('kfcs','BINNING')
    current = binningKeyword.read()
    if binning==None:
        return current
        
    if binning != current:
        binningKeyword.write(binning)
        say ('BINNING set to %s' % (binning))
    else:
        say("Binning: Target equals current, no change needed.")

    current = binningKeyword.read()
    return current


def tintb(exptime=None):
    """
    Reads or sets the blue channel science camera exposure time

    Parameters
    ----------
    exptime : float
        Desired exposure time. 

    Examples
    --------
    Prints the current exposure time

    >>> Blue.tintb()

    Set the exposure time

    >>> Blue.tintb(exptime=10)

    """
    
    exptimeKeyword = ktl.cache('kbds','TTIME')

    if exptime!=None:
        exptimeKeyword.write(exptime)
        say ('Exposure time set to %s' % (str(exptime)))


    result = exptimeKeyword.read()
    return result

def tintfc(exptime=None):
    """
    Reads or sets the focal plane camera exposure time

    Parameters
    ----------
    exptime : float
        Desired exposure time. 

    Examples
    --------
    Prints the current exposure time

    >>> Blue.tintfc()

    Set the exposure time

    >>> Blue.tintfc(exptime=10)

    """
    exptime = float(exptime)
    exptimeKeyword = ktl.cache('kfcs','EXPTIME')

    if (exptime == 0):
        say('The exposure time for the focal plane camera cannot be zero')
        exptime = 0.01

    if exptime!=None:
        exptimeKeyword.write(exptime)
        say ('Exposure time set to %s' % (str(exptime)))

    result = exptimeKeyword.read()
    return result


def triggerfc(trigger_time=None):
    """
    Reads or sets the focal plane camera trigger time

    Parameters
    ----------
    trigger_time : int
        Desired trigger time (interval between exposures)

    Examples
    --------
    Prints the current trigger time

    >>> Blue.triggerfc()

    Set the triger time

    >>> Blue.triggerfc(5)

    """
    
    keyword = ktl.cache('kfcs','TRIGTIME')

    if trigger_time!=None:
        keyword.write(trigtime)
        say ('Trigger time set to %s' % (str(trigtime)))


    result = keyword.read()
    return result

def sequencefc(sequence=None):
    """
    Reads or sets the focal plane camera sequence (number of images, 0 = continuous)

    Parameters
    ----------
    sequence : int
        Desired number of exposures

    Examples
    --------
    Prints the current number of exposures

    >>> Blue.sequencefc()

    Set the number of the exposures

    >>> Blue.sequencefc(5)

    """
    
    sequenceKeyword = ktl.cache('kfcs','SEQUENCE')
    sequenceKeyword.read()

    seqCurrent = sequenceKeyword.binary

    if sequence is not None and sequence != seqCurrent:
        sequenceKeyword.write(sequence)
        say ('Sequence set to %s' % (str(sequence)))

    result = sequenceKeyword.read()
    return result

        

def gainmulb(gainmul=None):
    """
    Reads or sets the blue channel science camera gain multiplier

    Parameters
    ----------
    gainmul : int
        Desired gain multiplier. Available values are 5 and 10.

    Examples
    --------
    Prints the current gain multiplier

    >>> Blue.gainmulb()

    Set the binning mode

    >>> Blue.gainmulb(gainmul=5)

    """

    gainmulKeyword = ktl.cache('kbds','GAINMUL')
    availableModes = [5,10]
    current = gainmulKeyword.read()
    if gainmul==None:
        return current
        
    elif int(gainmul) in availableModes:
        if int(gainmul) != int(current):
            gainmulKeyword.write(gainmul)
            say ('GAINMUL set to %s' % (gainmul))
        else:
            say("Gainmul: Target equals current, no change needed.")

        current = gainmulKeyword.read()
        return current

    else:
        raise ValueError('GAINMUL %s is not supported' % (gainmul))

def ccdspeedb(ccdspeed=None):
    """
    Reads or sets the blue channel science camera ccdspeed

    Parameters
    ----------
    ccdspeed : int
        Desired ccdspeed. Available values are 0 (slow) and 1 (fast)

    Examples
    --------
    Prints the current ccdspeed

    >>> Blue.ccdspeedb()

    Set the ccdspeed to fast

    >>> Blue.ccdspeedbb(ccdspeed=1)

    """
    ccdspeedKeyword = ktl.cache('kbds','CCDMODE')
    availableModes = [0,1]
    current = ccdspeedKeyword.read()
    if ccdspeed == None:
        return current

    elif int(ccdspeed) in availableModes:
        if int(ccdspeed) != int(current):
            ccdspeedKeyword.write(ccdspeed)
            say ('CCDSPEED set to %s' % (ccdspeed))
        else:
            say("CCDspeed: Target equals current, no change needed.")

        current = ccdspeedKeyword.read()
        return current
    else:
        raise ValueError('CCDSPEED %s is not supported' % (ccdspeed))

def ccdmodeb(ccdmode=None):
    """
    Reads or sets the blue channel science camera ccdmode

    Parameters
    ----------
    ccdmode : int
        Desired ccdmode Available values are 0 (slow) and 1 (fast)

    Examples
    --------
    Prints the current ccdmode

    >>> Blue.ccdmodeb()

    Set the ccdmode to fast

    >>> Blue.ccdmodeb(ccdmode=1)

    """
    ccdmodeKeyword = ktl.cache('kbds','CCDMODE')
    availableModes = [0,1]
    current = ccdmodeKeyword.read()
    if ccdmode == None:
        return current

    elif int(ccdmode) in availableModes:
        if int(ccdmode) != int(current):
            ccdmodeKeyword.write(ccdmode)
            say ('CCDMODE set to %s' % (ccdmode))
        else:
            say("CCDmode: Target equals current, no change needed.")

        current = ccdmodeKeyword.read()
        return current
    else:
        raise ValueError('CCDMODE %s is not supported' % (ccdmode))


def autoshutb(mode=None):
    """
    Reads or sets the blue channel science camera autoshutter

    Parameters
    ----------
    autoshutb : int
        Desired autoshutb mode (1 or 0)

    Examples
    --------
    Prints the current autoshut mode

    >>> Blue.autoshutb(mode=1)

    """
    autoshutKeyword = ktl.cache('kbds','AUTOSHUT')
    availableModes = [0,1]
    current = autoshutKeyword.read()
    if mode == None:
        return current

    elif int(mode) in availableModes:
        if int(mode) != int(current):
            autoshutKeyword.write(mode)
            say ('AUTOSHUT set to %s' % (mode))
        else:
            say("AUTOSHUT: Target equals current, no change needed.")

        current = autoshutKeyword.read()
        return current
    else:
        raise ValueError('AUTOSHUT %s is not supported' % (mode))


def focusb(target=None, move=True, quiet=False):
    """
    Reads or set the blue camera focus

    Parameters
    ----------
    target : float
        Desired focus value in mm.
    move : boolean
        Set to False to just set target
    quiet : boolean
        Set to disable progress bar

    Examples
    --------
    Print the current focus value
    >>> Blue.focusb

    Set the current focus value to 1.5mm
    >>> Blue.focusb(target=1.5)

    """
    server = 'kbms'
    foctargmm = ktl.cache(server,'FOCTARGMM') # target encoder
    focmove = ktl.cache(server,'FOCMOVE')   # initiate the move
    focstatus = ktl.cache(server,'FOCSTATUS') 
    focmm = ktl.cache(server,'FOCMM')
    focposerr = ktl.cache(server,'FOCPOSERR')
    focmmerr = ktl.cache(server,'FOCMMERR')
    foctol = ktl.cache(server,'FOCTOL')
    focenc = ktl.cache(server,'FOCENC')
    foctarg = ktl.cache(server,'FOCTARG')

    monitoredKeywords = (foctargmm,focmove,focstatus,focmm,focposerr,focmmerr,foctol,focenc,foctarg)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current value
    if target==None:
        result = focmm.ascii
        lg.info("kcwiServer: Returning focus value '%s'" % (result))
        return result

    # set the target. This is done both for move=True and move=False
    foctargmm.write(target,wait=True)
    time.sleep(2)

    # if the requested target is the same as the current, do not move
    #print(float(focenc.ascii))
    #print(abs(float(focenc.ascii)-float(foctarg.ascii)))
    #print(float(foctarg.ascii))
    
    #time.sleep(2)

    if abs(float(focenc.ascii)-float(foctarg.ascii)) < float(foctol.ascii) and move==True:
        say("Focus: Target equals current, no move needed.")
        return focmm.ascii

    # check if move is possible
    checkIfMoveIsPossible(focstatus)

    # if move is True, then force a move
    if move==True:
        focmove.write(1)

        # move expressions
        moving        = '$kbms.focmove == 1'
        not_moving    = '$kbms.focmove == 0'

        moving = ktl.Expression(moving)
        not_moving = ktl.Expression(not_moving)

        # wait for moving
        result = moving.wait(timeout = timeOutMove)
        if not quiet:
            p = AnimatedProgressBar(end=100, width=standardWidth)
            ktl.monitor(server,'FOCPROG',ProgressCallback,p)

        if result == False:
            raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("Blue camera focus", timeOutMove))

        # wait for not moving
        not_moving.wait(timeout=timeOutComplete)

        # check for successful move
        time.sleep(4)
        checkSuccess(statusKeyword=focstatus, mechanism="Blue Camera focus", targetReachedExpression=None, successStatus="OK")
        if abs(focposerr) > foctol:
            say("Warning: The required focus has NOT been reached")

        # return value
        result = focmm.ascii
        lg.info("kcwiServer: Returning blue camera focus '%s'" % (result))
        return result


def filterb(target=None, move=True):
    """
    Reads or set the blue channel filter

    Parameters
    ----------
    target : string
        Desired filter. Values are: TBD
    move : boolean
        Set to false to only modify the target without moving the filter

    Examples
    --------
    Prints the name of the current filter

    >>> Blue.filterb()

    Insert the B1 filter

    >>> Blue.filterb(target="B1")

    Modify the filter target keyword but do not move

    >>> Blue.filterb(target="B1", move=False)

    """
    timeOutComplete = 180.              # extra time for filter exchange
    server = 'kbes'
    fname = ktl.cache(server, 'FNAME')   # current filter
    ftargn = ktl.cache(server, 'FTARGN') # target filter
    fmove = ktl.cache(server, 'FMOVE')   # initiate the move
    fstatus = ktl.cache(server, 'FSTATUS') # values: OK, MOVING, ERROR, INIT_ERROR
    movemode = ktl.cache(server, 'MOVEMODE')

    monitoredKeywords = (fname, ftargn, fstatus, fmove, movemode)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current filter, otherwise set the filter
    if target==None:
        filter = fname.ascii
        lg.info("kcwiServer: Returning filter value '%s'" %filter)
        return filter

    # if the requested target is the same as the current, do not move
    if target==fname.ascii and move==True:
        say("Filter: Target equals current, no move needed.")
        return fname.ascii

    # check if move is possible
    checkIfMoveIsPossible(fstatus)

    # reset move mode to 0
    currentMoveMode = movemode.ascii
    changeMoveMode(movemode=movemode,mode=0)

    # initiate the move
    ftargn.write(target)

    # if move is True, then force a move
    if move==True:
        fmove.write(1)

        # fmove expressions
        moving        = '$kbes.fmove == 1'
        not_moving    = '$kbes.fmove == 0'
        target_reached = '$kbes.fname == $kbes.ftargn'

        moving = ktl.Expression(moving)
        not_moving = ktl.Expression(not_moving)
        target_reached = ktl.Expression(target_reached)

        # wait for moving
        result = moving.wait(timeout = timeOutMove)
        if result == False:
            raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("Filter", timeOutMove))

        # wait for not moving
        not_moving.wait(timeout=timeOutComplete)

        # check for successful move
        time.sleep(2)
        checkSuccess(statusKeyword=fstatus, mechanism="Filter",
                targetReachedExpression=target_reached, successStatus="Success:")

        # return value
        filter = fname.ascii
        lg.info("kcwiServer: Returning filter value '%s'" %filter)
        return filter

    # reset move mode
    if currentMoveMode == 1:
        changeMoveMode(movemode=movemode, mode=1)

def gratingb(target=None, move=True):
    """
    Reads or set the blue channel grating

    Parameters
    ----------
    target : string
        Desired grating. Values are: TBD
    move : boolean
        Set to false to only modify the target without moving the grating

    Examples
    --------
    Prints the name of the current grating

    >>> Blue.gratingb()

    Insert the L grating

    >>> Blue.gratingb(target="L")

    Modify the grating target keyword but do not move

    >>> Blue.gratingb(target="H2", move=False)

    """
    timeOutComplete = 360.              # extra time for grating exchange
    server = 'kbes'
    gname = ktl.cache(server,'GNAME')   # current grating
    gtargn = ktl.cache(server,'GTARGN') # target grating
    gmove = ktl.cache(server,'GMOVE')   # initiate the move
    gstatus = ktl.cache(server,'GSTATUS') 
    movemode = ktl.cache(server,'MOVEMODE')

    monitoredKeywords = (gname, gtargn, gstatus, gmove, movemode)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current filter, otherwise set the filter
    if target==None:
        grating = gname.ascii
        lg.info("kcwiServer: Returning grating value '%s'" % (grating))
        return grating

    # if the requested target is the same as the current, do not move
    if target==gname.ascii and move==True:
        say("Grating: Target equals current, no move needed.")
        return gname.ascii

    # check if move is possible
    checkIfMoveIsPossible(gstatus)

    # reset move mode to 0
    currentMoveMode = movemode.ascii
    changeMoveMode(movemode=movemode,mode=0)

    # set the target. This is done both for move=True and move=False
    gtargn.write(target)

    # if move is True, then force a move
    if move==True:
        gmove.write(1)

        # fmove expressions
        moving        = '$kbes.gmove == 1'
        not_moving    = '$kbes.gmove == 0'
        target_reached = '$kbes.gname == $kbes.gtargn'

        moving = ktl.Expression(moving)
        not_moving = ktl.Expression(not_moving)
        target_reached = ktl.Expression(target_reached)

        # wait for moving
        result = moving.wait(timeout = timeOutMove)
        if result == False:
            raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("Grating", timeOutMove))

        # wait for not moving
        not_moving.wait(timeout=timeOutComplete)

        # check for successful move
        time.sleep(2)
        checkSuccess(statusKeyword=gstatus, mechanism="Grating",
                targetReachedExpression=target_reached, successStatus="Success:")

        # return value
        grating = gname.ascii
        lg.info("kcwiServer: Returning grating value '%s'" %grating)
        return grating


    # reset move mode
    if currentMoveMode == 1:
        changeMoveMode(movemode=movemode, mode=1)


def camangleb(angvalue=None, move=True, quiet=False):
    """
    Reads or set the blue channel articulation stage angle

    Parameters
    ----------
    angvalue : float
        Desired camera angle in degrees
    move : boolean
        Set to false to only modify the target without moving the camangle
    quiet : boolean
        Set to disable progress bar

    Examples
    --------
    Prints the name of the current camangle

    >>> Blue.camangleb()

    Go to 10 degrees

    >>> Blue.camangleb(angvalue=10)

    Modify the camangle target keyword but do not move

    >>> Blue.camangleb(angvalue=10, move=False)

    """
    timeOutComplete = 180.              # extra time for cam angle
    server = 'kbms'
    #gname = ktl.cache(server,'GNAME')   # current grating
    arttarg = ktl.cache(server,'ARTTARG') # target encoder
    arttargang = ktl.cache(server,'ARTTARGANG') # target angle
    artmove = ktl.cache(server,'ARTMOVE')   # initiate the move
    artstatus = ktl.cache(server,'ARTSTATUS') 
    artenc = ktl.cache(server,'ARTENC')
    artang = ktl.cache(server,'ARTANG')
    artposerr = ktl.cache(server,'ARTPOSERR')
    arttol = ktl.cache(server,'ARTTOL')

    monitoredKeywords = (arttarg,arttargang,artmove,artstatus,artenc,artang,artposerr,arttol)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current filter, otherwise set the filter
    if angvalue==None:
        result = artang.ascii
        lg.info("kcwiServer: Returning camera angle '%s'" % (result))
        return result

    # if the requested target is the same as the current, do not move
    if abs(float(angvalue)-artang) < 0.001 and move==True:
        say("Articulation stage: Target equals current, no move needed.")
        return artang.ascii

    # check if move is possible
    checkIfMoveIsPossible(artstatus)

    # check if we are in filling position
    if is_in_filling_position() != False:
        say("KCWI might be in filling position, moves are not allowed")
        return -1

    # set the target. This is done both for move=True and move=False
    arttargang.write(angvalue)

    # if move is True, then force a move
    if move==True:
        artmove.write(1)

        # move expressions
        moving        = '$kbms.artmove == 1'
        not_moving    = '$kbms.artmove == 0'
        target_reached = '$kbms.artang == $kbms.arttargang'

        moving = ktl.Expression(moving)
        not_moving = ktl.Expression(not_moving)
        target_reached = ktl.Expression(target_reached)

        # wait for moving
        result = moving.wait(timeout = timeOutMove)
        if not quiet:
            p = AnimatedProgressBar(end=100, width=standardWidth)
            ktl.monitor(server,'ARTPROG',ProgressCallback,p)

        if result == False:
            raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("Articulation stage", timeOutMove))

        # wait for not moving
        not_moving.wait(timeout=timeOutComplete)

        # check for successful move
        time.sleep(5)
        checkSuccess(statusKeyword=artstatus, mechanism="Articulation stage", targetReachedExpression=None, successStatus="OK")
        if abs(artposerr) > arttol:
            say("Warning: The required angle has NOT been reached")

        # return value
        result = artang.ascii
        lg.info("kcwiServer: Returning articulation stage angle '%s'" % (result))
        return result


def grangleb(angvalue=None, move=True, quiet=False):
    """
    Reads or set the blue channel grating angle

    Parameters
    ----------
    angvalue : float
        Desired grating angle in degrees
    move : boolean
        Set to false to only modify the target without moving the grangle
    quiet : boolean
        Set to disable progress bar

    Examples
    --------
    Prints the name of the current camangle

    >>> Blue.grangleb()

    Go to 10 degrees

    >>> Blue.grangleb(angvalue=10)

    """
    timeOutComplete = 180.                  # extra time for grating angle
    server = 'kbes'
    grtargp = ktl.cache(server,'GRTARGP')   # target position (0,1 or 2)
    grangle = ktl.cache(server,'GRANGLE')   # current angle
    grtrgang = ktl.cache(server,'GRTRGANG') # target angle
    grstatus = ktl.cache(server,'GRSTATUS') 
    gstatus = ktl.cache(server,'GSTATUS')
    grmove = ktl.cache(server,'GRMOVE')
    monitoredKeywords = (grtargp, grangle, grtrgang, grstatus,gstatus, grmove)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current filter, otherwise set the filter
    if angvalue==None:
        result = grangle.ascii
        lg.info("kcwiServer: Returning grating angle '%s'" % (result))
        return result

    # if the requested target is the same as the current, do not move
    if abs(float(angvalue)-grangle) < 0.01:
        say("Grating angle: Target equals current, no move needed.")
        return grangle.ascii

    # check if move is possible
    checkIfMoveIsPossible(gstatus)
    checkIfMoveIsPossible(grstatus)

    # set the target. This is done both for move=True and move=False
    grtrgang.write(angvalue)

    # stop here if we are not asking for a move

    if move == False:
        return

    # check that we are in angle mode

    # if we are not in angle mode, changing the angle mode initiates a move
    # if we are in angle mode, we need to issue a move command

    if grtargp != 2:
        sys.stdout.write("Setting grating rotator to angle mode\n")
        grtargp.write(2)

    grmove.write(1)

    # move expressions
    moving        = '$kbes.grstatus == "Moving"'
    not_moving    = '$kbes.grstatus == "Move complete"'
    target_reached = '$kbes.grposerr < $kbes.grtolopt'

    moving = ktl.Expression(moving)
    not_moving = ktl.Expression(not_moving)
    target_reached = ktl.Expression(target_reached)

    # wait for moving
    result = moving.wait(timeout = timeOutMove)
    if not quiet:
        p = AnimatedProgressBar(end=100, width=standardWidth)
        ktl.monitor(server,'GRPROG',ProgressCallback,p)

    if result == False:
        raise RuntimeError("Mechanism %s did not start moving within %d seconds"
                % ("Grating rotator", timeOutMove))

    # wait for not moving
    not_moving.wait(timeout=timeOutComplete)

    # check for successful move
    time.sleep(2)
    checkSuccess(statusKeyword=grstatus, mechanism="Grating rotator",
            targetReachedExpression=target_reached, successStatus="Move")
    #if abs(artposerr) > arttol:
    #    say("Warning: The required encoder position has NOT been reached")

    # return value
    result = grangle.ascii
    return result


def nsmaskb(target=None, move=True, quiet=True):
    """
    Reads or modify the position of the nod and shuffle mask


    Parameters
    ----------
    target : string
        Desired position. Valid values are: "Open", "Test", "Mask"
    move : boolean
        Set to false to only modify the target without moving the N&S mask
    quiet : boolean
        Set to disable progress bar


    Examples
    --------
    Prints the position of the nod and shuffle mask

    >>> Blue.nsmasbk()

    Set the nod and shuffle mask to Mask

    >>> Blue.nsmaskb(target="Mask")

    """

    server = 'kbms'
    nasname = ktl.cache(server, 'NASNAME')   # current 
    nastargn = ktl.cache(server, 'NASTARGN') # target 
    nasmove = ktl.cache(server, 'NASMOVE')   # initiate the move
    nasstatus = ktl.cache(server, 'NASSTATUS') # values?

    monitoredKeywords = (nasname, nastargn,nasmove,nasstatus)

    # set wait = False if you can accept undefined keywords (for simulation, for example)
    setupMonitoring(monitoredKeywords, wait=True)

    # if called with an empty string, return the current slicer
    if target==None:
        nas = nasname.ascii
        lg.info("kcwiServer: Returning nod and shuffle value '%s'" % (nas))
        return nas

    # if the requested target is the same as the current, do not move
    if target==nasname.ascii and move==True:
        say("N&S: Target is the same as requested. No move needed.")
        return

    # check if move is possible
    checkIfMoveIsPossible(nasstatus)

    # initiate the move
    nastargn.write(target)

    # if move is True, then force a move
    if move==True:
        nasmove.write(1)
        if not quiet:
            p = AnimatedProgressBar(end=100, width=standardWidth)
            ktl.monitor(server,'NASPROG',ProgressCallback,p)
        # fmove expressions
        moving        = '$kbms.nasmove == 1'
        not_moving    = '$kbms.nasmove == 0'
        target_reached = '$kbms.nasname == $kbms.nastargn'

        moving = ktl.Expression(moving)
        not_moving = ktl.Expression(not_moving)
        target_reached = ktl.Expression(target_reached)

        # wait for moving
        result = moving.wait(timeout = timeOutMove)
        if result == False:
            raise RuntimeError("Mechanism %s did not start moving within %d seconds" % ("N&S Mask", timeOutMove))

        # wait for not moving
        not_moving.wait(timeout=240)

        # check for successful move
        time.sleep(5)

        checkSuccess(statusKeyword=nasstatus, mechanism="N&S Mask", targetReachedExpression=target_reached, successStatus="OK")


