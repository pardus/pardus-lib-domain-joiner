#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages

changelog = 'debian/changelog'
if os.path.exists(changelog):
    head = open(changelog).readline()
    try:
        version = head.split("(")[1].split(")")[0]
    except:
        print("debian/changelog format is wrong for get version")
        version = ""
    f = open('pardus-domain-core/__version__', 'w')
    f.write(version)
    f.close()

data_files = [
    ("/usr/share/pardus/pardus-domain-settings/pardus-domain-core/",
     [
        "pardus-domain-core/__init__.py",
        "pardus-domain-core/config_manager.py",
        "pardus-domain-core/domain_joiner_ldap.py",
        "pardus-domain-core/domain_joiner_realmd.py",
        "pardus-domain-core/domain_joiner_winbind.py",
        "pardus-domain-core/domain_operations.py",
        "pardus-domain-core/__version__",
     ]),
    ("/usr/share/pam-configs/", ["data/pardus-pam-config"]),
]

setup(
    name="pardus-domain-core",
    version=version,
    packages=find_packages(),
    data_files=data_files,
    author="Büşra ÇAĞLIYAN",
    author_email="busra.cagliyan@pardus.org.tr",
    description="This application is a library for ui/cli applications that joins your computer to the domain or leaves it from the domain.",
    license="GPLv3",
    keywords="domain settings ldap realmd winbind pardus",
    url="https://www.pardus.org.tr",
)