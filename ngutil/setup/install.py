from setuptools.command.install import install as _install

class _PostInstall(object):
    """
    Post installation worker class.
    """
    def run(self):
        print 'Post install method run'

class NGUtilInstall(_install):
    """
    Custom installation wrapper.
    """
    def run(self):
        
        # Run the built-in installer first
        _install.run(self)

        # the second parameter, [], can be replaced with a set of parameters if _post_install needs any
        self.execute(_PostInstall().run, [], msg="Running post-installation tasks...")