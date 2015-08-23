#!/usr/bin/python
from setuptools import setup, find_packages
from setuptools.command.install import install as _install

# Get the module version
from ngutil import __version__

def _post_install():
    """
    Post installation setup method.
    """
    print 'Post install method run'

class NGUtilInstall(install):
    """
    Custom installation wrapper.
    """
    def run(self):
        
        # Run the built-in installer first
        _install.run(self)

        # the second parameter, [], can be replaced with a set of parameters if _post_install needs any
        self.execute(_post_install, [], msg="Running post-installation tasks...")

# Run the setup
setup(
    name             = 'ngutil',
    version          = __version__,
    description      = 'Python package to help install and configure sites with nginx and php-fpm.',
    long_description = open('DESCRIPTION.rst').read(),
    author           = 'Brandon Wood',
    author_email     = 'bwood05@gmail.com',
    url              = 'http://github.com/bwood05/ngutil',
    license          = 'GPLv3',
    packages         = find_packages(),
    keywords         = 'web nginx virtual host http configuration',
    install_requires = ['wget', 'feedback'],
    entry_points     = {
          'console_scripts': [
              'ngutil = ngutil:cli'
        ]
    },
    cmdclass         = {
        'install': NGUtilInstall
    },
    classifiers      = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Terminals',
        'Topic :: System :: Systems Administration',
        'Topic :: System :: Shells',
        'Topic :: Internet :: WWW/HTTP :: Site Management'
    ],
    include_package_data = True,
    
)