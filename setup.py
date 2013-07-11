#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from distutils.core import setup

setup(
    name="pawlabeling",
    packages=["pawlabeling"],
    version="0.0.1",
    description="GUI for labeling veterinary pressure measurements",
    author="Ivo Flipse",
    author_email="ivoflipse@flipserd.com",
    url = "www.flipserd.com/blog/ivoflipse",
    download_url="",
    platforms = ['Linux','Mac OSX','Windows XP/Vista/7/8'],
    classifiers=[
        "Programming Language :: Python",
        'License :: OSI Approved :: BSD License',
        "Development Status :: 2 - Pre-Alpha"
        "Operating System :: OS Independent",
        "Intended Audience :: End Users/Desktop",
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        "Topic :: Scientific/Engineering"
    ]
)

