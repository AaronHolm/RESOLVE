#!/usr/bin/env python

"""
This script exports results.

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

import os
import csv
import traceback
import sys
import pdb

import fileio

def export_results(instance, results, results_directory, debug_mode):
    """
    Export Resolve results. This function is called from run_opt.py.
    It retrieves the relevant sets over which it will loop, then call functions to export different result categories.
    If an exception is encountered, log the error traceback. If not in debug mode, exit. If in debug mode,
    open an interactive Python session that will make it possible to try to correct the error without having to re-run
    problem; quitting the interactive session will resume running the next export function, not exit.
    :param instance: the problem instance
    :param results: the results
    :param results_directory: directory to export results files to
    :param debug_mode:
    :return:
    """

    print('Exporting results... ')

    # First, load solution
    load_solution(instance, results)

    # Call various export functions
    # Export loads and power balance
    try:
        export_loads_and_power_balance(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting loads and power balance! Check export_loads_and_power_balance()."
        handle_exception(msg, debug_mode)

    # Export builds, capital costs, and fixed O&M costs
    try:
        export_resource_build(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting resource builds! Check export_resource_build()."
        handle_exception(msg, debug_mode)

    try:
        export_storage_build_variables(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting storage builds! Check export_storage_build_variables()."
        handle_exception(msg, debug_mode)

    # Export hourly operations
    try:
        export_hourly_operations(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting hourly operations! Check export_hourly_operations()."
        handle_exception(msg, debug_mode)

    # Export hourly transmission flows
    try:
        export_transmission_flows(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting hourly transmission flows! Check export_transmission_flows()."
        handle_exception(msg, debug_mode)

    # Export simultaneous flow group duals
    try:
        simultaneous_transmission_flow_duals(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting simultaneous flow group duals! Check simultaneous_transmission_flow_duals()."
        handle_exception(msg, debug_mode)

    # Export curtailment
    try:
        export_curtailment(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting curtailment! Check export_curtailment()."
        handle_exception(msg, debug_mode)

    # Export planning reserve margin and ELCC surface results
    try:
        export_planning_reserve_margin(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting planning reserve margin or ELCC surface results! Check export_planning_reserve_margin()."
        handle_exception(msg, debug_mode)

    # Export energy sufficiency results
    if instance.energy_sufficiency:
        try:
            export_energy_sufficiency(instance, results_directory)
        except Exception as err:
            msg = "ERROR exporting energy sufficiency results! Check export_energy_sufficiency()."
            handle_exception(msg, debug_mode)

    # Export RPS results
    try:
        export_rps(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting RPS results! Check export_rps()."
        handle_exception(msg, debug_mode)

    # Record resource-specific local capacity values
    try:
        export_local_capacity_resources(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting local capacity resources! Check export_local_capacity_resources()."
        handle_exception(msg, debug_mode)

    # Record GHG constraint targets and duals.
    try:
        export_ghg(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting GHG! Check export_ghg()."
        handle_exception(msg, debug_mode)

    # Export transmission costs
    try:
        export_transmission_costs(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting transmission costs! Check export_transmission_costs()."
        handle_exception(msg, debug_mode)

    if instance.allow_tx_build:
        try:
            export_transmission_build(instance, results_directory)
        except Exception as err:
            msg = "ERROR exporting transmission build! Check export_transmission_build()."
            handle_exception(msg, debug_mode)

    # Export fuel burn
    try:
        export_fuel_burn(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting fuel burn! Check export_fuel_burn()."
        handle_exception(msg, debug_mode)

    # Export ghg imports into the ghg target area
    try:
        export_ghg_imports(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting ghg imports into the ghg target area! Check export_ghg_imports()."
        handle_exception(msg, debug_mode)

    # Export the duals of reserve constraints that are indexed by the set of timepoints
    try:
        export_reserve_timepoints(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting reserve timepoint duals + violations! Check export_reserve_timepoints()."
        handle_exception(msg, debug_mode)

    # Export the duals of the ramping constraints
    try:
        export_ramping_duals_by_timepoint(instance, results_directory)
    except Exception as err:
        msg = "ERROR exporting ramping duals timepoint duals! Check export_ramping_duals_by_timepoint()."
        handle_exception(msg, debug_mode)

    # Export Hydro multi-day sharing daily budget increase information
    if instance.multi_day_hydro_energy_sharing:
        try:
            export_hydro_daily_budget_changes(instance, results_directory)
        except Exception as err:
            msg = "ERROR exporting hydro daily budget changes! Check export_hydro_daily_budget_changes()."
            handle_exception(msg, debug_mode)

    # Export Line limits changes if resource_tx_use is enabled
    if instance.resource_use_tx_capacity:
        try:
            export_line_limits_resource_tx_use(instance, results_directory)
        except Exception as err:
            msg = "ERROR exporting dedicated imports' changes to line limits! Check export_line_limits_resource_tx_use()."
            handle_exception(msg, debug_mode)


# formatting functions
# return two decimal places
def format_2f(input_data):
    """
    :param input_data: The data to format
    :return:
    """
    if input_data is None:
        formatted_data = None
    else:
        formatted_data = '{:0.2f}'.format(input_data)
        # if formatted_data is negative but rounds to zero, it will be printed as a negative zero
        # this gets rid of the negative zero
        if formatted_data == '0.00' or formatted_data == '-0.00':
            formatted_data = 0
    return formatted_data


# return six decimal places
def format_6f(input_data):
    """
    :param input_data: The data to format
    :return:
    """
    if input_data is None:
        formatted_data = None
    else:
        formatted_data = '{:0.6f}'.format(input_data)
        # if formatted_data is negative but rounds to zero, it will be printed as a negative zero
        # this gets rid of the negative zero
        if formatted_data == '0.000000' or formatted_data == '-0.000000':
            formatted_data = 0
    return formatted_data


# #################### Data Exports #################### #
def load_solution(instance, results):
    """
    Load results. This function is called by export_results().
    :param instance:
    :param results:
    :return:
    """
    instance.solutions.load_from(results)


def export_loads_and_power_balance(instance, results_directory):
    """
    This file contains hourly loads for each zone and timepoint that were input into the RESOLVE optimization,
    as well as the amount of overgeneration and unserved energy for each zone and timepoint.
    It also contains the shadow price of the zonal power balance constraint for each timepoint,
    which is analogous to the hourly energy price.
    Care should be taken interpreting this energy price as the RESOLVE investment framework differs
    in several fundamental ways from a conventional production simulation.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...loads and power balance...')

    loads_and_balance_writer = fileio.csvwriter(os.path.join(results_directory, "loads_and_power_balance.csv"))
    loads_and_balance_writer.writerow([
        "zone",
        "period",
        "timepoint_id",
        "day_id",
        "hour_of_day",
        "day_weight",
        "input_load_mw",
        "hourly_energy_cost_$_per_mwh",
        "unserved_energy_mw",
        "overgeneration_mw",
        "total_generation_mw",
        "unbundled_rps_generation_mw",
        "storage_charging_mw",
        "flexible_ev_load_mw",
        "flexible_load_shift_mw",
        "hydrogen_electrolysis_load_mw",
        "ee_ftm_load_reduction_mw"
    ])

    for zone in instance.ZONES:
        for timepoint in instance.TIMEPOINTS:

            # discount_and_day_weight un-discounts the periods and un-weighs the days to obtain intuitive dual values.
            discount_and_day_weight = \
                instance.discount_factor[instance.period[timepoint]] * instance.day_weight[instance.day[timepoint]]

            if instance.allow_unserved_energy:
                unserved_energy = instance.Unserved_Energy_MW[zone, timepoint].value
            else:
                unserved_energy = 0

            generation = 0
            unbundled_rps_generation = 0
            storage_charging = 0
            hydrogen_electrolysis_load = 0
            flexible_ev_load = 0
            ee_load_reduction = 0
            flexible_load_shift = 0

            # Aggregate generation and storage charging by zone for given timepoint
            for resource in instance.RESOURCES:

                # Sum all generation in zone
                if instance.zone[resource] == zone:

                    # Aggregate generation by zone
                    if resource in instance.HYDROGEN_ELECTROLYSIS_RESOURCES:
                        # Aggregate hydrogen electrolysis load by zone
                        hydrogen_electrolysis_load += instance.Hydrogen_Electrolysis_Load_MW[resource, timepoint].value
                    # Aggregate EV loads of all EV resources
                    elif resource in instance.EV_RESOURCES:
                        flexible_ev_load += instance.Charge_EV_Batteries_MW[resource, timepoint].value
                    # EE load impact
                    elif resource in instance.EE_PROGRAMS:
                        ee_load_reduction += instance.EE_Reduced_Load_FTM_MW[resource, timepoint]()
                    # Flexible loads
                    elif resource in instance.FLEXIBLE_LOAD_RESOURCES:
                        flexible_load_shift += instance.Shift_Load_Up_MW[resource, timepoint].value
                        flexible_load_shift -= instance.Shift_Load_Down_MW[resource, timepoint].value
                    else:
                        generation += instance.Provide_Power_MW[resource, timepoint].value

                        # Aggregate generation contracted to but not balanced by the RPS zone (unbundled RECs).
                        if zone not in instance.RPS_ZONES and resource in instance.RPS_ELIGIBLE_RESOURCES:
                            unbundled_rps_generation += instance.Provide_Power_MW[resource, timepoint].value

                    # Aggregate storage charging by zone
                    if resource in instance.STORAGE_RESOURCES:
                        storage_charging += instance.Charge_Storage_MW[resource, timepoint].value

            # the dual value (or shadow price) of the zonal power balance constraint is the closest thing
            # to an hourly energy cost that Resolve calculates
            loads_and_balance_writer.writerow([
                zone,
                instance.period[timepoint],
                timepoint,
                instance.day[timepoint],
                instance.hour_of_day[timepoint],
                instance.day_weight[instance.day[timepoint]],
                format_2f(instance.input_load_mw[zone, timepoint]),
                format_2f(instance.dual[instance.Zonal_Power_Balance_Constraint[zone, timepoint]]
                          / discount_and_day_weight),
                format_2f(unserved_energy),
                format_2f(instance.Overgeneration_MW[zone, timepoint].value),
                format_2f(generation),
                format_2f(unbundled_rps_generation),
                format_2f(storage_charging),
                format_2f(flexible_ev_load),
                format_2f(flexible_load_shift),
                format_2f(hydrogen_electrolysis_load),
                format_2f(ee_load_reduction)
            ])


