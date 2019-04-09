''' Library functions to simplify common actions with KCWI.
.. moduleauthor:: L.Rizzi, K. Lanclos
'''

# Import all subcomponents of this module. It's important not to
# adjust the namespace until all subcompoents have been imported;
# otherwise, the subcomponent has to use the revised namespace.

from . import Blue
from . import Calibration
from . import BlueWrapper
from . import Helper
from . import Log
from . import Procs
from . import PowerInit
#from . import Red
#from . import RedWrapper
from . import Version

_Blue = Blue
_BlueWrapper = BlueWrapper
#_Red = Red
#_RedWrapper = RedWrapper

#Blue = _BlueWrapper
#Red = RedWrapper


def verbose (selection=True):
    ''' Enable normal tracebacks from all called functions
        without automatically catching and logging them as
        is done for the wrapped functions.
    '''

    global Blue
    #global Red

    if selection == True:
        Blue = _Blue
        #Red = _Red
    else:
        Blue = _BlueWrapper
        #Red = _RedWrapper



# Clean up the name space after importing all subcomponents.

version = Version.version
Version.append('$Revision: 85432 $')
del Version


# vim: set expandtab tabstop=8 softtabstop=4 shiftwidth=4 autoindent:
