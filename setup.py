# setup.py for crow-serial (PyCrow)
# 23 April 2018
# Chris Siedell
# https://github.com/chris-siedell/PyCrow

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'long_description.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='crow-serial',
    version='0.3.0',
    description='A Crow serial protocol implementation',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='http://siedell.com/projects/Crow',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        ],
    keywords='serial protocol',
    project_urls={
        'Source':'https://github.com/chris-siedell/PyCrow',
        },
    packages=find_packages(),
    install_requires=['pyserial'],
    python_requires='>=3',
)


