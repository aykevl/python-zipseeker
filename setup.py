#!/usr/bin/env python

from distutils.core import setup

VERSION='1.0.7'

setup(name='zipseeker',
      packages=['zipseeker'],
      version=VERSION,
      description='Create a streamable and (somewhat) seekable .ZIP file',
      long_description=open('README.rst').read(),
      author='Ayke van Laethem',
      author_email='aykevanlaethem@gmail.com',
      url='https://github.com/aykevl/zipseeker',
      keywords=['zip', 'http', 'streaming'],
      download_url='https://github.com/aykevl/python-zipseeker/archive/v%s.zip' % VERSION,
     )
