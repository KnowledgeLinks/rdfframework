__author__ = ",".join([ "Jeremy Nelson", "Mike Stabile"])
__license__ = "GPLv3"
__version_info__ = ('0', '8', '0')
__version__ = '.'.join(__version_info__)

from setuptools import find_packages, setup

setup(
    name='rdfframework',
    version= __version__,
    author=__author__,
    author_email= ','.join(['jermnelson@gmail.com', 
                             'mstabile75@gmail.com']),
    description="RDFFramework for issuing OpenBadges",
    long_description="",
    packages=find_packages(),
    include_package_data=True,
    platforms='any',
    install_requires=[
        'flask',
        'rdflib',
        'requests'
    ],
    classifiers=[
        'Framework :: Flask',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application'
    ]
)
