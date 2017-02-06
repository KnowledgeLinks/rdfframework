__author__ = ",".join([ "Jeremy Nelson", "Mike Stabile"])
__license__ = "GPLv3"
with open('VERSION') as v_fo:
     __version__ = v_fo.read()

from setuptools import find_packages, setup

def readme():
    with open('README.md') as rm_fo:
        return rm_fo.read()

setup(
    name='rdfframework',
    version= __version__,
    author=__author__,
    author_email= ','.join(['jermnelson@gmail.com', 
                            'mstabile75@gmail.com',
                            'knowledgelinks.io@gmail.com']),
    description="Application builder for KnowledgeLinks.io RDF vocabulary.",
    long_description=readme(),
    keywords='RDF linked data application builder',
    packages=find_packages(),
    include_package_data=True,
    platforms='any',
    install_requires=[
        'flask',
        'Flask-Login',
        'Flask-WTF',
        'passlib',
        'requests',
        'dateutils'
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
    ],
    url='https://github.com/KnowledgeLinks/rdfframework/tree/development',
    test_suite='nose.collector',
    tests_require=['nose', 'nose-cover3'],
    zip_safe=False
)