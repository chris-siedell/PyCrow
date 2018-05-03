# setup.py
# For crow-serial (PyCrow)
# 2 May 2018
# Chris Siedell
# project: https://pypi.org/project/crow-serial/
# source: https://github.com/chris-siedell/PyCrow
# homepage: http://siedell.com/projects/Crow/


from setuptools import setup, find_packages
from codecs import open
from os import path
import io
import os
import re


here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


# This strategy of keeping the version string in the __init__
#  file -- as well as the code to implement it -- comes from PySerial.

def read(*names, **kwargs):
    """Python 2 and Python 3 compatible text file reading.
    Required for single-sourcing the version string.
    """
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8")
    ) as fp:
        return fp.read()

def find_version(*file_paths):
    """
    Search the file for a version string.
    file_path contain string path components.
    Reads the supplied Python module as text without importing it.
    """
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

version = find_version('crow', '__init__.py')


setup(
    name='crow-serial',
    version=version,
    description='Host implementation of the Crow serial protocol.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='http://siedell.com/projects/Crow',
    author='Chris Siedell',
    author_email='chris@siedell.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        ],
    keywords='serial protocol',
    project_urls={
        'Source':'https://github.com/chris-siedell/PyCrow',
        'Homepage':'http://siedell.com/projects/Crow',
        },
    packages=find_packages(),
    install_requires=['pyserial'],
    python_requires='>=3',
)


