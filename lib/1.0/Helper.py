
import ktl
import sys
import logging as lg
import sys, os
import time
import subprocess
from subprocess import PIPE

def setupMonitoring(keywords, wait=True):

    for key in keywords:
        key.monitor()

    if wait == False:
        return
    else:
        checkInitialValues(keywords)

def checkInitialValues(keywords):

    for keyword in keywords:
        keyword.wait(timeout=1)
        if keyword['populated'] == False:
           raise RuntimeError('Keyword %s is not available. The server might be offline.' % (keyword.full_name))

def say(message):
    sys.stdout.write(message + '\n')
    sys.stdout.flush()

def sleepdots(seconds):
    i = 0
    while i < seconds:
        i += 1
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(1)

    sys.stdout.write('\n')


def isServerUp(server):
    p = subprocess.Popen(['show -s '+server+' uptime'], stderr = PIPE, shell=True, stdout=PIPE)
    output = p.communicate()
    if "Failed to create RPC client" in output[1]:
        return False
    else:
        say("Server %s is up" % (server))
        return True





def checkIfMoveIsPossible(statusKeyword):

    # if the status keyword is in error, do not attempt the move
    if statusKeyword.ascii.split(' ')[0] in ['Error:', 'Moving:','Error','Moving']:
        lg.error("kcwiServer: Cannot execute requested move. Status is '%s'" % (statusKeyword))
        raise RuntimeError("Cannot start requested move. Status is %s" % (statusKeyword))

def changeMoveMode(movemode,mode):

    if mode in [0,1]:
        movemode.write(mode)
    else:
        raise ValueError("resetMoveMode called with wrong argument (mode=%s)" % (mode))

def checkSuccess(statusKeyword=None, mechanism=None, targetReachedExpression=None, successStatus=None):

    if targetReachedExpression==None:
        result = True
    else:
        result = targetReachedExpression.evaluate()
    statusString = statusKeyword.ascii.split(' ')[0]
    if result == False or statusString != successStatus:
        lg.info("kcwiServer: %s move failed. Status is %s" % (mechanism, statusKeyword.ascii))
        raise RuntimeError("kcwiServer: %s move failed. Status is %s" % (mechanism, statusKeyword.ascii))



def get_terminal_width():
    command = ['tput','cols']
    try:
        width = int(subprocess.check_output(command))
    except OSError as e:
        print("Invalid command '{0]': exit status ({1})".format(command[0],e.errno))
    except subprocess.CalledProcessError as e:
        print("Command '{0}' returned non-zero exit status: ({1})".format(command, e.returncode))
    else:
        return width


class ProgressBar(object):
    """ProgressBar class holds the options of the progress bar.
    The options are:
        start   State from which start the progress. For example, if start is
                5 and the end is 10, the progress of this state is 50%
        end     State in which the progress has terminated.
        width   --
        fill    String to use for "filled" used to represent the progress
        blank   String to use for "filled" used to represent remaining space.
        format  Format
        incremental
    """
    def __init__(self, start=0, end=10, width=12, fill='=', blank='.', format='[%(fill)s>%(blank)s] %(progress)s%%', incremental=True):
        super(ProgressBar, self).__init__()

        self.start = start
        self.end = end
        #sz = os.get_terminal_size()
        try:
            self.width = get_terminal_width()-10
        except:
            say("Cannot determine terminal width. Using standard width.")
            self.width=width
        #self.width = width
        self.fill = fill
        self.blank = blank
        self.format = format
        self.incremental = incremental
        self.step = 100 / float(self.width) #fix
        self.reset()

    def __add__(self, increment):
        increment = self._get_progress(increment)
        if 100 > self.progress + increment:
            self.progress += increment
        else:
            self.progress = 100
        return self

    def __str__(self):
        progressed = int(self.progress / self.step) #fix
        fill = progressed * self.fill
        blank = (self.width - progressed) * self.blank
        return self.format % {'fill': fill, 'blank': blank, 'progress': int(self.progress)}

    __repr__ = __str__

    def _get_progress(self, increment):
        return float(increment * 100) / self.end

    def reset(self):
        """Resets the current progress to the start point"""
        self.progress = self._get_progress(self.start)
        return self

class AnimatedProgressBar(ProgressBar):
    """Extends ProgressBar to allow you to use it straighforward on a script.
    Accepts an extra keyword argument named `stdout` (by default use sys.stdout)
    and may be any file-object to which send the progress status.
    """
    def __init__(self, *args, **kwargs):
        super(AnimatedProgressBar, self).__init__(*args, **kwargs)
        self.stdout = kwargs.get('stdout', sys.stdout)
        self.disable=False

    def show_progress(self):
        if self.disable==True:
            return
        if hasattr(self.stdout, 'isatty') and self.stdout.isatty():
            self.stdout.write('\r')
        else:
            self.stdout.write('\n')
        self.stdout.write(str(self))
        self.stdout.flush()

def ProgressCallback(keyword,value,instance):
    #value = int(keyword['bin'])
    if instance.progress == 0 and int(value)==100:
        return
    instance.progress=int(value)
    instance.show_progress()
    # this produces the final new line
    if instance.progress == 100:
        # this deals with cases in which the "100%" is broadcast multiple times
        if instance.disable==False:
            sys.stdout.write("\n")
        instance.disable=True


def NullCallback(keyword,value,data):
    return
