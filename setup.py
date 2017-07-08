#!/usr/bin/env python

from distutils.core import setup
import os

ROOT = os.path.dirname(__file__)
if not ROOT:
    ROOT = '.'

VERSION='1.0.9'

setup(name='zipseeker',
      packages=['zipseeker'],
      version=VERSION,
      description='Create a streamable and (somewhat) seekable .ZIP file',
      long_description=open(ROOT + '/README.rst').read(),
      author='Ayke van Laethem',
      author_email='aykevanlaethem@gmail.com',
      url='https://github.com/aykevl/zipseeker',
      keywords=['zip', 'http', 'streaming'],
      download_url='https://github.com/aykevl/python-zipseeker/archive/v%s.zip' % VERSION,
     )