def export_resource_build(instance, results_directory):
    """
    This file contains the investment decisions made by RESOLVE for each candidate resource in each period
    as well as the capacities of resources for which no investment decisions were made
    (e.g. existing resources and contracted resources that come online at some point in the future).
    The fully deliverable/energy only status of new renewable resources is included.
    Blanks cells indicate that RESOLVE does not make this decision.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...resource build...')

    build_writer = fileio.csvwriter(os.path.join(results_directory, "resource_build.csv"))
    build_writer.writerow([
        "period",
        "resource",
        "zone",
        "contract",
        "technology",
        "planned_capacity_mw",
        "new_build_mw",
        "cumulative_new_build_mw",
        "operational_capacity_mw",
        "transmission_zone",
        "fully_deliverable_capacity_mw",
        "energy_only_capacity_mw",
        "new_build_flexible_load_capacity_mwh_per_day",
        "total_flexible_load_capacity_mwh_per_day",
        "hydrogen_electrolysis_capacity_mw",
        "capacity_limit_dual_$",
        "unit_size_mw",
        "operational_units",
        "capital_cost_$",
        "fixed_o_and_m_cost_$",
        "period_discount_factor",
        "operational_planned_capacity_mw",
        "retired_planned_capacity_mw",
        "operational_new_capacity_mw",
        "retired_new_capacity_mw",
        "min_cumulative_new_build_mw"
    ])

    for period in instance.PERIODS:
        for resource in instance.RESOURCES - instance.EV_RESOURCES:

            # Resources where new capacity can be built
            if resource in instance.NEW_BUILD_RESOURCES:
                build_capacity_mw = instance.Build_Capacity_MW[resource, period].value
                cumulative_new_installed_capacity_mw = \
                    instance.Cumulative_New_Installed_Capacity_MW[resource, period]()
                operational_new_capacity_mw = instance.Operational_New_Capacity_MW[resource, period]()
                # calculate capital costs
                capital_cost = instance.Capital_Cost_Annual_In_Period_Dollars[resource, period]()
                min_cumulative_new_build_mw = instance.min_cumulative_new_build_mw[resource, period]
            else:
                build_capacity_mw = None
                cumulative_new_installed_capacity_mw = None
                operational_new_capacity_mw = None
                min_cumulative_new_build_mw = None
                if resource in instance.FLEXIBLE_LOAD_RESOURCES:
                    capital_cost = instance.Flexible_Load_DR_Cost[resource, period].value
                else:
                    capital_cost = None

            # report deliverability/energy only capacity only for resources in the set TX_DELIVERABILITY_RESOURCES
            if resource in instance.TX_DELIVERABILITY_RESOURCES:
                transmission_zone = instance.tx_zone_of_resource[resource]
                fully_deliverable_capacity_mw = \
                    instance.Fully_Deliverable_Installed_Capacity_MW[resource, period].value
                energy_only_capacity_mw = instance.Energy_Only_Installed_Capacity_MW[resource, period].value
            else:
                transmission_zone = None
                fully_deliverable_capacity_mw = None
                energy_only_capacity_mw = None

            if resource in instance.CAPACITY_LIMITED_RESOURCES:
                capacity_limit_dual = instance.dual[instance.Capacity_Limit_Constraint[resource, period]] \
                    / instance.discount_factor[period]
            else:
                capacity_limit_dual = None

            if resource in instance.HYDROGEN_ELECTROLYSIS_RESOURCES:
                hydrogen_electrolysis_cap = instance.Operational_Capacity_MW[resource, period]()
            else:
                hydrogen_electrolysis_cap = None

            if resource in instance.HYDROGEN_ELECTROLYSIS_RESOURCES | instance.FLEXIBLE_LOAD_RESOURCES:
                planned_capacity = None
                operational_capacity = None
            else:
                planned_capacity = instance.planned_installed_capacity_mw[resource, period]
                operational_capacity = instance.Operational_Capacity_MW[resource, period]()

            if resource in instance.RESOURCES_WITH_MW_CAPACITY:
                operational_planned_capacity_mw = instance.Operational_Planned_Capacity_MW[resource, period]()
                fixed_o_and_m_cost = instance.Fixed_OM_Annual_In_Period_Dollars[resource, period]()
            else:
                operational_planned_capacity_mw = None
                fixed_o_and_m_cost = None

            if resource in instance.CAN_RETIRE_RESOURCES:
                retired_planned_capacity_mw = instance.Retire_Planned_Capacity_Cumulative_MW[resource, period]()
            else:
                retired_planned_capacity_mw = None

            if resource in instance.CAN_RETIRE_RESOURCES_NEW:
                retired_new_capacity_mw = instance.Retire_New_Capacity_In_Period_Cumulative_MW[resource, period]()
            else:
                retired_new_capacity_mw = None

            if resource in instance.FLEXIBLE_LOAD_RESOURCES:
                new_flex_load_capacity = instance.Build_Flexible_Load_Energy_Capacity_MWh[resource, period].value
                total_flexible_load_capacity = instance.Total_Daily_Flexible_Load_Potential_MWh[resource, period]()
            else:
                new_flex_load_capacity = None
                total_flexible_load_capacity = None

            if resource in instance.DISPATCHABLE_RESOURCES:
                unit_size = instance.unit_size_mw[instance.technology[resource]]
                operational_units = operational_capacity / unit_size
            else:
                unit_size = None
                operational_units = None

            build_writer.writerow([
                period,
                resource,
                instance.zone[resource],
                instance.contract[resource],
                instance.technology[resource],
                format_2f(planned_capacity),
                format_2f(build_capacity_mw),
                format_2f(cumulative_new_installed_capacity_mw),
                format_2f(operational_capacity),
                transmission_zone,
                format_2f(fully_deliverable_capacity_mw),
                format_2f(energy_only_capacity_mw),
                format_2f(new_flex_load_capacity),
                format_2f(total_flexible_load_capacity),
                format_2f(hydrogen_electrolysis_cap),
                format_2f(capacity_limit_dual),
                format_2f(unit_size),
                format_2f(operational_units),
                format_2f(capital_cost),
                format_2f(fixed_o_and_m_cost),
                instance.discount_factor[period],
                format_2f(operational_planned_capacity_mw),
                format_2f(retired_planned_capacity_mw),
                format_2f(operational_new_capacity_mw),
                format_2f(retired_new_capacity_mw),
                format_2f(min_cumulative_new_build_mw)
            ])


def export_storage_build_variables(instance, results_directory):
    """
    This file contains investment decisions made by RESOLVE in every period for the energy capacity
    of each storage resource. Blanks cells indicate that RESOLVE does not make a decision.
    :param instance:
    :param results_directory:
    :return:
    """
    storage_build_writer = fileio.csvwriter(os.path.join(results_directory, "storage_build.csv"))
    storage_build_writer.writerow([
        "period",
        "resource",
        "zone",
        "contract",
        "technology",
        "planned_energy_capacity_mwh",
        "new_build_mwh",
        "cumulative_new_build_mwh",
        "total_energy_capacity_mwh"
    ])

    for period in instance.PERIODS:
        for resource in instance.STORAGE_RESOURCES:
            if resource in instance.NEW_BUILD_STORAGE_RESOURCES:
                new_build = instance.Build_Storage_Energy_Capacity_MWh[resource, period].value
                cumulative_new_build = instance.Cumulative_New_Storage_Energy_Capacity_MWh[resource, period]()
            else:
                new_build = None
                cumulative_new_build = None

            storage_build_writer.writerow([
                period,
                resource,
                instance.zone[resource],
                instance.contract[resource],
                instance.technology[resource],
                format_2f(instance.planned_storage_energy_capacity_mwh[resource, period]),
                format_2f(new_build),
                format_2f(cumulative_new_build),
                format_2f(instance.Total_Storage_Energy_Capacity_MWh[resource, period]())
            ])


def export_hourly_operations(instance, results_directory):
    """
    This file contains the hourly operational decisions made by RESOLVE for each resource on all days modeled
    in RESOLVE (currently 37 days per year). Types of operational decisions included in this file are:
    unit commitment, power production, reserve commitment, and flexible load dispatch.
    Blanks cells indicate that RESOLVE does not make this decision.
    This file also contains the hourly operational cost of the decisions made by RESOLVE for each resource,
    including variable costs, fuel costs, start-up costs, and shut-down costs.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...operations...')

    operations_writer = fileio.csvwriter(os.path.join(results_directory, "operations.csv"))
    operations_writer.writerow([
        "resource",
        "zone",
        "contract",
        "technology",
        "period",
        "timepoint_id",
        "day",
        "hour_of_day",
        "day_weight",
        "power_mw",
        "scheduled_curtailment_mw",
        "upward_reg_mw",
        "downward_reg_mw",
        "upward_lf_reserve_mw",
        "downward_lf_reserve_mw",
        "spin_mw",
        "freq_response_total_mw",
        "freq_response_partial_mw",
        "committed_units",
        "committed_capacity_mw",
        "fully_operational_units",
        "start_units",
        "starting_units",
        "shut_down_units",
        "shutting_down_units",
        "storage_charging_mw",
        "ev_charging_mw",
        "energy_in_storage_mwh",
        "energy_in_ev_batteries_mwh",
        "total_daily_flexible_load_potential_mwh",
        "shift_load_down_mw",
        "shift_load_up_mw",
        "flexible_load_final_mw",
        "subhourly_dispatch_down_mw",
        "subhourly_dispatch_up_mw",
        "hydrogen_electrolysis_load_mw",
        "ee_ftm_load_reduction_mw",
        "variable_costs_$",
        "fuel_costs_$",
        "unit_start_costs_$",
        "unit_shutdown_costs_$",
        "curtailment_costs_$"
    ])

    for timepoint in instance.TIMEPOINTS:

        total_curtailable_energy = sum(
            instance.Provide_Power_MW[r, timepoint].value
            for r in instance.LOAD_FOLLOWING_ZONE_CURTAILABLE_RESOURCES)

        total_scheduled_curtailment = sum(
            instance.Scheduled_Curtailment_MW[r, timepoint].value
            for r in instance.LOAD_FOLLOWING_ZONE_CURTAILABLE_RESOURCES)

        for resource in instance.RESOURCES:

            if resource not in instance.LOAD_ONLY_RESOURCES | instance.EE_PROGRAMS | instance.FLEXIBLE_LOAD_RESOURCES:
                provide_power = instance.Provide_Power_MW[resource, timepoint].value
            else:
                provide_power = None

            if resource in instance.CURTAILABLE_VARIABLE_RESOURCES:
                scheduled_curtailment = instance.Scheduled_Curtailment_MW[resource, timepoint].value
                if resource not in instance.RPS_ELIGIBLE_RESOURCES:
                    curtailment_costs = scheduled_curtailment \
                        * instance.curtailment_cost_per_mwh[instance.zone[resource], instance.period[timepoint]]
                else:
                    curtailment_costs = None
            else:
                scheduled_curtailment = None
                curtailment_costs = None

            if resource in instance.THERMAL_RESOURCES:
                fuel_costs = instance.Fuel_Cost_Dollars_Per_Timepoint[resource, timepoint]()
            else:
                fuel_costs = None

            # Dispatchable resources have commitment variables
            if resource in instance.DISPATCHABLE_RESOURCES:
                committed_units = instance.Commit_Units[resource, timepoint].value
                committed_capacity_mw = instance.Commit_Capacity_MW[resource, timepoint]()
                start_units = instance.Start_Units[resource, timepoint].value
                unit_start_costs = instance.Start_Cost_In_Timepoint[resource, timepoint]()
                starting_units = instance.Starting_Units[resource, timepoint]()
                shut_down_units = instance.Shut_Down_Units[resource, timepoint].value
                shutting_down_units = instance.Shutting_Down_Units[resource, timepoint]()
                unit_shutdown_costs = instance.Shutdown_Cost_In_Timepoint[resource, timepoint]()

            else:
                committed_units = None
                committed_capacity_mw = None
                start_units = None
                unit_start_costs = None
                starting_units = None
                shut_down_units = None
                shutting_down_units = None
                unit_shutdown_costs = None

            if resource in instance.DISPATCHABLE_RAMP_LIMITED_RESOURCES:
                fully_operational_units = instance.Fully_Operational_Units[resource, timepoint]()
            else:
                fully_operational_units = None

            # Resources that provide regulation
            if resource in instance.REGULATION_RESERVE_RESOURCES:
                upward_reg = instance.Provide_Upward_Reg_MW[resource, timepoint].value
                downward_reg = instance.Provide_Downward_Reg_MW[resource, timepoint].value
            else:
                upward_reg = None
                downward_reg = None

            # Resources that provide load-following reserves
            if resource in instance.LOAD_FOLLOWING_RESERVE_RESOURCES:
                upward_lf_reserves = instance.Provide_LF_Upward_Reserve_MW[resource, timepoint].value
                downward_lf_reserves = instance.Provide_LF_Downward_Reserve_MW[resource, timepoint].value

            elif (resource in instance.LOAD_FOLLOWING_ZONE_CURTAILABLE_RESOURCES):
                if total_curtailable_energy > 0.0:
                    subhourly_resource_downward_dispatch = (
                        instance.Variable_Resource_Provide_Downward_LF_MW[timepoint].value *
                        instance.Provide_Power_MW[resource, timepoint].value /
                        total_curtailable_energy)

                    downward_lf_reserves = subhourly_resource_downward_dispatch
                else:
                    downward_lf_reserves = 0.0

                if total_scheduled_curtailment > 0.0:
                    subhourly_resource_upward_dispatch = (
                        instance.Variable_Resource_Provide_Upward_LF_MW[timepoint].value *
                        instance.Scheduled_Curtailment_MW[resource, timepoint].value /
                        total_scheduled_curtailment)

                    upward_lf_reserves = subhourly_resource_upward_dispatch
                else:
                    upward_lf_reserves = 0.0
            else:
                upward_lf_reserves = None
                downward_lf_reserves = None

            # Resources that provide spin
            if resource in instance.SPINNING_RESERVE_RESOURCES:
                spin_mw = instance.Provide_Spin_MW[resource, timepoint].value
            else:
                spin_mw = None

            if resource in instance.TOTAL_FREQ_RESP_RESOURCES:
                freq_response_total = instance.Provide_Frequency_Response_MW[resource, timepoint].value
            else:
                freq_response_total = None

            if resource in instance.PARTIAL_FREQ_RESP_RESOURCES:
                freq_response_partial = instance.Provide_Frequency_Response_MW[resource, timepoint].value
            else:
                freq_response_partial = None

            # Storage charging
            if resource in instance.STORAGE_RESOURCES:
                storage_charging = instance.Charge_Storage_MW[resource, timepoint].value
                energy_in_storage = instance.Energy_in_Storage_MWh[resource, timepoint].value
            else:
                storage_charging = None
                energy_in_storage = None

            # Subhourly dispatch
            # up = discharge, down = charge
            # renewable subhourly curtailment/dispatch is recorded elsewhere because it implemented as a fleet-wide
            # rather than a resource-specific dispatch

            if resource in instance.REGULATION_RESERVE_RESOURCES \
                    or resource in instance.LOAD_FOLLOWING_RESERVE_RESOURCES:
                subhourly_dispatch_down = 0.0
                subhourly_dispatch_up = 0.0
                if resource in instance.REGULATION_RESERVE_RESOURCES:
                    subhourly_dispatch_down += downward_reg * instance.reg_dispatch_fraction
                    subhourly_dispatch_up += upward_reg * instance.reg_dispatch_fraction
                if resource in instance.LOAD_FOLLOWING_RESERVE_RESOURCES:
                    subhourly_dispatch_down += downward_lf_reserves * instance.lf_reserve_dispatch_fraction
                    subhourly_dispatch_up += upward_lf_reserves * instance.lf_reserve_dispatch_fraction
            else:
                subhourly_dispatch_down = None
                subhourly_dispatch_up = None

            if resource in instance.HYDROGEN_ELECTROLYSIS_RESOURCES:
                hydrogen_electrolysis_load = instance.Hydrogen_Electrolysis_Load_MW[resource, timepoint].value
            else:
                hydrogen_electrolysis_load = None

            if resource in instance.EV_RESOURCES:
                ev_charging = instance.Charge_EV_Batteries_MW[resource, timepoint].value
                energy_in_ev_batteries = instance.Energy_in_EV_Batteries_MWh[resource, timepoint].value
            else:
                ev_charging = None
                energy_in_ev_batteries = None

            if resource in instance.EE_PROGRAMS:
                ee_load_reduction = instance.EE_Reduced_Load_FTM_MW[resource, timepoint]()
            else:
                ee_load_reduction = None

            if resource in instance.FLEXIBLE_LOAD_RESOURCES:
                daily_flex_load_potential = \
                    instance.Total_Daily_Flexible_Load_Potential_MWh[resource, instance.period[timepoint]]()
                shift_load_down = instance.Shift_Load_Down_MW[resource, timepoint].value
                shift_load_up = instance.Shift_Load_Up_MW[resource, timepoint].value
                flexible_load_final = shift_load_up - shift_load_down
            else:
                daily_flex_load_potential = None
                shift_load_down = None
                shift_load_up = None
                flexible_load_final = None

            operations_writer.writerow([
                resource,
                instance.zone[resource],
                instance.contract[resource],
                instance.technology[resource],
                instance.period[timepoint],
                timepoint,
                instance.day[timepoint],
                instance.hour_of_day[timepoint],
                instance.day_weight[instance.day[timepoint]],
                format_2f(provide_power),
                format_2f(scheduled_curtailment),
                format_2f(upward_reg),
                format_2f(downward_reg),
                format_2f(upward_lf_reserves),
                format_2f(downward_lf_reserves),
                format_2f(spin_mw),
                format_2f(freq_response_total),
                format_2f(freq_response_partial),
                format_6f(committed_units),
                format_2f(committed_capacity_mw),
                format_6f(fully_operational_units),
                format_6f(start_units),
                format_6f(starting_units),
                format_6f(shut_down_units),
                format_6f(shutting_down_units),
                format_2f(storage_charging),
                format_2f(ev_charging),
                format_2f(energy_in_storage),
                format_2f(energy_in_ev_batteries),
                format_2f(daily_flex_load_potential),
                format_2f(shift_load_down),
                format_2f(shift_load_up),
                format_2f(flexible_load_final),
                format_2f(subhourly_dispatch_down),
                format_2f(subhourly_dispatch_up),
                format_2f(hydrogen_electrolysis_load),
                format_2f(ee_load_reduction),
                format_2f(instance.Variable_Cost_In_Timepoint[resource, timepoint]()),
                format_2f(fuel_costs),
                format_2f(unit_start_costs),
                format_2f(unit_shutdown_costs),
                format_2f(curtailment_costs)
            ])


