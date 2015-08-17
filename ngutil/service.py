from feedback import Feedback
from subprocess import Popen, PIPE

class _NGUtilService(object):
    """
    Simple class wrapper for handling Linux services.
    """
    def __init__(self, name):
        
        # Service name
        self.name = name
        
        # Feedback handler
        self.feedback = Feedback(use_timestamp=True)
        
    def is_running(self):
        """
        Check if the service is running.
        """
        proc = Popen(['service', self.name, 'status'], stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        
        # Return the status
        return True if ('running' in out.rstrip()) else False
        
    def _do_service(self, state):
        """
        Wrapper for handling the service command argument.
        """
        proc = Popen(['service', self.name, state], stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        
        # Set the message prefix
        prefix = {
            'restart': 'Restarted',
            'stop':    'Stopped',
            'start':   'Started',
            'reload':  'Reloaded',
            'save':    'Saved'
        }
        
        # If error code returned
        if not proc.returncode == 0:
            self.feedback.error('Failed to {0} service \'{1}\': {2}'.format(state, self.name, err.rstrip()))
            return False
            
        # Service command success
        self.feedback.success('{0} \'{1}\' service...'.format(prefix[state], self.name))
        return True
        
    def _do_chkconfig(self, state):
        """
        Wrapper for running chkconfig.
        """
        proc = Popen(['chkconfig', self.name, state], stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        
        # State string
        state_str = ('enable', 'Enabled') if (state == 'on') else ('disable', 'Disabled')
        
        # Make sure the command succeeded
        if not proc.returncode == 0:
            self.feedback.error('Failed to {0} service: {1}, error={2}'.format(state_str[0], self.name, err.rstrip()))
            return False
            
        # Chkconfig command success
        self.feedback.success('{0} service: {1}'.format(state_str[1], self.name))
        return True
        
    def disable(self):
        """
        Disable the service.
        """
        self._do_chkconfig('off')
        
    def enable(self):
        """
        Enable the service.
        """
        self._do_chkconfig('on')
        
    def save(self):
        """
        Save the service (if the service supports this command).
        """
        self._do_service('save')
        
    def reload(self):
        """
        Reload the service.
        """
        self._do_service('reload')
        
    def stop(self):
        """
        Stop the service.
        """
        self._do_service('stop')
        
    def start(self):
        """
        Start the service.
        """
        return self._do_service('start')
        
    def restart(self):
        """
        Restart the service.
        """
        return self._do_service('restart')