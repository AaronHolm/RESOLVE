#!/usr/bin/env python
# coding: utf-8
"""
This script runs Resolve by:
1. Loading the model formulation
2. Loading data
3. Creating a problem instance
4. Solving the problem instance
5. Loading results
6. Writing results files

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

# Resolve modules
import load_data
import model_formulation
import export_results
import create_results_summary
import fileio

# Pyomo modules
from pyomo.environ import *
from pyomo.opt import ProblemFormat
from pyomo.opt import SolverFactory

# Third-party modules
import pandas as pd
import os
import sys
import datetime
from pyutilib.services import TempfileManager
import shutil

# Scenario to run is given as first script argument (0th argument is the script name)
# this must be the same name as a folder in the 'inputs' directory
scenario_name = sys.argv[1]

# set cbc as the default solver, but allow for other command line arguments
if len(sys.argv) >= 3:
    solver_name = sys.argv[2]
else:
    solver_name = "cbc"

if 'cloud' in sys.argv and solver_name == 'gurobi':
    cloud = True
else:
    cloud = False


# Directory structure
class DirStructure(object):
    """
    Directory and file structure.
    """

    def __init__(self, code_directory):
        self.CODE_DIRECTORY = code_directory
        self.DIRECTORY = os.path.join(self.CODE_DIRECTORY, "..")
        self.INPUTS_DIRECTORY = os.path.join(self.DIRECTORY, "inputs")
        self.RESULTS_DIRECTORY = os.path.join(self.DIRECTORY, "results")
        self.LOGS_DIRECTORY = os.path.join(self.DIRECTORY, "logs")
        self.SCENARIO_INPUTS_DIRECTORY = os.path.join(self.INPUTS_DIRECTORY, scenario_name)
        self.SCENARIO_RESULTS_DIRECTORY = os.path.join(self.RESULTS_DIRECTORY, scenario_name)
        self.SCENARIO_LOGS_DIRECTORY = os.path.join(self.LOGS_DIRECTORY, scenario_name)

    def make_directories(self):
        if not os.path.exists(self.RESULTS_DIRECTORY):
            os.mkdir(self.RESULTS_DIRECTORY)

        if not os.path.exists(self.LOGS_DIRECTORY):
            os.mkdir(self.LOGS_DIRECTORY)

        if not os.path.exists(os.path.join(self.RESULTS_DIRECTORY, scenario_name)):
            os.mkdir(os.path.join(self.RESULTS_DIRECTORY, scenario_name))

        if not os.path.exists(os.path.join(self.LOGS_DIRECTORY, scenario_name)):
            os.mkdir(os.path.join(self.LOGS_DIRECTORY, scenario_name))

    def get_feature_toggles(self):
        self.feature_toggles = fileio.dictfromfile(os.path.join(self.SCENARIO_INPUTS_DIRECTORY, 'feature_toggles.csv'),
                                                   header_as_keys=False, num_columns_as_keys=1, removerowblanks=True)


# Logging
class Logger(object):
    """
    The print statement will call the write() method of any object you assign to sys.stdout,
    so assign the terminal (stdout) and a log file as output destinations.
    """
    def __init__(self, directory_structure):
        self.terminal = sys.stdout
        self.log_file_path = os.path.join(directory_structure.LOGS_DIRECTORY, scenario_name,
            datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + "_" +
            str(scenario_name) + ".log")
        self.log_file = fileio.filewriter(self.log_file_path, buffering=1)

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()


def create_problem_instance(scenario_inputs_directory, feature_toggles):
    """
    Load model formulation and data, and create problem instance.
    :param scenario_inputs_directory:
    :param feature_toggles:
    :return: instance:
    """
    # Get model, load data, and solve
    print('Reading model...')
    model = model_formulation.resolve_model
    print('...model read.')

    print('Loading data...')
    data, flexible_params = load_data.scenario_data(
        scenario_inputs_directory, feature_toggles
    )
    print('...data read.')

    print('Compiling instance...')
    instance = model.create_instance(data)
    print('...instance created.')

    # example code for debugging via printing output
    # instance.THERMAL_RESOURCES.pprint()

    # just list out all the parameters that have changed value via the flexible_params functionality
    # so that people can look back at the log file for confirmation that the instance was created correctly
    if feature_toggles['debug']:
        print('\nParameters updated from default value:')
        params_updated = flexible_params.index.unique(level=0)
        for param_name in params_updated:
            print('  {}:'.format(param_name))
            resources = flexible_params.loc[
                pd.IndexSlice[param_name, :, :, :, :, :]
            ].index.unique(level=0)
            for idx in getattr(instance, param_name):
                if (
                    any(resource in idx for resource in resources) and
                    getattr(instance, param_name)[idx] != getattr(instance, param_name).__dict__['_default_val']
                ):
                    print(
                        '    {idx}: {value}'.format(
                        idx=idx, value=getattr(instance, param_name)[idx])
                    )

    return instance


def solve(instance, directory_structure):
    """Select solver and associated solver options.

    Args:
        instance (AbstractModel): Filled abstract model instance to solve.
        directory_structure (DirStructure): Directory structure and feature toggle object.

    Returns:
        solution (SolverResults): Solution to the abstract model instance.
    """
    # ### Solve ### #
    solver_io = 'lp'
    # Try to first use the local solvers subdirectory (which includes default CBC executable)
    os.environ['PATH'] = (
        os.path.join(directory_structure.DIRECTORY, 'solvers') +
        os.pathsep +
        os.environ['PATH']
    )
    solver_io = 'lp'
    solver = SolverFactory(solver_name, solver_io=solver_io)

    # solver options that lead to better performance
    if solver_name == "cplex":
        solver.options["lpmethod"] = 4
    elif solver_name == "gurobi":
        solver.options["MarkowitzTol"] = 0.5
        solver.options["Method"] = 2
        solver.options["Presolve"] = 1
        solver.options["ScaleFlag"] = 2
        solver.options["NumericFocus"] = 1
        solver.options["Aggregate"] = 0
        if cloud:
            solver.options['TimeLimit'] = 3600 * 12
    elif solver_name == "cbc":
        solver.options["ratio"] = 0.5
        #solver.options["threads"] = 4
        solver.options["threads"] = 12
        solver.options["startalg"] = "barrier"

    print('Solving...')
    if directory_structure.feature_toggles['debug']:
        keepfiles = True
        symbolic_solver_labels = True
    else:
        keepfiles = False
        symbolic_solver_labels = False

    if solver_name == "gurobi" and cloud:
        # only load get_gurobi_jobs if `cloud` is used
        try:
            import get_gurobi_jobs

            license_file = get_gurobi_jobs.check_cloud_status()
            os.environ['GRB_LICENSE_FILE'] = license_file
        except ImportError as error:
            print(
                'ImportError: {}. If you do not need to use Gurobi Instant Cloud and do not have access set up, please do not use the options "gurobi cloud".'
                .format(error.message)
            )

    # to keep human-readable LP files for debugging, set keepfiles = True
    solution = solver.solve(instance, keepfiles=keepfiles, tee=True, symbolic_solver_labels=symbolic_solver_labels)

    return solution


def get_objective_function_value(instance, scenario_results_directory):
    """
    Save the objective function value.
    :param instance:
    :param scenario_results_directory:
    :return:
    """
    print('\nObjective function value is: {:,.2f}'.format(instance.Total_Cost()))
    with fileio.filewriter(
        os.path.join(scenario_results_directory, "objective_function_value.txt")
    ) as objective_file:
        objective_file.write("Objective function value is: " + str(instance.Total_Cost()))


def run_scenario(directory_structure):
    """
    Run a scenario. Determine and create scenario directories, create problem instance, solve, and export results.
    :param directory_structure:
    :return:
    """

    # Directories
    scenario_inputs_directory = os.path.join(directory_structure.SCENARIO_INPUTS_DIRECTORY)
    scenario_results_directory = os.path.join(directory_structure.SCENARIO_RESULTS_DIRECTORY)
    scenario_logs_directory = os.path.join(directory_structure.SCENARIO_LOGS_DIRECTORY)

    # Write logs to this directory
    TempfileManager.tempdir = scenario_logs_directory

    # Create problem instance
    instance = create_problem_instance(scenario_inputs_directory, directory_structure.feature_toggles)

    # Create a 'dual' suffix component on the instance, so the solver plugin will know which suffixes to collect
    instance.dual = Suffix(direction=Suffix.IMPORT)

    # Solve
    solution = solve(instance, directory_structure)

    # Get objective function value
    get_objective_function_value(instance, scenario_results_directory)

    # Load and export results
    export_results.export_results(instance,
                                  solution,
                                  scenario_results_directory,
                                  debug_mode=1)

    # Create results summaries
    create_results_summary.create_summaries(scenario_results_directory)

    # Copy inputs passthrough to summary results for Results Tool
    shutil.copyfile(scenario_inputs_directory + r'/inputs_passthrough.csv',
        scenario_results_directory + r'/summary/inputs_passthrough.csv')

    print('Done.')


def main():
    code_directory = os.getcwd()
    dir_str = DirStructure(code_directory)
    dir_str.make_directories()
    dir_str.get_feature_toggles()
    logger = Logger(dir_str)
    log_file = logger.log_file_path
    print('Running scenario {}...'.format(scenario_name))
    print('Logging run to {}...'.format(log_file))
    stdout = sys.stdout
    sys.stdout = logger
    run_scenario(dir_str)
    sys.stdout = stdout  # return sys.stdout to original, just in case


if __name__ == "__main__":
    main()