def export_transmission_flows(instance, results_directory):
    """
    This file contains the hourly transmission dispatch decisions made by RESOLVE for each transmission line,
    as well as the shadow price of flow limits on each line.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...transmit power...')

    tx_writer = fileio.csvwriter(os.path.join(results_directory, "transmit_power.csv"))
    tx_writer.writerow([
        "transmission_line",
        "transmission_from",
        "transmission_to",
        "period",
        "timepoint_id",
        "day",
        "hour_of_day",
        "day_weight",
        "unspecified_power_mw",
        "unspecified_power_positive_direction_mw",
        "unspecified_power_negative_direction_mw",
        "max_flow_dual_$",
        "min_flow_dual_$",
        "energy_cost_from_$_per_mwh",
        "energy_cost_to_$_per_mwh",
        "hurdle_cost_positive_direction_$",
        "hurdle_cost_negative_direction_$",
        "power_including_dedicated_imports_mw"
    ])

    for timepoint in instance.TIMEPOINTS:

        # discount_and_day_weight un-discounts the periods and un-weighs the days to obtain intuitive dual values.
        discount_and_day_weight = \
            instance.discount_factor[instance.period[timepoint]] * instance.day_weight[instance.day[timepoint]]

        for line in instance.TRANSMISSION_LINES:

            max_flow_dual = instance.dual[instance.Transmission_Max_Flow_Constraint[line, timepoint]] \
                / discount_and_day_weight
            min_flow_dual = instance.dual[instance.Transmission_Min_Flow_Constraint[line, timepoint]] \
                / discount_and_day_weight

            energy_cost_from = instance.dual[instance.Zonal_Power_Balance_Constraint[
                instance.transmission_from[line], timepoint]] / discount_and_day_weight
            energy_cost_to = instance.dual[instance.Zonal_Power_Balance_Constraint[
                instance.transmission_to[line], timepoint]] / discount_and_day_weight

            tx_writer.writerow([
                line,
                instance.transmission_from[line],
                instance.transmission_to[line],
                instance.period[timepoint],
                timepoint,
                instance.day[timepoint],
                instance.hour_of_day[timepoint],
                instance.day_weight[instance.day[timepoint]],
                format_2f(instance.Transmit_Power_Unspecified_MW[line, timepoint].value),
                format_2f(instance.Transmit_Power_Unspecified_Positive_Direction_MW[line, timepoint].value),
                format_2f(instance.Transmit_Power_Unspecified_Negative_Direction_MW[line, timepoint].value),
                format_2f(max_flow_dual),
                format_2f(min_flow_dual),
                format_2f(energy_cost_from),
                format_2f(energy_cost_to),
                format_2f(instance.Hurdle_Cost_Per_Timepoint_Positive_Direction[line, timepoint]()),
                format_2f(instance.Hurdle_Cost_Per_Timepoint_Negative_Direction[line, timepoint]()),
                format_2f(instance.Transmit_Power_MW[line, timepoint]())
            ])
        # Export transmission flows for semi storage zones when the feature is allowed
        if instance.allow_semi_storage_zones:
            for ssz in instance.SEMI_STORAGE_ZONES:
                line = "ssz_" + ssz
                max_flow_dual = instance.dual[instance.SSZ_Tx_Limit_Max_Constraint[ssz, timepoint]] \
                                / discount_and_day_weight
                min_flow_dual = instance.dual[instance.SSZ_Tx_Limit_Min_Constraint[ssz, timepoint]] \
                                / discount_and_day_weight
                energy_cost_from = instance.dual[instance.Zonal_Power_Balance_Constraint[
                    instance.ssz_from_zone[ssz], timepoint]] / discount_and_day_weight

                # Hurdle rate costs incurred by sending power along transmission lines

                hurdle_cost_positive_direction = instance.SSZ_Positive_Transmit_Power_MW[ssz, timepoint].value * \
                                                 instance.ssz_positive_direction_hurdle_rate_per_mw[
                                                     ssz, instance.period[timepoint]]
                hurdle_cost_negative_direction = instance.SSZ_Negative_Transmit_Power_MW[ssz, timepoint].value * \
                                                 instance.ssz_negative_direction_hurdle_rate_per_mw[
                                                     ssz, instance.period[timepoint]]

                tx_writer.writerow([
                    line,  # transmission line
                    instance.ssz_from_zone[ssz],  # transmission_from,
                    ssz,  # transmission_to
                    instance.period[timepoint],
                    timepoint,
                    instance.day[timepoint],
                    instance.hour_of_day[timepoint],
                    instance.day_weight[instance.day[timepoint]],
                    format_2f(instance.SSZ_Transmit_Power_MW[ssz, timepoint].value),
                    format_2f(instance.SSZ_Positive_Transmit_Power_MW[ssz, timepoint].value),  # positive_direction_mw
                    format_2f(instance.SSZ_Negative_Transmit_Power_MW[ssz, timepoint].value),  # negative_direction_mw
                    format_2f(max_flow_dual),
                    format_2f(min_flow_dual),
                    format_2f(energy_cost_from),
                    None,  # energy cost to
                    format_2f(hurdle_cost_positive_direction),
                    format_2f(hurdle_cost_negative_direction),
                    format_2f(instance.SSZ_Transmit_Power_MW[ssz, timepoint].value)
                ])


def simultaneous_transmission_flow_duals(instance, results_directory):
    """
    This file contains the hourly shadow prices of constraints that limit
    the sum of flows on groups of transmission lines.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...simultaneous transmission flow duals...')

    sim_flow_writer = fileio.csvwriter(os.path.join(results_directory, "sim_flow_group_duals.csv"))
    sim_flow_writer.writerow([
        "simultaneous_flow_group",
        "period",
        "timepoint_id",
        "day",
        "hour_of_day",
        "day_weight",
        "simultaneous_flow_group_dual_$"
    ])

    for timepoint in instance.TIMEPOINTS:

        # discount_and_day_weight un-discounts the periods and un-weighs the days to obtain intuitive dual values.
        discount_and_day_weight = \
            instance.discount_factor[instance.period[timepoint]] * instance.day_weight[instance.day[timepoint]]

        for sim_flow_group in instance.SIMULTANEOUS_FLOW_GROUPS:
            sim_flow_writer.writerow([
                sim_flow_group,
                instance.period[timepoint],
                timepoint,
                instance.day[timepoint],
                instance.hour_of_day[timepoint],
                instance.day_weight[instance.day[timepoint]],
                format_2f(instance.dual[instance.Simultaneous_Flows_Limit_Constraint[sim_flow_group, timepoint]]
                          / discount_and_day_weight)
            ])


