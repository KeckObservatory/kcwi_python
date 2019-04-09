#from . import Version
#Version.append('$Revision: 85432 $')
#del Version
"""
.. module:: Global
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

def stateid(id=None):
    """
    Reads or sets the unique id of the current state file

    Parameters
    ----------
    id : string
       Desired state file id

    Examples
    --------
    Sets the current state 

    >>> Global.stateid("abcdefg")
    """
    server = 'kcwi'
    stateid = ktl.cache(server, 'STATEID') 

    if id is None:
        return(stateid.read())

    stateid.write(str(id))


def statenam(name=None):
    """
    Reads or sets the configuration name associated the current state file

    Parameters
    ----------
    name : string
       Desired state file configuration name

    Examples
    --------
    Sets the current state 

    >>> Global.statenam("abcdefg")
    """
    server = 'kcwi'
    statenam = ktl.cache(server, 'STATENAM') 

    if name is None:
        return(statenam.read())

    statenam.write(str(name))

def progname(name=None):
    """
    Reads or sets the TAC approved program

    Parameters
    ----------
    name : string
       Desired TAC approved program code

    Examples
    --------
    Sets the current program

    >>> Global.progname("abcdefg")
    """
    server = 'kcwi'
    kprogname = ktl.cache(server, 'PROGNAME') 

    if name is None:
        return(kprogname.read())

    kprogname.write(str(name))
   
