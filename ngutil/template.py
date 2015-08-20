from pwd import getpwnam
from os import path, makedirs, chown, chmod

# NGUtil Libraries
from ngutil.common import _NGUtilCommon

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
            self.feedback.success('Created path -> {0}'.format(target_dir))
        
    def setup(self, template_id, target_file):
        """
        Select a template to use for further processing.
        """
        if not template_id in self._TEMPLATES:
            self.die('Invalid template ID: {0}'.format(template_id))
        self.feedback.info('Preparing to deploy \'{0}\' template to: {1}'.format(template_id, target_file))
            
        # Set the active template
        self.active = template_id
        self.target = target_file
        
        # Read the template into memory
        fh = open(self._TEMPLATES[template_id], 'r')
        self.contents = fh.read()
        fh.close()
        
    def setvars(self, args):
        """
        Set template substitution variables.
        """
        for k,v in args.iteritems():
            self.contents = self.contents.replace('{{{{{0}}}}}'.format(k), str(v))
            self.feedback.success('Updated template variable \'{0}\'-> {1}'.format(k,v))
            
    def deploy(self, owner='root', mode=644, overwrite=False):
        """
        Deploy the template file.
        """
        if path.isfile(self.target) and not overwrite:
            self.die('Cannot deploy template file, target \'{0}\' already exists.'.format(self.target))
            
        # Make sure the path to the file exists
        self._mkpath(self.target)
        
        # Create the file
        fh = open(self.target, 'w')
        fh.write(self.contents)
        fh.close()
        
        # Set permissions
        chown(self.target, getpwnam(owner).pw_uid, getpwnam(owner).pw_gid)
        chmod(self.target, mode)
        self.feedback.success('Deployed template -> {0}'.format(self.target))