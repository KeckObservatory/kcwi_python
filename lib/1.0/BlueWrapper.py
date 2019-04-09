from . import Version
Version.append ('$Revision: 85432 $')
del Version


from . import Blue
from . import Log


def filter (*args, **kwargs):
    return Log.wrapper (Blue.filter, *args, **kwargs)


# vim: set expandtab tabstop=8 softtabstop=4 shiftwidth=4 autoindent:
