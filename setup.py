__author__ = ",".join([ "KnowledgeLinks", "Jeremy Nelson", "Mike Stabile"])
__author_email__ = ','.join(['knowledgelinks.io@gmail.com',
                             'jermnelson@gmail.com',
                             'mstabile75@gmail.com'
                            ])
__license__ = "GPLv3"
__version__ = "0.0.38"

from setuptools import find_packages, setup

def readme():
    readme = ''
    try:
        with open('README.md') as rm_fo:
            readme = rm_fo.read()
    except FileNotFoundError:
        readme = "Not set"
    return readme


setup(
    name='rdfframework',
    version= __version__,
    author=__author__,
    author_email= __author_email__,
    description="Application builder for KnowledgeLinks.io RDF applications.",
    long_description=readme(),
    keywords='RDF linked data application builder',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    platforms='any',
    install_requires=[
        'urllib3<1.22,>=1.21.1',
        'click',
        'elasticsearch>5.4.0,<6',
        'elasticsearch_dsl',
        'Flask',
        'Flask-WTF',
        'isodate',
        'Markdown',
        'lxml',
        'passlib',
        'rdflib',
        'requests',
        'dateutils',
        'beautifulsoup4',
        'cssselect',
        'colorama',
        'jsonpath_ng'
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: Database",
        "Topic :: Text Processing :: General",
        "Topic :: Text Processing :: Indexing",
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application'
    ],
    package_data = {
        'rdfframework.datamanager.vocabularies': ["*.*"],
        'rdfframework.sparql.queries': ["*.rq"],
        'rdfframework.turtle': ["*.ttl"]
    },
    url='https://github.com/KnowledgeLinks/rdfframework/tree/development',
    # test_suite='nose.collector',
    # tests_require=['nose', 'nose-cover3'],
    zip_safe=False
)
