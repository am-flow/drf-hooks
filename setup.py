try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup  # if setuptools breaks

# Dynamically calculate the version
version_tuple = __import__('drf_hooks').VERSION
version = '.'.join([str(v) for v in version_tuple])

setup(
    name = 'drf-hooks',
    description = 'A powerful mechanism for sending real time API notifications via a new subscription model.',
    version = version,
    author = 'Angira Tripathi',
    author_email = 'angira.tripathi@am-flow.com',
    url = 'http://github.com/am-flow/drf-hooks',
    install_requires=['Django>=3.1', 'requests'],
    packages=['drf_hooks'],
    package_data={
        'drf_hooks': [
            'migrations/*.py',
        ]
    },
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
    ],
)
