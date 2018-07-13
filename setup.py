"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/rickalm/python-bamboo-api
"""
__author__ = 'rickalm'

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='bamboo_api',

    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.2.0`',

    description='Bamboo API Client',
    long_description=long_description,
    url='https://github.com/rickalm/python-bamboo-api',
    author='Rick Alm',
    author_email='rickealm@gmail.com',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3',
    ],

    keywords='api bitbucket bamboo rest api client',
    packages=find_packages(exclude=['contrib', 'docs', 'test*']),

    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'requests',
        'bs4',
    ],
    extras_require={},
    package_data={},

    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    data_files=[],

)

setup(
    name='bitbucket_api',

    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.2.0`',

    description='Bitbucket API Client',
    long_description=long_description,
    url='https://github.com/rickalm/python-bamboo-api',
    author='Rick Alm',
    author_email='rickealm@gmail.com',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3',
    ],

    keywords='api bitbucket bamboo rest api client',
    packages=find_packages(exclude=['contrib', 'docs', 'test*']),

    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'requests',
        'bs4',
    ],
    extras_require={},
    package_data={},

    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    data_files=[],

)
