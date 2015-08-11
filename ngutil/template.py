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
        
    def setup(self, template_id, target_file):
        """
        Select a template to use for further processing.
        """
        if not template_id in self._TEMPLATES:
            throw Exception('Invalid template ID: {}'.format(template_id))
            
        # Set the active template
        self.active = template_id
        self.target = target_file