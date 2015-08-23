#!/usr/bin/python
from setuptools import setup, find_packages

# ngutil
from ngutil import __version__
from ngutil.setup.install import NGUtilInstall

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