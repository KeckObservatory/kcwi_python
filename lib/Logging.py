import logging, sys


class kcwiLog():
    def __init__(self):
        self.formatter = logging.Formatter('%(asctime)s - %(module)12s.%(funcName)20s - %(levelname)s: %(message)s')
        # set up logging to STDOUT for all levels DEBUG and higher
        self.mylogger = logging.getLogger('MyLogger')
        self.mylogger.setLevel(logging.DEBUG)
        # create shortcut functions
        self.debug = self.mylogger.debug
        self.info = self.mylogger.info
        self.warning = self.mylogger.warning
        self.error = self.mylogger.error
        self.critical = self.mylogger.critical

    def setStdout(self):
        self.sh = logging.StreamHandler(sys.stdout)
        self.sh.setLevel(logging.INFO)
        self.sh.setFormatter(self.formatter)
        self.mylogger.addHandler(self.sh)    # enabled: stdout

    def setFile(self, filename):
        # set up logging to a file for all levels DEBUG and higher
        self.fh = logging.FileHandler(filename)
        self.fh.setLevel(logging.DEBUG)
        self.fh.setFormatter(self.formatter)
        self.mylogger.addHandler(self.fh)    # enabled: file
        # Add log entries for versions of numpy, matplotlib, astropy, ccdproc
        self.info(sys.version)
        self.info('python version = {}.{}.{}'.format(sys.version_info.major,
                                        sys.version_info.minor,
                                        sys.version_info.micro))

