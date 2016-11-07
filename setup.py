#!/usr/bin/env python
"""
   Copyright 2016 beardypig

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from os.path import abspath, dirname, join
from setuptools import setup, find_packages
from sys import path as sys_path

deps = [
    "construct==2.8.8"
]

srcdir = join(dirname(abspath(__file__)), "src/")
sys_path.insert(0, srcdir)

setup(name="pymp4",
      version="1.0.0",
      description="A Python parser for MP4 boxes",
      url="https://github.com/beardypig/pymp4",
      author="beardypig",
      author_email="beardypig@users.noreply.github.com",
      license="Apache 2.0",
      packages=find_packages("src"),
      package_dir={"": "src"},
      entry_points={
          "console_scripts": ["mp4dump=pymp4.cli:dump"]
      },
      install_requires=deps,
      test_suite="tests",
      classifiers=["Development Status :: 4 - Beta",
                   "Environment :: Console",
                   "Operating System :: POSIX",
                   "Programming Language :: Python :: 2.7",
                   "Programming Language :: Python :: 3.3",
                   "Programming Language :: Python :: 3.4",
                   "Programming Language :: Python :: 3.5",
                   "Programming Language :: Python :: 3.6",
                   "Topic :: Multimedia :: Sound/Audio",
                   "Topic :: Multimedia :: Video",
                   "Topic :: Utilities"])
