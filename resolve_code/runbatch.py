#!/usr/bin/env python
# coding: utf-8
"""
E3 RESOLVE

Wrapper script that runs a batch of Resolve cases:
1. Reads cases_to_run.csv file
2. Runs Resolve in series using the run_opt.py script for each of these cases

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

# Runs a batch of cases specified in cases_to_run.csv
# Solver name can be specified

import os
import csv
import multiprocessing
import sys


def run_parallel_case(case):
    print('Running scenario in parallel: {}'.format(case))
    command = 'python run_opt.py {} gurobi cloud'.format(case)
    os.system(command)


def main():
    # set cbc as the default solver, but allow for other command line arguments
    if len(sys.argv) >= 2:
        solver_name = sys.argv[1]  # 0th argument is script name
    else:
        solver_name = "cbc"

    if 'cloud' in sys.argv and solver_name == 'gurobi':
        cloud = True
    else:
        cloud = False

    cases_to_run = []
    starting_dir = os.getcwd()

    with open(os.path.join(starting_dir, 'cases_to_run.csv')) as infile:
        csvreader = csv.reader(infile, delimiter=',')
        for row in csvreader:
            cases_to_run += row

    # Figure out how many parallel jobs to run
    if not [idx for idx, s in enumerate(sys.argv) if 'parallel=' in s]:
        parallel_jobs = 1
    else:
        parallel_jobs = min(
            len(cases_to_run),
            int(sys.argv[
                [idx for idx, s in enumerate(sys.argv) if 'parallel=' in s][0]
            ].split('parallel=')[1])
        )
        print('Running {} jobs in parallel'.format(parallel_jobs))

    if cloud and parallel_jobs > 1:
        # scale pool for number of parallel jobs
        import get_gurobi_jobs
        get_gurobi_jobs.check_cloud_status(parallel_jobs)

        # start solving in parallel
        pool = multiprocessing.Pool(processes=parallel_jobs)
        pool.map(run_parallel_case, cases_to_run)
        pool.close()
        pool.join()
    else:
        for case in cases_to_run:
            print(
                'Running scenario {} of {}: {}'
                .format(cases_to_run.index(case) + 1, len(cases_to_run), case)
            )
            command = "python run_opt.py " + case + ' ' + solver_name
            if cloud:
                command += " cloud"
            os.system(command)


if __name__ == '__main__':
    main()
