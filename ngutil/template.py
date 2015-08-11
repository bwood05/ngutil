from pwd import getpwnam
from os import path, makedirs, chown, chmod

# NGUtil Libraries
from .common import _NGUtilCommon

class _NGUtilTemplates(_NGUtilCommon):
    """
    Class for handling loading and updating template files.
    """
    def __init__(self):
        super(_NGUtilTemplates, self).__init__()
        
        # Active template / target file
        self.active = None
        self.target = None
        
        # Template contents
        self.contents = None
        
    def _mkpath(self, file):
        """
        Make sure the path to a file exists.
        """
        
        # Target directory
        target_dir = path.dirname(file)
        
        # Make sure the directory exists
        if not path.isdir(target_dir):
            makedirs(target_dir)
        
    def setup(self, template_id, target_file):
        """
        Select a template to use for further processing.
        """
        if not template_id in self._TEMPLATES:
            throw Exception('Invalid template ID: {}'.format(template_id))
            
        # Set the active template
        self.active = template_id
        self.target = target_file
        
        # Read the template into memory
        fh = open(self._TEMPLATES[template_id], 'r')
        self.contents = fh.read()
        fh.close()
        
    def setvars(self, **kwargs):
        """
        Set template substitution variables.
        """
        for k,v in kwargs.iteritems():
            self.contents.replace('{{{{{0}}}}}'.format(k), v)
            
    def deploy(self, owner='root', mode=644):
        """
        Deploy the template file.
        """
        if path.isfile(self.target):
            self.die('Cannot deploy template file, target \'{}\' already exists.'.format(self.target))
            
        # Make sure the path to the file exists
        self._mkpath(self.target)
        
        # Create the file
        fh = open(self.target, 'w')
        fh.write(self.contents)
        fh.close()
        
        # Set permissions
        chown(self.target, getpwnam(owner).pw_uid, getpwnam(owner).pw_gid)
        chmod(self.target, mode)