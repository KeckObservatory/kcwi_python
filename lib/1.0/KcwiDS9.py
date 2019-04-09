import sys

import os
import shlex
import subprocess
import time

class ds9:
        title = None
        '''
        The ds9 class provides wrappers around the unix commands xpaget
        and xpaset. The class is smart enough to automatically detect
        a running ds9 and attach automatically displayed images to it
        '''
        def __init__(self, title):
                ''' ds9 construction init checks to see if a ds9 called title
                is currently running. If not, a new ds9 instance is created with
                that title'''
                self.title = title
                self.zoom = None
                cmd = shlex.split("xpaget %s" % self.title)

                devnull = open( '/dev/null', 'w')
                retcode = subprocess.call( cmd, stdout=devnull, stderr=devnull)
                self.process_name = None
                if retcode == 1:

                        self.process_name = subprocess.Popen(["ds9", "-title", self.title , "-preserve", "pan", "yes","-cd", "."])        
                        time.sleep(2)
                        

        def xpaget(self, cmd):
                '''xpaget is a convenience function around unix xpaget'''
                cmd = shlex.split("xpaget %s %s" % (self.title, cmd))
                retcode = subprocess.call(cmd)

        def xpapipe(self, cmd, pipein):
                ''' xpapipe is a convenience wrapper around echo pipein | xpaset ...'''
      
                cmd = shlex.split('xpaset %s %s' % (self.title, cmd))
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.stdin.write(pipein)
                p.stdin.flush()
                print(p.communicate())


        def xpaset(self, cmd):
                '''xpaget is a convenience function around unix xpaset'''
                xpacmd = "xpaset -p %s %s" % (self.title, cmd)
                # lg.debug(xpacmd)

                cmd = shlex.split(xpacmd)

                retcode = subprocess.call(cmd)
                # lg.debug("retcode = %s" % retcode) 


        def frameno(self, frame):
                '''frameno sets the ds9 frame number to [frame]'''
                self.xpaset("frame %i" %frame)

        def open(self, fname, frame):
                '''open opens a fits file [fname] into frame [frame]'''
                self.frameno(frame)
                self.xpaset("file %s" % fname)

