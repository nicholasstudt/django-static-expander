#!/usr/bin/env python

from distutils.core import setup

setup(
    name = "Expander",
    version = '0.0.1',
    author = 'Nicholas Studt',
    author_email = 'nicholas@photodwarf.org',
    description = 'Apply templates to files on disk.',
    package_dir = {'apps.expander': 'lib'},
    packages = ['apps.expander'],

#    scripts = ['django/bin/django-admin.py'],
)