def export_curtailment(instance, results_directory):
    """
    This file contains hourly and sub-hourly variable renewable curtailment decisions for each zone in RESOLVE.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...curtailment...')

    curtailment_writer = fileio.csvwriter(os.path.join(results_directory, "curtailment.csv"))
    curtailment_writer.writerow([
        "zone",
        "contract",
        "period",
        "timepoint_id",
        "day",
        "hour_of_day",
        "day_weight",
        "scheduled_curtailment_mw",
        "subhourly_downward_lf_mwh",
        "subhourly_upward_lf_mwh",
        "curtailment_cost_$"
    ])

    for timepoint in instance.TIMEPOINTS:

        for zone, contract in instance.ZONE_CONTRACT_COMBINATIONS:
            scheduled_curtailment = float()
            curtailment_cost = float()

            for resource in instance.CURTAILABLE_VARIABLE_RESOURCES:
                if zone == instance.zone[resource] and contract == instance.contract[resource]:
                    scheduled_curtailment += instance.Scheduled_Curtailment_MW[resource, timepoint].value
                    if resource not in instance.RPS_ELIGIBLE_RESOURCES:
                        curtailment_cost += scheduled_curtailment * \
                                            instance.curtailment_cost_per_mwh[zone, instance.period[timepoint]]

            # as a placeholder for specifying resource-specific subhourly curtailment
            # ascribe all subhourly curtailment to the first load following zone
            if zone == contract == instance.LOAD_FOLLOWING_ZONES[1]:
                subhourly_curtailment = instance.Subhourly_Downward_LF_Energy_MWh[timepoint]()
                subhourly_upward_lf_mwh = instance.Subhourly_Upward_LF_Energy_MWh[timepoint]()
            else:
                subhourly_curtailment = None
                subhourly_upward_lf_mwh = None

            curtailment_writer.writerow([
                zone,
                contract,
                instance.period[timepoint],
                timepoint,
                instance.day[timepoint],
                instance.hour_of_day[timepoint],
                instance.day_weight[instance.day[timepoint]],
                format_2f(scheduled_curtailment),
                format_2f(subhourly_curtailment),
                format_2f(subhourly_upward_lf_mwh),
                format_2f(curtailment_cost)
           ])


def export_planning_reserve_margin(instance, results_directory):
    """
    elcc_surface_facets.csv: This file contains results for each facet of the effective load carrying capability (ELCC)
    surface in each period. These results can show which (if any) of the ELCC facets is active in each period.

    planning_reserve_margin.csv: This file contains the input planning reserve margin (PRM) and local capacity targets
    in each period, as well as the shadow price of meeting those targets.
    A summary of PRM contributions by resource type is also included.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...planning reserve margin and ELCC surface...')

    # write headers for both output files
    prm_writer = fileio.csvwriter(os.path.join(results_directory, "planning_reserve_margin.csv"))
    prm_writer.writerow([
        "period",
        "prm_peak_load_MW",
        "planning_reserve_margin_fraction",
        "capacity_target_MW",
        "system_capacity_MW",
        "firm_capacity_MW",
        "prm_planned_import_capacity_MW",
        "prm_import_resource_capacity_adjustment_MW",
        "storage_ELCC_MW",
        "new_renewable_import_capacity_MW",
        "variable_renewable_ELCC_MW",
        "planning_reserve_margin_dual_$",
        "local_capacity_deficiency_MW",
        "local_capacity_dual_$",
        "marginal_solar_elcc_mw_per_fraction_of_annual_load",
        "marginal_wind_elcc_mw_per_fraction_of_annual_load",
        "active_elcc_facet_index",
        "prm_peak_load_MW_before_EE_MW"
    ])

    surface_writer = fileio.csvwriter(os.path.join(results_directory, "elcc_surface_facets.csv"))
    surface_writer.writerow([
        "period",
        "prm_peak_load_MW",
        "prm_annual_energy_MWh",
        "facet_index",
        "solar_coefficient",
        "solar_elcc_MW_per_fraction_of_annual_load",
        "solar_fraction_of_annual_load",
        "solar_elcc_MW",
        "wind_coefficient",
        "wind_elcc_MW_per_fraction_of_annual_load",
        "wind_fraction_of_annual_load",
        "wind_elcc_MW",
        "facet_intercept_MW",
        "facet_elcc_MW",
        "elcc_surface_facet_dual_$"
    ])

    for period in instance.PERIODS:

        # Calculate the energy from variable resources in each period that contributes to the elcc surfaces
        # such that the elcc implied by each facet of the surface can be calculated below
        solar_fraction_of_annual_load = 0.0
        wind_fraction_of_annual_load = 0.0

        for resource in instance.PRM_VARIABLE_RENEWABLE_RESOURCES:
            # existing renewable resources are assumed to be fully deliverable,
            # whereas a choice is made for new renewable resources whether to be energy only or fully deliverable
            if resource in instance.TX_DELIVERABILITY_RESOURCES:
                elcc_surface_capacity = instance.Fully_Deliverable_Installed_Capacity_MW[resource, period].value
            else:
                elcc_surface_capacity = instance.Operational_Capacity_MW[resource, period]()

            if instance.elcc_solar_bin[resource]:
                solar_fraction_of_annual_load += \
                    elcc_surface_capacity * instance.hours_per_year * instance.capacity_factor[resource] \
                    / instance.prm_annual_load_mwh[period]
            elif instance.elcc_wind_bin[resource]:
                wind_fraction_of_annual_load += \
                    elcc_surface_capacity * instance.hours_per_year * instance.capacity_factor[resource] \
                    / instance.prm_annual_load_mwh[period]

        # Reset values used to find the active ELCC facet and marginal ELCC values
        min_var_elcc_in_period_mw = None
        marginal_solar_elcc_mw_per_fraction_of_annual_load = None
        marginal_wind_elcc_mw_per_fraction_of_annual_load = None
        active_elcc_facet = None

        # Output facet-specific values for each period for variable renewable ELCC
        for facet in instance.ELCC_SURFACE_FACETS:

            solar_elcc_mw_per_fraction_of_annual_load = \
                instance.solar_coefficient[facet] * instance.prm_peak_load_mw[period]

            solar_elcc_mw = solar_elcc_mw_per_fraction_of_annual_load * solar_fraction_of_annual_load

            wind_elcc_mw_per_fraction_of_annual_load =\
                instance.wind_coefficient[facet] * instance.prm_peak_load_mw[period]

            wind_elcc_mw = wind_elcc_mw_per_fraction_of_annual_load * wind_fraction_of_annual_load

            intercept_elcc_mw = instance.facet_intercept[facet] * instance.prm_peak_load_mw[period]

            facet_elcc_mw = solar_elcc_mw + wind_elcc_mw + intercept_elcc_mw

            surface_writer.writerow([
                period,
                format_2f(instance.prm_peak_load_mw[period]),
                format_2f(instance.prm_annual_load_mwh[period]),
                facet,
                format_6f(instance.solar_coefficient[facet]),
                format_2f(solar_elcc_mw_per_fraction_of_annual_load),
                format_6f(solar_fraction_of_annual_load),
                format_2f(solar_elcc_mw),
                format_6f(instance.wind_coefficient[facet]),
                format_2f(wind_elcc_mw_per_fraction_of_annual_load),
                format_6f(wind_fraction_of_annual_load),
                format_2f(wind_elcc_mw),
                format_2f(intercept_elcc_mw),
                format_2f(facet_elcc_mw),
                format_2f(instance.dual[instance.ELCC_Surface_Constraint[period, facet]]
                          / instance.discount_factor[period])
            ])

            # Find the active ELCC facet - the one with the minimum ELCC value - and record marginal wind/solar ELCC
            # For each facets, test whether the ELCC of the facet is less than the one already recorded
            # note - the value of the variable ELCC_Variable_Renewables_MW can't be pulled directly
            # because when the PRM constraint isn't binding it can range between zero and the correct value
            if min_var_elcc_in_period_mw is None or min_var_elcc_in_period_mw > facet_elcc_mw:
                min_var_elcc_in_period_mw = facet_elcc_mw
                marginal_solar_elcc_mw_per_fraction_of_annual_load = solar_elcc_mw_per_fraction_of_annual_load
                marginal_wind_elcc_mw_per_fraction_of_annual_load = wind_elcc_mw_per_fraction_of_annual_load
                active_elcc_facet = facet

        # Sum the capacity of firm capacity resources in the PRM
        firm_capacity_mw = 0.0
        for resource in instance.PRM_FIRM_CAPACITY_RESOURCES:
            firm_capacity_mw += instance.Operational_NQC_MW[resource, period]()

        # Sum the capacity of storage resources in the PRM
        # which is limited by either the storage duration or the installed capacity, depending on the param elcc_hours
        # note - the value of the variable ELCC_Storage_MW can't be pulled directly
        # because when the PRM constraint isn't binding it can range between zero and the correct value
        storage_elcc_mw = 0.0
        for resource in instance.PRM_STORAGE_RESOURCES:
            storage_elcc_mw += (
                instance.net_qualifying_capacity_fraction[resource] *
                min(instance.Operational_Capacity_MW[resource, period](),
                    instance.Total_Storage_Energy_Capacity_MWh[resource, period]() / instance.elcc_hours)
            )

        new_renewable_import_capacity = 0.0
        for resource in instance.TX_DELIVERABILITY_RESOURCES:
            if instance.import_on_new_tx[resource]:
                new_renewable_import_capacity += \
                    instance.Fully_Deliverable_Installed_Capacity_MW[resource, period].value\
                    * instance.tx_import_capacity_fraction[resource]

        planned_import_capacity = 0.0
        if instance.allow_unspecified_import_contribution[period]:
            planned_import_capacity = instance.prm_planned_import_capacity_mw[period]
        else:
            planned_import_capacity = (instance.PRM_Available_Planned_Import_MW[period]() -
                                       instance.prm_import_resource_capacity_adjustment_mw[period])

        # print out planning reserve margin results for each period.
        prm_writer.writerow([
            period,
            format_2f(instance.PRM_Peak_Load_MW[period]()),
            instance.planning_reserve_margin[period],
            format_2f(instance.PRM_Peak_Load_MW[period]() * (1 + instance.planning_reserve_margin[period])),
            format_2f(firm_capacity_mw
                      + storage_elcc_mw
                      + new_renewable_import_capacity
                      + min_var_elcc_in_period_mw
                      + instance.prm_planned_import_capacity_mw[period]
                      + instance.prm_import_resource_capacity_adjustment_mw[period]),
            format_2f(firm_capacity_mw),
            format_2f(planned_import_capacity),
            format_2f(instance.prm_import_resource_capacity_adjustment_mw[period]),
            format_2f(storage_elcc_mw),
            format_2f(new_renewable_import_capacity),
            format_2f(min_var_elcc_in_period_mw),
            format_2f(instance.dual[instance.Planning_Reserve_Margin_Constraint[period]]
                      / instance.discount_factor[period]),
            format_2f(instance.local_capacity_deficiency_mw[period]),
            format_2f(instance.dual[instance.Local_Capacity_Deficiency_Constraint[period]]
                      / instance.discount_factor[period]),
            format_2f(marginal_solar_elcc_mw_per_fraction_of_annual_load),
            format_2f(marginal_wind_elcc_mw_per_fraction_of_annual_load),
            active_elcc_facet,
            format_2f(instance.prm_peak_load_mw[period])
        ])


def export_energy_sufficiency(instance, results_directory):
    """Export contribution to energy sufficiency constraint by resource category."""
    print('...energy sufficiency...')

    # write headers for both output files
    energy_sufficiency_writer = fileio.csvwriter(os.path.join(results_directory, "energy_sufficiency.csv"))
    energy_sufficiency_writer.writerow([
        "period",
        "sufficiency_horizon",
        "horizon_id",
        "energy_sufficiency_average_load_aMW",
        "Total_Resources_aMW",
        "energy_sufficiency_dual_$",
        "Firm_Capacity_aMW",
        "Hydro_aMW",
        "Storage_aMW",
        "PRM_Variable_Renewables_aMW",
        "New_Import_Renewables_aMW",
        "Available_Planned_Import_aMW",
        "Energy_Efficiency_aMW",
        "Conventional_DR_aMW"
    ])

    for period in instance.PERIODS:
        for sufficiency_horizon_group in instance.ENERGY_SUFFICIENCY_HORIZON_GROUPS:

            sufficiency_horizon = sufficiency_horizon_group[0]
            horizon_id = sufficiency_horizon_group[1]

            if instance.allow_ee_investment:
                ee_contribution = instance.Energy_Sufficiency_EE_aMW[sufficiency_horizon, horizon_id, period]()
            else:
                ee_contribution = None

            # When the energy sufficiency constraint isn't binding, Energy_Sufficiency_Storage_Contribution_aMW can range between 0 and the actual value.
            # The logic below adds up the contribution of each storage resource.
            storage_contribution = float()
            for resource in instance.PRM_STORAGE_RESOURCES:
                storage_contribution += min(instance.Operational_Capacity_MW[resource, period](),
                                            instance.Energy_Sufficiency_Storage_Energy_Bound_aMW[resource, sufficiency_horizon, period]())

            # subtract Energy_Sufficiency_Storage_Contribution_aMW storage from the total because it might be less than the full contribution
            # then add the calculated storage values back.
            total_resources = instance.Energy_Sufficiency_Total_Resources_aMW[sufficiency_horizon, horizon_id, period]() \
                              - instance.Energy_Sufficiency_Storage_Contribution_aMW[sufficiency_horizon, period]() \
                              + storage_contribution

            energy_sufficiency_writer.writerow([
                period,
                sufficiency_horizon,
                horizon_id,
                format_2f(instance.energy_sufficiency_average_load_aMW[sufficiency_horizon, horizon_id, period]),
                format_2f(total_resources),
                format_2f(instance.dual[instance.Energy_Sufficiency_Constraint[sufficiency_horizon, horizon_id, period]] /
                          instance.discount_factor[period]),
                format_2f(instance.Energy_Sufficiency_Firm_Capacity_aMW[period]()),
                format_2f(instance.Energy_Sufficiency_Hydro_aMW[sufficiency_horizon, horizon_id, period]()),
                format_2f(storage_contribution),
                format_2f(instance.Energy_Sufficiency_Variable_Renewables_aMW[sufficiency_horizon, horizon_id, period]()),
                format_2f(instance.Energy_Sufficiency_Import_Renewables_aMW[sufficiency_horizon, horizon_id, period]()),
                format_2f(instance.Energy_Sufficiency_Available_Planned_Import_aMW[sufficiency_horizon, horizon_id, period]()),
                format_2f(ee_contribution),
                format_2f(instance.Energy_Sufficiency_Total_Conventional_DR_aMW[sufficiency_horizon, period]())
            ])


def export_local_capacity_resources(instance, results_directory):
    """
    This file contains the local capacity investment decisions made by RESOLVE
    for each local capacity resource in each period.
    :param instance:
    :param results_directory:
    :return:
    """

    local_capacity_writer = fileio.csvwriter(os.path.join(results_directory, "local_capacity_resources.csv"))
    local_capacity_writer.writerow([
        "resource",
        "period",
        "local_new_capacity_MW",
        "local_new_capacity_NQC_MW",
        "local_capacity_limit_MW",
        "local_capacity_limit_dual_$",
        "storage_local_energy_capacity_MWh"
    ])

    for resource in instance.LOCAL_CAPACITY_RESOURCES:

        for period in instance.PERIODS:

            # calculate nqc
            if resource in instance.PRM_FIRM_CAPACITY_RESOURCES:
                local_capacity_nqc_mw = instance.Local_New_Capacity_MW[resource, period].value \
                    * instance.net_qualifying_capacity_fraction[resource]
            elif resource in instance.PRM_VARIABLE_RENEWABLE_RESOURCES:
                local_capacity_nqc_mw = instance.Local_New_Capacity_MW[resource, period].value \
                    * instance.local_variable_renewable_nqc_fraction[resource]
            elif resource in instance.LOCAL_CAPACITY_STORAGE_RESOURCES:
                local_capacity_nqc_mw = instance.Local_New_Capacity_MW[resource, period].value
            elif resource in instance.PRM_EE_PROGRAMS:
                local_capacity_nqc_mw = instance.Local_New_Capacity_MW[resource, period].value \
                                        * (1 + instance.ee_t_and_d_losses_fraction[resource])
            else:
                local_capacity_nqc_mw = None

            # resources that have a local capacity limit
            if resource in instance.LOCAL_CAPACITY_LIMITED_RESOURCES:
                capacity_limit_local_mw = instance.capacity_limit_local_mw[resource, period]
                capacity_limit_local_dual = instance.dual[instance.Local_Capacity_Limit_Constraint[resource, period]] \
                    / instance.discount_factor[period]
            else:
                capacity_limit_local_mw = None
                capacity_limit_local_dual = None

            # local storage resources
            if resource in instance.LOCAL_CAPACITY_STORAGE_RESOURCES:
                storage_local_energy_capacity_mwh = \
                    instance.Local_New_Storage_Energy_Capacity_MWh[resource, period].value
            else:
                storage_local_energy_capacity_mwh = None

            local_capacity_writer.writerow([
                resource,
                period,
                format_2f(instance.Local_New_Capacity_MW[resource, period].value),
                format_2f(local_capacity_nqc_mw),
                format_2f(capacity_limit_local_mw),
                format_2f(capacity_limit_local_dual),
                format_2f(storage_local_energy_capacity_mwh)
            ])


def export_rps(instance, results_directory):
    """
    This file contains the input RPS target level in each period, as well as the shadow price of the RPS constraint,
    the RPS credits banked, and a high-level summary of the components of the RPS constraint.
    Also includes information on pipeline biogas use and costs.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...RPS...')

    rps_writer = fileio.csvwriter(os.path.join(results_directory, "rps.csv"))
    rps_writer.writerow([
        "zone",
        "period",
        "rps_eligible_gen_mwh",
        "scheduled_curtailment_mwh",
        "Subhourly_Downward_LF_Energy_MWh",
        "rps_storage_losses_mwh",
        "rps_target_mwh",
        "rps_banked_mwh",
        "rps_constraint_dual_$",
        "rps_nonmodeled_mwh",
        "rps_net_bank_spent_mwh",
        "rps_previously_banked_mwh",
        "pipeline_biogas_generation_mwh",
        "pipeline_biogas_cost_$_per_year",
        "pipeline_biogas_max_dual_$_per_mmbtu",
        "rps_unbundled_fraction_limit_dual_$_per_mwh",
        "rps_target_before_ee_mwh"
    ])

    for period in instance.PERIODS:

        if instance.optimize_rps_banking:
            rps_banked_mwh = instance.Bank_RPS_MWh[period].value
            rps_net_bank_spent_mwh = \
                instance.Previously_Banked_RPS_MWh[period]() - instance.Bank_RPS_MWh[period].value
        else:
            rps_banked_mwh = None
            rps_net_bank_spent_mwh = instance.rps_bank_planned_spend_mwh[period]

        if instance.enforce_unbundled_fraction_limit[period]:
            unbundled_dual = instance.dual[instance.RPS_Unbundled_Fraction_Limit_Constraint[period]] \
                             / instance.discount_factor[period]
        else:
            unbundled_dual = None

        # the RPS target could include one or many zones - concat the names of the zones here
        rps_zone_name = '_'.join(map(str, instance.RPS_ZONES))

        rps_writer.writerow([
            rps_zone_name,
            period,
            format_2f(instance.RPS_Eligible_Generation_MWh_Per_Year[period]()),
            format_2f(instance.Scheduled_RPS_Curtailment_Per_Year[period]()),
            format_2f(instance.Subhourly_RPS_Curtailment_Per_Year[period]()),
            format_2f(instance.RPS_Storage_Losses_MWh_Per_Year[period]()),
            format_2f(instance.RPS_Target_MWh[period]()),
            format_2f(rps_banked_mwh),
            format_2f(instance.dual[instance.Achieve_RPS_Constraint[period]] / instance.discount_factor[period]),
            format_2f(instance.rps_nonmodeled_mwh[period]),
            format_2f(rps_net_bank_spent_mwh),
            format_2f(instance.Previously_Banked_RPS_MWh[period]()),
            format_2f(instance.RPS_Pipeline_Biogas_Generation_MWh_Per_Year[period]()),
            format_2f(instance.Pipeline_Biogas_Consumption_MMBtu_Per_Year[period]()
                * instance.incremental_pipeline_biogas_cost_per_mmbtu[period]),
            format_2f(instance.dual[instance.Maximum_Pipeline_Biogas_Potential_Constraint[period]]
                / instance.discount_factor[period]),
            format_2f(unbundled_dual),
            format_2f(instance.rps_fraction_of_retail_sales[period] * instance.retail_sales_mwh[period])
        ])


def export_ghg(instance, results_directory):
    """
    This file contains the input GHG emissions target in each period, and the shadow price of meeting that target.
    Blanks cells indicate that a GHG emissions target was not modeled.
    :param instance:
    :param results_directory:
    :return:
    """

    ghg_writer = fileio.csvwriter(os.path.join(results_directory, "ghg.csv"))
    ghg_writer.writerow([
        "period",
        "ghg_target_tco2_per_yr",
        "ghg_emissions_credit_tco2_per_yr",
        "ghg_constraint_dual_$",
        "ghg_unspecified_imports_tco2_per_yr",
        "ghg_emissions_within_area_tco2_per_yr"
    ])

    for period in instance.PERIODS:

        if instance.enforce_ghg_targets:
            ghg_target = instance.ghg_emissions_target_tco2_per_year[period]
            ghg_credit = instance.ghg_emissions_credit_tco2_per_year[period]
            ghg_constraint_dual = instance.dual[instance.GHG_Target_Constraint[period]]\
                                  / instance.discount_factor[period]
        else:
            ghg_target = None
            ghg_credit = None
            ghg_constraint_dual = None

        ghg_writer.writerow([
            period,
            format_2f(ghg_target),
            format_2f(ghg_credit),
            format_2f(ghg_constraint_dual),
            format_2f(instance.GHG_Unspecified_Imports_tCO2_Per_Year[period]()),
            format_2f(instance.GHG_Resource_Emissions_tCO2_Per_Year[period]())
        ])


def export_transmission_costs(instance, results_directory):
    """
    This file contains the cost of building new transmission in each period triggered by
    new renewable resource investment decisions made by RESOLVE.
    Also included is the breakdown of fully deliverable/energy only capacity in each transmission zone in each period.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...transmission costs by period')

    transmission_costs_writer = fileio.csvwriter(os.path.join(results_directory, "transmission_costs.csv"))
    transmission_costs_writer.writerow([
        "period",
        "tx_zone",
        "transmission_cost_$",
        "period_discount_factor",
        "new_transmission_capacity_mw",
        "fully_deliverable_new_tx_threshold_mw",
        "fully_deliverable_installed_capacity_mw",
        "energy_only_tx_limit_mw",
        "energy_only_installed_capacity_mw",
        "energy_only_limit_dual_$"
    ])

    for period in instance.PERIODS:
        for tx_zone in instance.TX_ZONES:

            fully_deliverable_capacity = float()
            energy_only_capacity = float()
            for resource in instance.TX_DELIVERABILITY_RESOURCES:
                if instance.tx_zone_of_resource[resource] == tx_zone:
                    fully_deliverable_capacity += \
                        instance.Fully_Deliverable_Installed_Capacity_MW[resource, period].value
                    energy_only_capacity += instance.Energy_Only_Installed_Capacity_MW[resource, period].value

            transmission_costs_writer.writerow([
                period,
                tx_zone,
                format_2f(instance.New_Transmission_Capacity_MW[tx_zone, period].value
                          * instance.tx_deliverability_cost_per_mw_yr[tx_zone]),
                instance.discount_factor[period],
                format_2f(instance.New_Transmission_Capacity_MW[tx_zone, period].value),
                format_2f(instance.fully_deliverable_new_tx_threshold_mw[tx_zone]),
                format_2f(fully_deliverable_capacity),
                format_2f(instance.energy_only_tx_limit_mw[tx_zone]),
                format_2f(energy_only_capacity),
                format_2f(instance.dual[instance.Energy_Only_TX_Zone_Limit_Constraint[tx_zone, period]]
                          / instance.discount_factor[period])
            ])

def export_transmission_build(instance, results_directory):
    """Export period transmission build for new transmission lines."""

    print("...transmission build...")

    tx_build_writer = fileio.csvwriter(os.path.join(results_directory, "transmission_build.csv"))
    tx_build_writer.writerow(["line",
                              "period",
                              "period_build_mw",
                              "total_build_mw",
                              "local_capacity_contribution_mw",
                              "build_cost_per_yr"])

    for line in instance.TRANSMISSION_LINES_NEW:
        for period in instance.PERIODS:
            transmission_build_costs = float()
            for (pp, v) in instance.PERIOD_VINTAGES:
                if pp == period:
                    transmission_build_costs += instance.New_Tx_Period_Vintage_Build_Cost[line, pp, v]()

            tx_build_writer.writerow([
                line,
                period,
                format_2f(instance.New_Tx_Period_Installed_Capacity_MW[line, period].value),
                format_2f(instance.New_Tx_Total_Installed_Capacity_MW[line, period]()),
                format_2f(instance.New_Tx_Local_Capacity_Contribution_MW[line, period]()),
                format_2f(transmission_build_costs)
            ])


def export_fuel_burn(instance, results_directory):
    """
    This file contains the hourly fuel burn and greenhouse gas (GHG) emissions by resource.
    :param instance:
    :param results_directory:
    :return:
    """

    print('...fuel burn and CO2 by resource...')

    fuel_burn_writer = fileio.csvwriter(os.path.join(results_directory, "fuel_burn_by_resource.csv"))
    fuel_burn_writer.writerow([
        "resource",
        "zone",
        "contract",
        "technology",
        "fuel",
        "timepoint",
        "period",
        "day",
        "hour_of_day",
        "day_weight",
        "fuel_burn_mmbtu",
        "emissions_tco2",
        "pipeline_biogas_mmbtu",
        "start_fuel_mmbtu"
    ])

    for r in instance.THERMAL_RESOURCES:
        for tmp in instance.TIMEPOINTS:

            if r in instance.PIPELINE_BIOGAS_RESOURCES:
                biogas_consumption = instance.Pipeline_Biogas_Consumption_MMBtu[r, tmp].value
            else:
                biogas_consumption = None

            if r in instance.DISPATCHABLE_RESOURCES:
                start_fuel = format_2f(instance.Start_Fuel_MMBtu_In_Timepoint[r, tmp]())
            else:
                start_fuel = None

            fuel_burn_writer.writerow([
                r,
                instance.zone[r],
                instance.contract[r],
                instance.technology[r],
                instance.fuel[instance.technology[r]],
                tmp,
                instance.period[tmp],
                instance.day[tmp],
                instance.hour_of_day[tmp],
                instance.day_weight[instance.day[tmp]],
                format_2f(instance.Fuel_Consumption_MMBtu[r, tmp]()),
                format_2f(instance.GHG_Resource_Emissions_tCO2_Per_Timepoint[r, tmp]()),
                format_2f(biogas_consumption),
                start_fuel
            ])


def export_ghg_imports(instance, results_directory):
    """
    This file contains the hourly GHG emissions imported into the ghg target area along transmission lines.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...ghg imports...')
    ghg_imports_writer = fileio.csvwriter(os.path.join(results_directory, "ghg_imports.csv"))
    ghg_imports_writer.writerow([
        "line",
        "timepoint",
        "period",
        "day",
        "hour_of_day",
        "day_weight",
        "positive_direction_ghg_import_tco2",
        "negative_direction_ghg_import_tco2"
    ])

    # GHG imports are recorded even if a cap on emissions isn't enforced
    # as long as TRANSMISSION_LINES_GHG_TARGET is defined
    for line in instance.TRANSMISSION_LINES_GHG_TARGET:
        for tmp in instance.TIMEPOINTS:
            ghg_imports_writer.writerow([
                line,
                tmp,
                instance.period[tmp],
                instance.day[tmp],
                instance.hour_of_day[tmp],
                instance.day_weight[instance.day[tmp]],
                format_2f(instance.GHG_Unspecified_Imports_tCO2_Per_Timepoint_Positive_Direction[line, tmp]()),
                format_2f(instance.GHG_Unspecified_Imports_tCO2_Per_Timepoint_Negative_Direction[line, tmp]())
            ])


def export_reserve_timepoints(instance, results_directory):
    """
    This file contains the hourly shadow prices of meeting reserve and reliability constraints.
    Exports the undiscounted duals for easier comparison, but the original/objective function dual can be obtained
    by multiplying the undiscounted dual by period_discount_factor.
    Also contains the unmet reserve violations in (MW).
    :param instance:
    :param results_directory:
    :return:
    """
    print('...reserve timepoint duals and violations...')
    reserve_timepoint_duals_violations_writer = \
        fileio.csvwriter(os.path.join(results_directory, "reserve_timepoints.csv"))
    reserve_timepoint_duals_violations_writer.writerow([
        "timepoint",
        "period",
        "day",
        "hour_of_day",
        "day_weight",
        "period_discount_factor",
        "min_gen_req",
        "spin_req",
        "upward_lf_req",
        "downward_lf_req",
        "upward_reg_req",
        "downward_reg_req",
        "min_local_gen_dual_$",
        "total_fr_dual_$",
        "partial_fr_dual_$",
        "spin_dual_$",
        "upward_lf_dual_$",
        "upward_reg_dual_$",
        "downward_reg_dual_$",
        "max_downward_lf_dual_$",
        "var_renw_down_lf_limit_dual_$",
        "var_renw_down_lf_availability_dual_$",
        "max_variable_upward_lf_dual_$",
        "available_variable_upward_lf_dual_$",
        "upward_reg_violation_mw",
        "downward_reg_violation_mw",
        "upward_lf_reserve_violation_mw",
        "downward_lf_reserve_violation_mw",
        "spin_violation_mw"
    ])

    meet_spin = instance.Meet_Spin_Requirement_Constraint
    meet_upward_lf = instance.Meet_Upward_LF_Requirement_Constraint
    meet_upward_reg = instance.Meet_Upward_Reg_Requirement_Constraint
    meet_downward_reg = instance.Meet_Downward_Reg_Requirement_Constraint
    max_downward_lf_provision = instance.Meet_Downward_LF_Requirement_Constraint
    var_renw_down_lf_limit = instance.Var_Renw_Down_LF_Reserve_Limit_Constraint
    var_renw_down_lf_availability = instance.Var_Renw_Down_LF_Reserve_Availability_Constraint
    available_variable_upward_lf = instance.Variable_Resource_Available_Upward_LF_Constraint
    max_variable_upward_lf = instance.Max_Upward_LF_From_Variable_Resources_Constraint

    for timepoint in instance.TIMEPOINTS:

        # discount_and_day_weight un-discounts the periods and un-weighs the days to obtain intuitive dual values.
        discount_and_day_weight = \
            instance.discount_factor[instance.period[timepoint]] * instance.day_weight[instance.day[timepoint]]

        if instance.min_gen_committed_mw[timepoint] != 0:
            min_local_gen_dual = instance.dual[instance.Min_Local_Gen_Constraint[timepoint]] \
                / discount_and_day_weight
        else:
            min_local_gen_dual = None

        if instance.freq_resp_total_req_mw[timepoint] != 0:
            total_fr_dual = instance.dual[instance.Total_Frequency_Response_Headroom_Constraint[timepoint]] \
                / discount_and_day_weight
        else:
            total_fr_dual = None

        if instance.freq_resp_partial_req_mw[timepoint] != 0:
            partial_fr_dual = \
                instance.dual[instance.Partial_Frequency_Response_Headroom_Constraint[timepoint]] \
                / discount_and_day_weight
        else:
            partial_fr_dual = None

        reserve_timepoint_duals_violations_writer.writerow([
            timepoint,
            instance.period[timepoint],
            instance.day[timepoint],
            instance.hour_of_day[timepoint],
            instance.day_weight[instance.day[timepoint]],
            instance.discount_factor[instance.period[timepoint]],
            format_2f(instance.min_gen_committed_mw[timepoint]),
            format_2f(instance.Spinning_Reserve_Req_MW[timepoint]()),
            format_2f(instance.Upward_Load_Following_Reserve_Req[timepoint]()),
            format_2f(instance.Downward_Load_Following_Reserve_Req[timepoint]()),
            format_2f(instance.upward_reg_req[timepoint]),
            format_2f(instance.downward_reg_req[timepoint]),
            format_2f(min_local_gen_dual),
            format_2f(total_fr_dual),
            format_2f(partial_fr_dual),
            format_2f(instance.dual[meet_spin[timepoint]] / discount_and_day_weight),
            format_2f(instance.dual[meet_upward_lf[timepoint]] / discount_and_day_weight),
            format_2f(instance.dual[meet_upward_reg[timepoint]] / discount_and_day_weight),
            format_2f(instance.dual[meet_downward_reg[timepoint]] / discount_and_day_weight),
            format_2f(instance.dual[max_downward_lf_provision[timepoint]] / discount_and_day_weight),
            format_2f(instance.dual[var_renw_down_lf_limit[timepoint]] / discount_and_day_weight),
            format_2f(instance.dual[var_renw_down_lf_availability[timepoint]] / discount_and_day_weight),
            format_2f(instance.dual[max_variable_upward_lf[timepoint]] / discount_and_day_weight),
            format_2f(instance.dual[available_variable_upward_lf[timepoint]] / discount_and_day_weight),
            format_2f(instance.Upward_Reg_Violation_MW[timepoint].value),
            format_2f(instance.Downward_Reg_Violation_MW[timepoint].value),
            format_2f(instance.Upward_LF_Reserve_Violation_MW[timepoint].value),
            format_2f(instance.Downward_LF_Reserve_Violation_MW[timepoint].value),
            format_2f(instance.Spin_Violation_MW[timepoint].value)
        ])


def export_ramping_duals_by_timepoint(instance, results_directory):
    """
    This file contains the hourly values relating to ramp constrains of dispatchable thermal generation.
    Note: this currently doesn't export reserve ramp constraints if the resource
    isn't in DISPATCHABLE_RAMP_LIMITED_RESOURCES, which is possible if
    ramp_rate_fraction is >= 1 but is less than the unit's operable range on the reserve timeframe.
    :param instance:
    :param results_directory:
    :return:
    """
    print('...ramping variables by timepoint...')

    ramp_writer = fileio.csvwriter(os.path.join(results_directory, "ramping_duals.csv"))
    ramp_writer.writerow([
        "resource",
        "technology",
        "zone",
        "timepoint",
        "period",
        "day",
        "hour_of_day",
        "day_weight",
        "period_discount_factor",
        "commit_units",
        "start_units",
        "shut_down_units",
        "fully_operational_units",
        "power_MW",
        "max_rampup_MW",
        "max_rampdown_MW",
        "rampup_dual_$",
        "rampdown_dual_$",
        "max_reserve_ramp_up_MW",
        "max_reserve_ramp_down_MW",
        "reserve_ramp_up_dual_$",
        "reserve_ramp_down_dual_$",
        "min_gen_MW",
        "min_gen_dual_$",
        "max_gen_MW",
        "max_gen_dual_$"
    ])

    for r in instance.DISPATCHABLE_RAMP_LIMITED_RESOURCES:
        for tmp in instance.TIMEPOINTS:
            discount_and_day_weight = \
                instance.discount_factor[instance.period[tmp]] * instance.day_weight[instance.day[tmp]]

            # ramp constraints between timesteps ######################
            if instance.ramp_rate_fraction[instance.technology[r]] \
                    >= (1 - instance.min_stable_level_fraction[instance.technology[r]]):
                rampup_dual = None
                rampdown_dual = None
                max_rampup_mw = None
                max_rampdown_mw = None
            else:
                rampup_dual = instance.dual[instance.Dispatchable_Resource_Ramp_Up_Constraint[r, tmp]] \
                    / discount_and_day_weight
                rampdown_dual = instance.dual[instance.Dispatchable_Resource_Ramp_Down_Constraint[r, tmp]] \
                    / discount_and_day_weight
                max_rampup_mw = (instance.Commit_Units[r, tmp].value - instance.Start_Units[r, tmp].value) \
                    * instance.unit_size_mw[instance.technology[r]] \
                    * instance.ramp_rate_fraction[instance.technology[r]] \
                    + instance.Start_Units[r, tmp].value \
                    * instance.unit_size_mw[instance.technology[r]] \
                    * instance.min_stable_level_fraction[instance.technology[r]] \
                    + instance.Start_Units[r, tmp].value * instance.ramp_relax
                max_rampdown_mw = (instance.Commit_Units[r, tmp].value - instance.Start_Units[r, tmp].value) \
                    * instance.unit_size_mw[instance.technology[r]] \
                    * instance.ramp_rate_fraction[instance.technology[r]] \
                    + instance.Shut_Down_Units[r, tmp].value \
                    * instance.unit_size_mw[instance.technology[r]] \
                    * instance.min_stable_level_fraction[instance.technology[r]] \
                    + instance.Shut_Down_Units[r, tmp].value * instance.ramp_relax

            # reserve ramp constraints ######################
            if (r not in instance.REGULATION_RESERVE_RESOURCES
                    and r not in instance.LOAD_FOLLOWING_RESERVE_RESOURCES
                    and r not in instance.SPINNING_RESERVE_RESOURCES):
                max_reserve_ramp_up_mw = None
                max_reserve_ramp_down_mw = None
                reserve_ramp_up_dual = None
                reserve_ramp_down_dual = None
            elif instance.reserve_timeframe_fraction_of_hour * instance.ramp_rate_fraction[instance.technology[r]] >= \
                    (1 - instance.min_stable_level_fraction[instance.technology[r]]):
                max_reserve_ramp_up_mw = None
                max_reserve_ramp_down_mw = None
                reserve_ramp_up_dual = None
                reserve_ramp_down_dual = None
            else:
                if r in instance.DISPATCHABLE_RAMP_LIMITED_RESOURCES:
                    reserve_capable_units = instance.Fully_Operational_Units[r, tmp]()
                else:
                    reserve_capable_units = instance.Commit_Units[r, tmp].value

                max_reserve_ramp_up_mw = reserve_capable_units \
                    * instance.unit_size_mw[instance.technology[r]] \
                    * instance.ramp_rate_fraction[instance.technology[r]] \
                    * instance.reserve_timeframe_fraction_of_hour
                max_reserve_ramp_down_mw = reserve_capable_units \
                    * instance.unit_size_mw[instance.technology[r]] \
                    * instance.ramp_rate_fraction[instance.technology[r]] \
                    * instance.reserve_timeframe_fraction_of_hour
                reserve_ramp_up_dual = instance.dual[instance.Dispatchable_Upward_Reserve_Ramp_Constraint[r, tmp]] \
                    / discount_and_day_weight
                reserve_ramp_down_dual = instance.dual[instance.Dispatchable_Downward_Reserve_Ramp_Constraint[r, tmp]] \
                    / discount_and_day_weight

            # min gen ######################
            min_gen = instance.Commit_Capacity_MW[r, tmp]() \
                * instance.min_stable_level_fraction[instance.technology[r]] \
                - (instance.Commit_Units[r, tmp].value - instance.Fully_Operational_Units[r, tmp]()) \
                * instance.ramp_relax

            min_gen_dual = instance.dual[instance.Thermal_Min_Gen_Down_Reserve_Constraint[r, tmp]] \
                / discount_and_day_weight

            # max_gen ######################
            max_gen = (instance.Commit_Units[r, tmp].value - instance.Fully_Operational_Units[r, tmp]()) \
                * instance.unit_size_mw[instance.technology[r]] \
                * instance.min_stable_level_fraction[instance.technology[r]] \
                + instance.Fully_Operational_Units[r, tmp]() \
                * instance.unit_size_mw[instance.technology[r]] \

            max_gen_dual = instance.dual[instance.Dispatchable_Max_Gen_Up_Reserve_Constraint[r, tmp]] \
                / discount_and_day_weight

            ramp_writer.writerow([
                r,
                instance.technology[r],
                instance.zone[r],
                tmp,
                instance.period[tmp],
                instance.day[tmp],
                instance.hour_of_day[tmp],
                instance.day_weight[instance.day[tmp]],
                instance.discount_factor[instance.period[tmp]],
                format_6f(instance.Commit_Units[r, tmp].value),
                format_6f(instance.Start_Units[r, tmp].value),
                format_6f(instance.Shut_Down_Units[r, tmp].value),
                format_6f(instance.Fully_Operational_Units[r, tmp]()),
                format_2f(instance.Provide_Power_MW[r, tmp].value),
                format_2f(max_rampup_mw),
                format_2f(max_rampdown_mw),
                format_2f(rampup_dual),
                format_2f(rampdown_dual),
                format_2f(max_reserve_ramp_up_mw),
                format_2f(max_reserve_ramp_down_mw),
                format_2f(reserve_ramp_up_dual),
                format_2f(reserve_ramp_down_dual),
                format_2f(min_gen),
                format_2f(min_gen_dual),
                format_2f(max_gen),
                format_2f(max_gen_dual)
            ])


def export_hydro_daily_budget_changes(instance, results_directory):
    """
    Export hydro daily budget changes when multi-day hydro sharing logic is on

    :param instance:
    :param results_directory:
    :return:
    """

    hydro_changes_writer = fileio.csvwriter(os.path.join(results_directory, "hydro_budget_changes.csv"))
    hydro_changes_writer.writerow([
        "zone",
        "hydro_resource",
        "period",
        "day_id",
        "daily_hydro_budget_increase_mwh"
    ])

    for hydro_resource in instance.HYDRO_RESOURCES:
        for period in instance.PERIODS:
            for day in instance.DAYS:
                hydro_changes_writer.writerow([
                    instance.zone[hydro_resource],
                    hydro_resource,
                    period,
                    day,
                    instance.Daily_Hydro_Budget_Increase_MWh[hydro_resource, period, day].value
                ])


def export_line_limits_resource_tx_use(instance, results_directory):
    """
    Export line limits when dedicated imports (storage and otherwise) affect line limits

    :param instance:
    :param results_directory:
    :return:
    """

    line_changes_writer = fileio.csvwriter(os.path.join(results_directory, "resource_tx_use_changes.csv"))
    line_changes_writer.writerow([
        "transmission_line",
        "timepoint",
        "min_flow",
        "transmit_flow_value",
        "transmit_unspecified_flow",
        "max_flow"
    ])

    for r_tx_id in instance.RESOURCE_TX_IDS:
        for tmp in instance.TIMEPOINTS:
            line_changes_writer.writerow([
                instance.tx_line_used[r_tx_id],
                tmp,
                instance.min_flow_planned_mw[instance.tx_line_used[r_tx_id]],
                instance.Transmit_Power_MW[instance.tx_line_used[r_tx_id],tmp](),
                instance.Transmit_Power_Unspecified_MW[instance.tx_line_used[r_tx_id],tmp].value,
                instance.max_flow_planned_mw[instance.tx_line_used[r_tx_id]]
            ])


def handle_exception(message, debug):
    """
    How to handle exceptions. First print a custom message and the traceback.
    If in debug mode, open the Python debugger (PDB), else exit. To execute multi-line statements in PDB, type this
    to launch an interactive Python session with all the local variables available.
    This function is used by export_results() to handle exceptions.
    :param message:
    :param debug:
    :return:
    """
    print(message)
    print(traceback.format_exc())
    if debug:
        print("""
           Launching Python debugger (PDB)...
           To execute multi-line statements in PDB, type this:
                import code; code.interact(local=vars())
           (The command launches an interactive Python session with all the local variables available.)
           To exit the interactive session and continue script execution, press Ctrl+D.
           """
        )
        tp, value, tb = sys.exc_info()
        pdb.post_mortem(tb)
    else:
        print('Exiting.')
        sys.exit()
