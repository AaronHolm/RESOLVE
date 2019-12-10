"""
This script constains checks dependencies for the E3 RESOLVE Model.

############################ LICENSE INFORMATION ############################
This file is part of the E3 RESOLVE Model.

Copyright (C) 2019 Energy and Environmental Economics, Inc.
For contact information, go to www.ethree.com

The E3 RESOLVE Model is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

The E3 RESOLVE Model is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with the E3 RESOLVE Model (in the file LICENSE.TXT). If not,
see <http://www.gnu.org/licenses/>.
#############################################################################
"""


from setuptools import setup

setup(
    name='e3resolve',
    version='2019.2.0',
    description='E3 RESOLVE long-term investment planning and operations model',
    url='https://www.ethree.com',
    author='Energy + Environmental Economics',
    install_requires=[
        'Pyomo==5.6.6',
        'numpy>=1.13.3',
        'pandas>=0.24.0'
    ]
)
