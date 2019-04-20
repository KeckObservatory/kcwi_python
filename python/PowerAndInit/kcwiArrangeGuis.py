import sys
import os
import subprocess
import argparse
import Xlib
import Xlib.display

#TODO just a skeleton, need to figure out wid from title
def arrangeGui(disp, title, X, Y, WIDTH, HEIGHT):
    display = Xlib.display.Display(disp)
    root = display.screen().root
    windowID = root.get_full_property(display.intern_atom(title), Xlib.X.AnyPropertyType).value[0]
    window = display.create_resource_object('window', windowID)
    if WIDTH and HEIGHT == 0:
         window.configure(x = X, y = Y)
         display.sync()
    else:
        window.configure(x = X, y = Y, width = WIDTH, height = HEIGHT)
        display.sync()




# check arguments

description = "KCWI Initialization Script"
parser = argparse.ArgumentParser(description=description)
args = parser.parse_args()

if os.environ.get("DISPLAY") is None:
    print("ERROR: must set DISPLAY before running this program")
    sys.exit(1)

# set display variables...
disp = subprocess.Popen("uidisp 1", stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
(output, err) = disp.communicate()
uidisp1 = output
disp = subprocess.Popen("uidisp 2", stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
(output, err) = disp.communicate()
uidisp2 = output

# ----------------------------------------------------------------------
# Arrange Guis on the desktops
# ----------------------------------------------------------------------

arrangeGui(uidisp1, 'AutoDisplayB', 430, 25, 728, 861)
arrangeGui(uidisp1, 'AutoDisplayFPC', 1170, 25, 728, 861)
arrangeGui(uidisp2, 'AutoDisplayMAGIQ', 250, 25, 728, 861)
arrangeGui(uidisp2, 'eventsounds', 1600, 700, 0, 0)
arrangeGui(uidisp2, 'Alignment', 1000, 25, 0, 0)

sys.exit(0)
