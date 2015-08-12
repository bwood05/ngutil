from os import path, makedirs
from sys import exit, stderr
from subprocess import Popen, PIPE

from ngutil import __root__

class _NGUtilCommon(object):
    """
    Common class for sharing methods and attributes between NGUtil classes.
    """
    def __init__(self):
        
        # Data directory
        self._DATA  = '{0}/data'.format(__root__)
        
        # Template ID / file mappings
        self._TEMPLATES = {
            'FPM':      self._data_map('fpm.conf.template'),
            'NG_REPO':  self._data_map('nginx.repo.template'),
            'NG_CONF':  self._data_map('nginx.conf.template'),
            'NG_HTTP':  self._data_map('site.http.conf'),
            'NG_HTTPS': self._data_map('site.https.conf')
        }
        
    def _data_map(self, FILE):
        """
        Map a file to the data directory.
        """
        return '{0}/{1}'.format(self._DATA, FILE)
        
    def mkdir(self, dir):
        """
        Make directory if it doesn't exist.
        """
        if not path.isdir(dir):
            makedirs(dir)
        
    def run_command(self, cmd, expects=0, shell=False):
        """
        Run a shell command with Popen
        """
        
        # If the command argument is a string
        if isinstance(cmd, str):
            cmd = cmd.split(' ')
        
        # Open the process
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=shell)
        out, err = proc.communicate()
        
        # Make sure the expected return code is found
        if not proc.return_code == expects:
            self.die('Failed to run command \'{0}\', ERROR={1}'.format(' '.join(cmd), err.readlines()))
            
        # Return exit code / stdout / stderr
        return proc.return_code, out, err
        
    def die(self, msg, code=1):
        """
        Print on stderr and die.
        """
        stderr.write('ERROR: {0}\n'.format(msg))
        exit(code)