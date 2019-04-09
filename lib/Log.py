from . import Version
Version.append('$Revision: 85432 $')
del Version


import sys
import traceback


def wrapper (function, *args, **kwargs):

    status = None

    try:
        result = function (*args, **kwargs)

    except SystemExit:
        exception = sys.exc_info ()[1]
        status = int (str (exception))

    except:
        exception = sys.exc_info ()
        status = 1

        type,value,trace = exception

        formatted = traceback.format_exception (type, value, trace)
        formatted = ''.join (formatted)
        formatted = formatted.rstrip ()
        formatted = formatted.replace ('\n', '\\n')

        terse = traceback.format_exception_only (type, value)
        terse = terse[0]

        # Log the full formatted traceback for debug. This is TBD.

        sys.stderr.write (terse)


    if status != None:
        # There was an exception. It was logged; stop running.
        sys.exit (status)


    return result



# vim: set expandtab tabstop=8 softtabstop=4 shiftwidth=4 autoindent:
