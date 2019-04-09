
import ktl
import sys, os, subprocess, pipes, shlex
from datetime import datetime, timedelta
import logging as lg
from KCWI.Helper import say

def exists_remote(host,path):
   """ Check if a directory exists on a remote server"""

   status = subprocess.call(
      ['ssh',host, 'test -e {}'.format(pipes.quote(path))])
   if status == 0:
      return True
   if status == 1:
      return False
   raise Exception ('SSH failed')

def is_writable_remote(host,path):
   """ Check if a directory is writable on a remote server"""
   status = subprocess.call(
      ['ssh',host, 'test -w {}'.format(pipes.quote(path))])
   if status == 0:
      return True
   if status == 1:
      return False
   raise Exception ('SSH failed')

def exists_and_is_writable(outdir):
    host = os.environ['HOST']
    user = os.environ['USER']
    #say("Checking directory as user %s on host %s" % (user,host))
    # check if the directory has been created correctly
    exists = False
    iswritable = False
    #if host == 'kcwitarg':
    if os.path.exists(outdir):
        #sys.stdout.write("Directory exists (local)\n")
        exists = True
    else:
        sys.stdout.write("Directory "+outdir+" does not exist (local)\n")
    #else:
    #   if exists_remote(user+"@kcwitarg",outdir):
    #      sys.stdout.write("Directory exists (remote)\n")
    #      exists = True
    #   else:
    #      sys.stdout.write("Directory "+outdir+" does not exist (remote)\n")

    # Check if the directory is writable

    #if host == 'kcwitarg':
    if os.access(outdir,os.W_OK):
        #sys.stdout.write("Directory is writable (local)\n")
        iswritable = True
    else:
        sys.stdout.write("Directory "+outdir+" is not writable(local)\n")
    #else:
    #   if is_writable_remote(user+"@kcwitarg",outdir):
    #      sys.stdout.write("Directory is writable (remote)\n")
    #      iswritable = True
    #   else:
    #      sys.stdout.write("Directory "+outdir+" is not writable (remote)\n")

    if (exists == True and iswritable == True):
       return True
    else:
       return False


def file_list(outdir, host):
   """
   Returns the list of files in a directory, local or remote
   """
   if os.environ['HOST'] != host:
      cmd = 'ssh -l %s %s ls -1 %s' % (os.environ['USER'],host, outdir)
   else:
      cmd = 'ls -1 %s' % (outdir)

   args = shlex.split(cmd)
   output,error = subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
   return output

def newdir(disk=None):

    # DISK

    if disk == None:
       # read the list of available disks
       disklist = ktl.cache('kbds','disklist')
       datadisk = disklist.read()

       disk = str(datadisk.split(':')[0])

    # UTDATE

    uttime = float(datetime.utcnow().strftime("%H"))
    if uttime>18.0:
       delta=1
    else:
       delta=0
    utdate = str((datetime.utcnow()+timedelta(days=delta)).strftime("%Y%b%d")).lower()

    # USER

    user = os.environ['USER']

    # HOST

    host = os.environ['HOST']

    # use the builtin feature of the kbds server to create the directory

    new_outdir = disk+"/"+user+"/"+utdate
    say("Attempting to change outdir to %s" % new_outdir)

    outdir(new_outdir)



def frameroot(channel):
    """ Returns the root name of the files for the current UT date"""

    uttime = float(datetime.utcnow().strftime("%H"))
    if uttime>18.0:
       delta=1
    else:
       delta=0

    ut = str((datetime.utcnow()+timedelta(days=delta)).strftime("%y%m%d"))
    if (channel == 'blue'):
        return 'kb'+ut+'_'
    if (channel == 'red'):
        return 'kr'+ut+'_'
    if (channel == 'fpc'):
        return 'kf'+ut+'_'

def get_lastfullimage(channel):
   """
   Return the full name of the last saved image
   """
   if (channel == 'blue'):
      koutdir = ktl.cache('kbds','outdir')
      host = 'kcwitarg'
   #if (channel == 'red'):
   #   koutdir = ktl.cache('kbds','outdir')
   if (channel == 'fpc'):
      koutdir = ktl.cache('kfcs','outdir')
      host = 'kcwiserver'

   outdir = koutdir.read()
   if exists_and_is_writable(outdir):
      files = file_list(outdir,host).split('\n')
   else:
      sys.stdout.write("Specified outdir %s does not exist.\n" % (outdir))
      sys.exit()
   pattern_start = frameroot(channel)
   pattern_end = '.fits'
   lastfile = ""
   if len(files)>0:
      selected_files = [x for x in files if x.startswith(str(pattern_start))]
      selected_numbers = [int((x.split("_")[1]).split(".")[0]) for x in selected_files]
      if len(selected_numbers)>0:
         lastfile = sorted(selected_numbers)[-1]
         if (channel == 'blue'):
            lastfile = "%s/%s%04d.fits" % (outdir,pattern_start,int(lastfile))
         if (channel == 'fpc'):
            lastfile = "%s/%s%06d.fits" % (outdir,pattern_start,int(lastfile))
         

   return lastfile

def get_nextfile(channel):
   """
   Return 1+ the frameno of the last saved image
   """

   if channel == 'blue':
      koutdir = ktl.cache('kbds','outdir')
      host = 'kcwiserver'
   #if channel == 'red':
   #   koutdir = ktl.cache('krds','outdir')
   if channel == 'fpc':
      koutdir = ktl.cache('kfcs','outdir')
      host = 'kcwiserver'

   outdir = koutdir.read()

   if exists_and_is_writable(outdir):
      files = file_list(outdir,host).split('\n')
   else:
      sys.stdout.write("Specified outdir %s does not exist.\n" % (outdir))
      sys.exit()

   pattern_start = frameroot(channel)
   pattern_end = '.fits'
   nextfile = 1
   if len(files)>0:
      selected_files = [x for x in files if x.startswith(str(pattern_start))]
      selected_numbers = [int((x.split("_")[1]).split(".")[0]) for x in selected_files]
      if len(selected_numbers)>0:
         nextfile = sorted(selected_numbers)[-1]+1

   #say("returning next file = %s" % (nextfile))
   return nextfile

def checkOutputDirs():
   """
   Shows a number of keywords related to the detector and focal plane camera servers
   """

   boutdir = ktl.cache('kbds','outdir')
   boutfile = ktl.cache('kbds','outfile')
   bframeno = ktl.cache('kbds','frameno')
   #routdir = ktl.cache('krds','outdir')
   #routfile = ktl.cache('krds','outfile')
   #rframeno = ktl.cache('krds','frameno')
   foutdir = ktl.cache('kfcs','outdir')
   foutfile = ktl.cache('kfcs','outfile')
   fframeno = ktl.cache('kfcs','counter')

   say("Blue camera:")
   say("OUTDIR  = %s" % boutdir.read())
   say("OUTFILE = %s" % boutfile.read())
   say("FRAMENO = %s" % bframeno.read())
   say("FP camera:")
   say("OUTDIR  = %s" % foutdir.read())
   say("OUTFILE = %s" % foutfile.read())
   say("FRAMENO = %s" % fframeno.read())



def nextimage(channel):
   """
   Returns the full name of the next image
   """

   if channel == 'blue':
      kframeno = ktl.cache('kbds','frameno')
      koutdir = ktl.cache('kbds','outdir')
      koutfile = ktl.cache('kbds','outfile')
   if channel == 'red':
      kframeno = ktl.cache('krds','frameno')
      koutdir = ktl.cache('krds','outdir')
      koutfile = ktl.cache('krds','outfile')
   if channel == 'fpc':
      kframeno = ktl.cache('kfcs','counter')
      koutdir = ktl.cache('kfcs','outdir')
      koutfile = ktl.cache('kfcs','outfile')

   fname = "%s/%s%04d.fits" % (koutdir.read(),koutfile.read(),int(kframeno.read()))

   return fname


def frame(channel,number=None):
   """
   if number is fiven, reset frameno to that number.
   If not, returns the current frameno
   """
   if channel == 'blue':
      kframeno = ktl.cache('kbds','frameno')
   if channel == 'red':
      kframeno = ktl.cache('krds','frameno')
   if channel == 'fpc':
      kframeno = ktl.cache('kfcs','frameno')

   if number == None:
      frame = kframeno.read()
      return frame
   else:
      kframeno.write(number)

   

def set_nextframe(channel, number=None):
   """
   if number is given, reset frameno to that number. If not, 
   reset to the last frame available on disk + 1
   """
   if channel == 'blue':
      kframeno = ktl.cache('kbds','frameno')
      if number == None:
         number = get_nextfile(channel)
   #if channel == 'red':
   #   kframeno = ktl.cache('krds','frameno')
   #   if number == None:
   #      nextfile = get_nextfile(channel)
   if channel == 'fpc':
      kframeno = ktl.cache('kfcs','counter')
      if number == None:
         number = get_nextfile(channel)

   kframeno.write(int(number))
   

def outdir(outdir=None):
   """ 
   With no arguments, prints the name of the current data directory. 
   With one argument, change the outdir keyword to the named directory, creating it if requested.
   If files already exist in the outputdirectory, frameno is reset to be 1 higher than the highest
   existing image number.
   """

   if outdir==None:
      koutdir = ktl.cache('kbds','outdir')
      return koutdir.read()

   say("Setting outdir to %s for Blue Camera" % (outdir))
   koutdirb = ktl.cache('kbds','outdir')
   koutdirb.write(outdir)
   #koutdirr = ktl.cache('krds','outdir')
   #koutdirr.write(outdir)
   say("Setting outdir to %s for Focal Plane Camera" % (outdir))
   koutdir_fpc = ktl.cache('kfcs','outdir')
   koutdir_fpc.write(outdir)
   exists_and_is_writable(outdir)
   if exists_and_is_writable(outdir):
      pass
   else:
      raise RuntimeError("Could not set outdir to "+outdir)

   # if there are files in the directory
   # set the frame to the next frame
   kframeno = ktl.cache('kbds','frameno')
   nextFileBlue = get_nextfile("blue")
   sys.stdout.write("Setting next file number to %s for blue camera.\n" % (nextFileBlue))
   kframeno.write(nextFileBlue)
   #nextFileRed = get_lastfile("red")
   #sys.stdout.write("Setting next file number to %s for red camera.\n" % (nextFileRed))
   # kframeno.write(nextFileRed)
   kframeno_fpc = ktl.cache('kfcs','counter')
   nextFile = get_nextfile("fpc")
   sys.stdout.write("Setting next file number to %s for focal plane camera.\n" % (nextFile))
   kframeno_fpc.write(nextFile)

def object(object=None):
   """ 
   Returns or sets the object
   """
   kobjectb = ktl.cache('kbds','object')
   #kobjectr = ktl.cache('krds','object')
   if object == None:

      object = kobjectb.read()
      return object

   else:
      kobjectb.write(object)
      #kobjectr.write(object)

def imtype(imtype=None):
   """ 
   Returns or sets the image type
   """
   kimtype = ktl.cache('kbds','imtype')
   #kobjectr = ktl.cache('krds','object')
   if imtype == None:

      imtype = kimtype.read()
      return imtype

   else:
      kimtype.write(imtype)
      #kobjectr.write(object)


def observer(observer=None):
   """ 
   Returns or sets the observer
   """
   kobserverb = ktl.cache('kbds','observer')
   #kobserverr = ktl.cache('krds','observer')

   if observer == None:

      observer = kobserverb.read()
      return observer

   else:
      kobserverb.write(observer)
      #kobserverr.write(observer)


      
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

   format = "%1s %-14s %1s\t%-14s %1s\t%-14s %1s"
   say(format % ('P','kp1s','on','kp2s','on','kp3s','on'))

   for plug in plugs:
      say(format % (str(plug),p1[plug][0].read(),p1[plug][1].read(),\
                    p2[plug][0].read(),p2[plug][1].read(),\
                    p3[plug][0].read(),p3[plug][1].read()))

   return p1,p2,p3

def kcwiPower(serverNumber=None, plugNumber=None, action=None):
   
   p1,p2,p3 = kcwiPowerStatus()
   
   powers = [p1,p2,p3]

   if serverNumber == None:
      question = "Which server number ?"
      reply = ""
      while reply not in ['1','2','3']:
         reply = str(raw_input(question)).strip()
      server = reply   
   else:
      server = serverNumber
   
   if plugNumber == None:
      question = "Which plug number ?"
      reply = ""
      while reply not in ['1','2','3','4','5','6','7','8']:
         reply = str(raw_input(question)).strip()
      plug = reply   
   else:
      plug = plugNumber

   if action == None:
      question = "on or off ?"
      reply = ""
      while reply not in ['on','off']:
         reply = str(raw_input(question)).lower().strip()
      action = reply.lower()


   name = powers[int(server)-1][int(plug)][0].read()
   status = powers[int(server)-1][int(plug)][1].read()

   if action == 'on':
      action = 1
   if action == 'off':
      action = 0

   say("%s: Changing status of %s (currently at %s) to %s" % (powers[int(server)-1][int(plug)][2],name, status,action))

   powers[int(server)-1][int(plug)][1].write(action)

   p1,p2,p3 = kcwiPowerStatus()

def moveSlicer(direction, number, nomove=False):
   slicer = ktl.cache('kcas','ifuname')
   tvxoff = ktl.cache('dcs','tvxoff')
   rel2curr = ktl.cache('dcs','rel2curr')

   slicer.monitor()
   say("Slicer is %s" % (slicer))
   platescale=1.36
   if slicer == 'Medium':
      sliceSize = platescale/2.0
   elif slicer == 'Small':
      sliceSize = platescale/4.0
   elif slicer == 'Large':
      sliceSize = platescale
   else:
      sliceSize = 0

   if direction == 'left':
      sign = +1
   elif direction == 'right':
      sign = -1
   else :
      sign = 0

   if (nomove is False):
      moveSize = sliceSize*number*sign
      say("Applying moves (%s %f) ...\n" % (direction,moveSize))
      tvxoff.write(sliceSize*number*sign)
      rel2curr.write(True)
   else:
      say("No moves applied")





def moveGuider(x1,y1,x2,y2,nomove=False):
   tvxoff = ktl.cache('dcs','tvxoff')
   tvyoff = ktl.cache('dcs','tvyoff')
   rel2curr = ktl.cache('dcs','rel2curr')
   binning = ktl.cache('magiq','binning')
   

   deltax = x1-x2
   deltay = y2-y1

   # this is the scale in arcsec/pix on the guider
   scale = 0.208
   # usually guiders are used in 2x2 binning

   scale = scale * float(binning.read())

   # convert delta in arcsec
   deltatvx = deltax * scale
   deltatvy = deltay * scale

   say("Requested moves: %3.1f %3.1f arcsecs" % (deltatvx, deltatvy))

   # move
   if (nomove is False):
      say("Applying moves...")
      tvxoff.write(deltatvx)
      tvyoff.write(deltatvy)
      rel2curr.write(True)
   else:
      say("No moves applied")

def moveFpc(x1,y1,x2,y2,nomove=False):

   instxoff = ktl.cache('dcs','instxoff')
   instyoff = ktl.cache('dcs','instyoff')
   rel2curr = ktl.cache('dcs','rel2curr')

   deltax = x2-x1
   deltay = y2-y1

   # this is the scale in arcsec/pix on the focal plane, unbinned
   scale = 0.00756
   # binning
   binning = 4
   scale = scale * binning

   # convert delta in arcsec
   deltainstx = deltax * scale
   deltainsty = deltay * scale

   say("Requested moves: %3.1f %3.1f arcsecs" % (deltainstx, deltainsty))

   # move
   if (nomove is False):
      say("Applying moves...")
      instxoff.write(deltainstx)
      instyoff.write(deltainsty)
      rel2curr.write(True)
   else:
      say("No moves applied")



