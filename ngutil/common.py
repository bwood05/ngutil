from os import path
from sys import exit, stderr

class _NGUtilCommon(object):
    """
    Common class for sharing methods and attributes between NGUtil classes.
    """
    def __init__(self, is_cli):
        
        # Command line flag
        self.is_cli = is_cli
        
        # Root / data directory
        self._ROOT  = path.abspath(path.dirname(__file__))
        self._DATA  = '{}/data'.format(self.ROOT)
        
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
        return '{}/{}'.format(self._DATA, FILE)
        
    def die(self, msg, code=1):
        """
        Print on stderr and die.
        """
        if self.is_cli:
            stderr.write('ERROR: {}\n'.format(msg))
            exit(code)
        else:
            raise Exception(msg)