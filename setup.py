from setuptools import setup, find_packages
import re

VERSIONFILE = "src/crestmarkettrawler/_version.py"
verstr = "unknown"
try:
    verstrline = open(VERSIONFILE, "rt").read()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        verstr = mo.group(1)
except EnvironmentError:
    print "unable to find version in %s" % (VERSIONFILE,)
    raise RuntimeError("if %s exists, it is required to be well-formed" % (VERSIONFILE,))

setup(
    name='crestmarkettrawler',
    version=verstr,
    description='EVE Online CREST market trawler',
    author='James Muscat',
    author_email='jamesremuscat@gmail.com',
    url='https://github.com/jamesremuscat/CRESTMarketTrawler',
    packages=find_packages('src', exclude=["*.tests"]),
    package_dir = {'':'src'},
      long_description="""\
        A market trawler for EVE Online using the CREST API and uploading to the EMDR.
      """,
    setup_requires=[],
    tests_require=[],
    install_requires=["bz2file", "gevent", "psycopg2", "psycogreen", "pycrest", "python-dateutil", "requests", "ujson", "xmltodict"],
    entry_points={
        'console_scripts': [
            'CRESTMarketTrawler = crestmarkettrawler.trawler:main',
            ],
        }
      )
