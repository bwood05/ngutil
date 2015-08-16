from pwd import getpwnam
from grp import getgrnam
from sys import exit, stderr
from feedback import Feedback
from subprocess import Popen, PIPE
from os import path, makedirs, chown, listdir

# ngutil
from ngutil import __root__

class _NGUtilCommon(object):
    """
    Common class for sharing methods and attributes between NGUtil classes.
    """
    def __init__(self):
        
        # Feedback handler
        self.feedback = Feedback(use_timestamp=True)
        
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
        
    def die(self, msg, code=1):
        """
        Print on stderr and die.
        """
        self.feedback.error(msg)
        exit(code)
        
    def _data_map(self, FILE):
        """
        Map a file to the data directory.
        """
        return '{0}/{1}'.format(self._DATA, FILE)
        
    def mkfile(self, _path, contents=None, overwrite=False):
        """
        Make a new file and optionally write data to it.
        """
        if path.isfile(_path) and not overwrite:
            self.die('Cannot make file "{0}". Already exists and overwrite={1}'.format(_path, repr(overwrite)))
        
        # Make the file
        fh = open(_path, 'w')
        
        # If writing contents
        if contents:
            fh.write(contents)
        
        # Close the file
        fh.close()
        
        # Return the path
        return _path
        
    def mkdir(self, dir):
        """
        Make directory if it doesn't exist.
        """
        if not path.isdir(dir):
            makedirs(dir)
            self.feedback.success('Created directory: {0}'.format(dir))
        else:
            self.feedback.info('Directory \'{0}\' already exists, skipping...'.format(dir))
        
    def run_command(self, cmd, expects=0, shell=False, stdout=PIPE, stderr=PIPE):
        """
        Run a shell command with Popen
        """
        
        # If the command argument is a string
        if isinstance(cmd, str):
            cmd = cmd.split(' ')
        
        # Open the process
        try:
            proc = Popen(cmd, stdout=stdout, stderr=stderr, shell=shell)
            out, err = proc.communicate()
            
            # Make sure the expected return code is found
            if not proc.returncode == expects:
                self.die('Failed to run command \'{0}\', ERROR={1}'.format(str(cmd), err))
                
            # Return exit code / stdout / stderr
            return proc.returncode, out, err
        except Exception as e:
            self.die('Failed to run command \'{0}\': ERROR={1}'.format(str(cmd), str(e)))
            
class _NGUtilSELinux(_NGUtilCommon):
    """
    Class wrapper for handling SELinux interactions.
    """
    def __init__(self):
        super(_NGUtilSELinux, self).__init__()

        # Check if SELinux is available
        try:
            import selinux
            self._selinux = selinux
            
            # Enforcing / status
            self.enforcing = True if selinux.security_getenforce() == 1 else False
            self.enabled   = True if selinux.is_selinux_enabled() == 1 else False 
            
            # If SELinux found and enabled
            if self.enabled:
                self.feedback.info('SELinux found on current system: enforcing={0}'.format(repr(self.enforcing)))
            
            # SELinux disabled
            else:
                self.feedback.info('SELinux disabled on current system...')
            
        # SELinux not available
        except:
            self.feedback.info('SELinux not available on current system')
            self.enabled = False

    def add_port(self, port, proto, context):
        if self.enabled:
            self.run_command('semanage port -a -t {0} -p {1} {2}'.format(context, proto, port), shell=True)

    def chcon(self, path, context, recursive=False):
        if self.enabled:
            self._selinux.chcon(path, context, recursive)