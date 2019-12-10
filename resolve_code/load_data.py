#!/usr/bin/env python

"""
This script loads model data.

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
from pyomo.environ import *
import model_formulation
import pandas as pd


def parse_timepoint_param(data, timepoint_mapping, index, value, namespace=None):
    """Fills values in DataPortal's '_dict' attribute for model instance for parameters indexed by model_object, timepoint.

    Args:
        data (pyo.DataPortal): Pyomo DataPortal object (we manually fill its '_data' attribute)
        timepoint_mapping (pd.DataFrame): Dataframe indexed by timepoint with period, month, day, and hour_of_day values
        index (tuple): Tuple index for parameter to set
        value (float): Parameter value to set
        namespace (str): Optional Pyomo model namespace (defaults to None)

    Raises:
        ValueError: If timepoint_mapping doesn't have a unique return value for a given period, day, and hour combination

    Returns:
        data (pyo.DataPortal): Pyomo DataPortal object (after additional parameter values added)
    """
    # parse tuple index for clarity
    param, model_object, period, day, hour_of_day_from, hour_of_day_to = index

    # convert the time indices to be ints
    hour_of_day_from = int(hour_of_day_from)
    hour_of_day_to = int(hour_of_day_to)
    day = int(day)
    period = int(period)

    for hour_of_day in range(hour_of_day_from, hour_of_day_to + 1):
        # find applicable timepoint
        timepoint_to_use = timepoint_mapping.loc[
            (timepoint_mapping['PERIODS'] == int(period)) &
            (timepoint_mapping['DAYS'] == int(day)) &
            (timepoint_mapping['HOURS_OF_DAY'] == int(hour_of_day)), :
        ].index


        if len(timepoint_to_use) > 1:
            raise ValueError('Timepoints are not unique for every period, day, and hour_of_day combination.')

        data._data[namespace][param][(model_object, timepoint_to_use[0])] = value

    return data

def parse_period_param(data, index, value, namespace=None):
    """Fills values in DataPortal's '_dict' attribute for model instance for parameters indexed by model_object, period.

    Args:
        data (pyo.DataPortal): Pyomo DataPortal object (we manually fill its '_data' attribute)
        index (tuple): Tuple index for parameter to set
        value (float): Parameter value to set
        namespace (str): Optional Pyomo model namespace (defaults to None)

    Returns:
        data (pyo.DataPortal): Pyomo DataPortal object (after additional parameter values added)
    """
    # parse tuple index for clarity
    param, model_object, period, day, hour_of_day_from, hour_of_day_to = index
    # convert to int
    period = int(period)

    data._data[namespace][param][(model_object, period)] = value

    return data


def parse_model_object_param(data, index, value, namespace=None):
    """Fills values in DataPortal's '_dict' attribute for model instance for parameters indexed by model_object.

    Args:
        data (pyo.DataPortal): Pyomo DataPortal object (we manually fill its '_data' attribute)
        index (tuple): Tuple index for parameter to set
        value (float): Parameter value to set
        namespace (str): Optional Pyomo model namespace (defaults to None)

    Returns:
        data (pyo.DataPortal): Pyomo DataPortal object (after additional parameter values added)
    """
    # parse tuple index for clarity
    param, model_object, period, day, hour_of_day_from, hour_of_day_to = index

    data._data[namespace][param][model_object] = value

    return data


def create_timepoint_mapping(data, namespace=None):
    """Creates a map of timepoints to the sets for PERIODS, MONTHS, DAYS, and HOURS_OF_DAY.

    Args:
        data (pyo.DataPortal): Pyomo DataPortal object (we manually fill its '_data' attribute)
        namespace (str): Optional Pyomo model namespace (defaults to None)

    Returns:
        timepoint_mapping (pd.DataFrame): Dataframe indexed by timepoint with period, month, day, and hour_of_day values
        sets (dict): Dict of unique sets for PERIODS, MONTHS, DAYS, and HOURS_OF_DAY
    """

    # Get mappings between timepoints and period, month, day, and hour
    timepoint_map = {}
    timepoint_map['PERIODS'] = data._data[namespace]['period']
    timepoint_map['MONTHS'] = data._data[namespace]['month']
    timepoint_map['DAYS'] = data._data[namespace]['day']
    timepoint_map['HOURS_OF_DAY'] = data._data[namespace]['hour_of_day']

    # Make a DataFrame to help find the timepoint that matches period, day, hour
    timepoint_mapping = pd.DataFrame(timepoint_map)
    # timepoint_mapping.columns = ['period', 'month', 'day', 'hour_of_day']
    timepoint_mapping.index.name = 'timepoint'

    # Get unique sets
    sets = {}
    sets['PERIODS'] = set(sorted(timepoint_map['PERIODS'].values()))
    sets['MONTHS'] = set(sorted(timepoint_map['MONTHS'].values()))
    sets['DAYS'] = set(sorted(timepoint_map['DAYS'].values()))
    sets['HOURS'] = set(sorted(timepoint_map['HOURS_OF_DAY'].values()))

    return timepoint_mapping, sets


def parse_flexible_params(data, flexible_params, namespace=None):
    """Parses time range-formatted params and adds them directly to the DataPortal's internal dictionary of values.

    Method can accommodate three types of parameters:
        1. Object-indexed parameters (indexed only by whatever is in the 'model_object' column)
        2. Object- and period-indexed parameters
        3. Object- and timepoint-indexed parameters

    Args:
        data (pyo.DataPortal): Pyomo DataPortal object (we manually fill its '_data' attribute)
        flexible_params (pd.DataFrame): Timerange parameter data to use
        namespace (str): Optional Pyomo model namespace (defaults to None)

    Raises:
        AttributeError: If parameter data already exists in DataPortal._data attribute

    Returns:
        data (pyo.DataPortal): Pyomo DataPortal object (after additional parameter values added)
    """
    # Get timepoints mapping
    timepoint_mapping, sets = create_timepoint_mapping(data)

    params_to_create = flexible_params.index.unique(level=0)

    for param in params_to_create:
        # Raise an error if any flexible params already exist in the DataPortal object
        if param in data._data[namespace].keys():
            raise AttributeError('Data for parameter {} is already loaded via data.load()'.format(param))
        # Initialize the nested dictionary with flexible params
        else:
            data._data[namespace][param] = {}

    # parse flexible params into DataPortal's _data dictionary
    for index, value in flexible_params.iterrows():
        # parse tuple index for clarity
        param, model_object, period, day, hour_of_day_from, hour_of_day_to = index

        # try to infer type of value and convert to Boolean or float
        value = value.value
        if not isinstance(value, float):
            if value in ['True', 'False']:
                value = bool(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass

        # pandas interprets None values in the index as 'None'
        # if we are just setting a simple (unindexed) parameter
        if all(idx == 'None' for idx in [period, day, hour_of_day_from, hour_of_day_to]):
            data = parse_model_object_param(data, index, value)

        # if we are setting a object parameter value for a specified period
        elif period != 'None' and all(idx == 'None' for idx in [day, hour_of_day_from, hour_of_day_to]):
            if period == 'All':
                for period_in_set in sets['PERIODS']:
                    index = (
                        param, model_object, period_in_set, day, hour_of_day_from, hour_of_day_to
                    )
                    data = parse_period_param(data, index, value)
            else:
                data = parse_period_param(data, index, value)

        # if we are setting parameter across timepoints
        else:
            # convert the time indices to be ints
            hour_of_day_from = int(hour_of_day_from)
            hour_of_day_to = int(hour_of_day_to)
            # raise error if hour_of_day_from or hour_of_day_to is not in the set of HOURS
            if hour_of_day_from not in sets['HOURS'] or hour_of_day_to not in sets['HOURS']:
                raise ValueError('Hour range set for {index} is invalid.'.format(index=index))
            if (day == 'All') and (period == 'All'):
                for period_in_set in sets['PERIODS']:
                    for day_in_set in sets['DAYS']:
                        index_for_day = (
                            param, model_object, period_in_set, day_in_set, hour_of_day_from, hour_of_day_to
                        )
                        parse_timepoint_param(
                            data, timepoint_mapping, index_for_day, value
                        )
            elif (day == 'All') and (not period == 'All'):
                for day_in_set in sets['DAYS']:
                    index_for_day = (
                        param, model_object, int(period), day_in_set, hour_of_day_from, hour_of_day_to
                    )
                    parse_timepoint_param(
                        data, timepoint_mapping, index_for_day, value
                    )
            elif (not day == 'All') and (period == 'All'):
                for period_in_set in sets['PERIODS']:
                    index_for_period = (
                        param, model_object, period_in_set, int(day), hour_of_day_from, hour_of_day_to
                    )
                    parse_timepoint_param(
                        data, timepoint_mapping, index_for_period, value
                    )
            else:
                parse_timepoint_param(data, timepoint_mapping, index, value)

    return data


def scenario_data(inputs_directory, feature_toggles):
    """
    Find and load data for the specified scenario.

    :param inputs_directory: the scenario inputs directory
    :param feature_toggles: toggle to turn on and off the functionality
    :return:
    """

    data = DataPortal()

    # All timepoints modeled with their associated metadata: which period, month, and day the timepoint is in,
    # and which hour of the day it represents.
    data.load(filename=os.path.join(inputs_directory, "timepoints.tab"),
              index=model_formulation.resolve_model.TIMEPOINTS,
              param=(model_formulation.resolve_model.period,
                     model_formulation.resolve_model.month,
                     model_formulation.resolve_model.day,
                     model_formulation.resolve_model.hour_of_day)
              )

    # The weight/discount factor applied to costs occurring in each period,
    # and the number of years represented by each period.
    data.load(filename=os.path.join(inputs_directory, "period_discount_factors.tab"),
              index=model_formulation.resolve_model.PERIODS,
              param=(model_formulation.resolve_model.discount_factor,
                     model_formulation.resolve_model.years_in_period)
              )

    # The weight associated with each day in RESOLVE; should sum up to 365.
    data.load(filename=os.path.join(inputs_directory, "day_weights.tab"),
              index=model_formulation.resolve_model.DAYS,
              param=model_formulation.resolve_model.day_weight
              )

    # The zones modeled, the spinning reserve requirements (if any) for each zone, and various flags.
    data.load(filename=os.path.join(inputs_directory, "zones.tab"),
              index=model_formulation.resolve_model.ZONES,
              param=(model_formulation.resolve_model.spin_reserve_fraction_of_load,
                     model_formulation.resolve_model.include_in_rps_target,
                     model_formulation.resolve_model.include_in_load_following,
                     model_formulation.resolve_model.include_in_ghg_target,
                     model_formulation.resolve_model.include_in_prm
                     )
              )

    # The input load in each zone in each timepoint.
    # Indexed by ZONES and TIMEPOINTS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "zone_timepoint_params.tab"),
              param=model_formulation.resolve_model.input_load_mw
              )

    # The regulation and load-following reserve requirements in each timepoint.
    data.load(filename=os.path.join(inputs_directory, "reserve_timepoint_requirements.tab"),
              index=model_formulation.resolve_model.TIMEPOINTS,
              param=(model_formulation.resolve_model.upward_reg_req,
                     model_formulation.resolve_model.downward_reg_req,
                     model_formulation.resolve_model.upward_lf_reserve_req,
                     model_formulation.resolve_model.downward_lf_reserve_req,
                     model_formulation.resolve_model.min_gen_committed_mw,
                     model_formulation.resolve_model.freq_resp_total_req_mw,
                     model_formulation.resolve_model.freq_resp_partial_req_mw
                     )
              )

    # All transmission lines with their origin (from) and destination (to) for the positive flow direction,
    # the minimum and maximum flow on the line, a flag for whether the line is ramp-constrained,
    # and a flag for whether a hurdle rate is applied on the line.
    data.load(filename=os.path.join(inputs_directory, "transmission_lines.tab"),
              index=model_formulation.resolve_model.TRANSMISSION_LINES,
              param=(model_formulation.resolve_model.transmission_from,
                     model_formulation.resolve_model.transmission_to,
                     model_formulation.resolve_model.min_flow_planned_mw,
                     model_formulation.resolve_model.max_flow_planned_mw,
                     model_formulation.resolve_model.ramp_constrained,
                     model_formulation.resolve_model.new_build_tx_flag)
              )

    # The names of the groups of lines over which simultaneous flow constraints are enforced.
    data.load(filename=os.path.join(inputs_directory, "simultaneous_flow_groups.tab"),
              set=model_formulation.resolve_model.SIMULTANEOUS_FLOW_GROUPS
              )

    # The limits on flow over each simultaneous flow group by period.
    # Indexed by SIMULTANEOUS_FLOW_GROUPS and PERIODS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "simultaneous_flow_limits.tab"),
              param=model_formulation.resolve_model.simultaneous_flow_limit_mw
              )

    # The line-directions included in each simultaneous flow group.
    data.load(filename=os.path.join(inputs_directory, "simultaneous_flow_group_lines.tab"),
              index=model_formulation.resolve_model.SIMULTANEOUS_FLOW_GROUP_LINES,
              param=model_formulation.resolve_model.direction)

    if feature_toggles['transmission_ramp_limit']:
        # The up and down ramp limits for each ramp-constrained line for each ramp duration.
        # Indexed by RAMP_CONSTRAINED_TRANSMISSION_LINES and INTERTIE_FLOW_RAMP_DURATIONS in model_formulation.py
        data.load(filename=os.path.join(inputs_directory, "transmission_ramps.tab"),
                  param=(model_formulation.resolve_model.flow_ramp_up_limit_fraction,
                         model_formulation.resolve_model.flow_ramp_down_limit_fraction)
                  )

    # Hurdle rates (cost per MW of energy flow) on each transmission line by period for both flow directions.
    # Indexed by TRANSMISSION_LINES and PERIODS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "hurdle_rates.tab"),
              param=(model_formulation.resolve_model.positive_direction_hurdle_rate_per_mw,
                     model_formulation.resolve_model.negative_direction_hurdle_rate_per_mw)
              )

    # Defines the set of fuels and the carbon content of each fuel.
    data.load(filename=os.path.join(inputs_directory, "fuels.tab"),
              index=model_formulation.resolve_model.FUELS,
              param=(model_formulation.resolve_model.tco2_per_mmbtu,
                     model_formulation.resolve_model.can_blend_with_pipeline_biogas)
              )

    # The price of each fuel by period and month.
    # Indexed by FUELS, PERIODS, and MONTHS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "fuel_prices.tab"),
              param=model_formulation.resolve_model.fuel_price_per_mmbtu
              )

    # GHG targets for each period.
    data.load(filename=os.path.join(inputs_directory, "ghg_targets.tab"),
              index=model_formulation.resolve_model.PERIODS,
              param=(model_formulation.resolve_model.ghg_emissions_target_tco2_per_year,
                     model_formulation.resolve_model.ghg_emissions_credit_tco2_per_year)
              )

    # The assumed greenhouse gas emissions intensity resulting from imports into the ghg target area
    # in each period for each transmission line.
    # Indexed by TRANSMISSION_LINES_GHG_TARGET and PERIODS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "ghg_import_rates.tab"),
              param=(model_formulation.resolve_model.positive_direction_tco2_per_mwh,
                     model_formulation.resolve_model.negative_direction_tco2_per_mwh)
              )

    # All technologies modeled, with flags for various operational characteristics.
    data.load(filename=os.path.join(inputs_directory, "technologies.tab"),
              index=model_formulation.resolve_model.TECHNOLOGIES,
              param=(model_formulation.resolve_model.thermal,
                     model_formulation.resolve_model.dispatchable,
                     model_formulation.resolve_model.generate_at_max,
                     model_formulation.resolve_model.variable,
                     model_formulation.resolve_model.storage,
                     model_formulation.resolve_model.hydro,
                     model_formulation.resolve_model.variable_cost_per_mwh,
                     model_formulation.resolve_model.firm_capacity,
                     model_formulation.resolve_model.conventional_dr,
                     model_formulation.resolve_model.hydrogen_electrolysis,
                     model_formulation.resolve_model.electric_vehicle,
                     model_formulation.resolve_model.energy_efficiency,
                     model_formulation.resolve_model.flexible_load)
              )

    # Parameters associated with each thermal technology: the fuel used, and the fuel burn slope and intercept.
    data.load(filename=os.path.join(inputs_directory, "tech_thermal_params.tab"),
              index=model_formulation.resolve_model.THERMAL_TECHNOLOGIES,
              param=(model_formulation.resolve_model.fuel,
                     model_formulation.resolve_model.fuel_burn_slope_mmbtu_per_mwh,
                     model_formulation.resolve_model.fuel_burn_intercept_mmbtu_per_hr)
              )

    # Parameters associated with each dispatchable thermal technology:
    # minimum stable level as fraction of capacity, ramp rate as fraction of capacity,
    # startup and shutdown time (integer hours), unit size, and startup and shutdown costs.
    data.load(filename=os.path.join(inputs_directory, "tech_dispatchable_params.tab"),
              index=model_formulation.resolve_model.DISPATCHABLE_TECHNOLOGIES,
              param=(model_formulation.resolve_model.min_stable_level_fraction,
                     model_formulation.resolve_model.ramp_rate_fraction,
                     model_formulation.resolve_model.min_down_time_hours,
                     model_formulation.resolve_model.min_up_time_hours,
                     model_formulation.resolve_model.unit_size_mw,
                     model_formulation.resolve_model.startup_cost_per_mw,
                     model_formulation.resolve_model.shutdown_cost_per_mw,
                     model_formulation.resolve_model.start_fuel_mmbtu_per_mw)
              )

    # Parameters associated with each storage technology:
    # charging and discharging efficiencies, and minimum storage duration.
    data.load(filename=os.path.join(inputs_directory, "tech_storage_params.tab"),
              index=model_formulation.resolve_model.STORAGE_TECHNOLOGIES,
              param=(model_formulation.resolve_model.charging_efficiency,
                     model_formulation.resolve_model.discharging_efficiency,
                     model_formulation.resolve_model.min_duration_h)
              )

    # The annual fixed cost of per unit of energy capacity ($/kWh-yr) for storage resources by vintage.
    # Indexed by NEW_BUILD_STORAGE_RESOURCES and VINTAGES in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "resource_vintage_storage_params.tab"),
              param=(model_formulation.resolve_model.energy_storage_cost_per_kwh_yr,
                     model_formulation.resolve_model.new_energy_capacity_fixed_o_and_m_dollars_per_kwh_yr)
              )

    # All resources with their technology, zone, and rps eligibility
    # as well as flags for whether capacity can be built and retired,
    # whether there is a limit on the total capacity that can be built for the resource,
    # whether the resource satisfy local capacity needs,
    # and whether the resource has local capacity limits.
    data.load(filename=os.path.join(inputs_directory, "resources.tab"),
              index=model_formulation.resolve_model.RESOURCES,
              param=(model_formulation.resolve_model.technology,
                     model_formulation.resolve_model.zone,
                     model_formulation.resolve_model.rps_eligible,
                     model_formulation.resolve_model.can_build_new,
                     model_formulation.resolve_model.capacity_limited,
                     model_formulation.resolve_model.local_capacity,
                     model_formulation.resolve_model.capacity_limited_local,
                     model_formulation.resolve_model.can_retire)
              )

    # Defines the relationship between each resource and reserve product.
    data.load(filename=os.path.join(inputs_directory, "reserve_resources.tab"),
              index=model_formulation.resolve_model.RESERVE_RESOURCES,
              param=(model_formulation.resolve_model.can_provide_spin,
                     model_formulation.resolve_model.can_provide_reg,
                     model_formulation.resolve_model.can_provide_lf_reserves,
                     model_formulation.resolve_model.contributes_to_min_gen,
                     model_formulation.resolve_model.contributes_to_freq_resp_total_req,
                     model_formulation.resolve_model.contributes_to_freq_resp_partial_req,
                     model_formulation.resolve_model.thermal_freq_response_fraction_of_commitment)
              )

    # Parameters related to variable renewable resource participation
    # in the planning reserve margin and local capacity constraints.
    data.load(filename=os.path.join(inputs_directory, "resource_variable_renewable_prm.tab"),
              index=model_formulation.resolve_model.PRM_VARIABLE_RENEWABLE_RESOURCES,
              param=(model_formulation.resolve_model.capacity_factor,
                     model_formulation.resolve_model.elcc_solar_bin,
                     model_formulation.resolve_model.elcc_wind_bin,
                     model_formulation.resolve_model.local_variable_renewable_nqc_fraction)
              )

    # Parameters related to the curtailment of variable renewable resources
    data.load(filename=os.path.join(inputs_directory, "resource_variable_renewable.tab"),
              index=model_formulation.resolve_model.VARIABLE_RESOURCES,
              param=model_formulation.resolve_model.curtailable
              )

    # The maximum capacity of each resource that can be built in each period.
    # Resources that do not have capacity limits enforced are not included.
    # Indexed by CAPACITY_LIMITED_RESOURCES and PERIODS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "capacity_limits.tab"),
              param=model_formulation.resolve_model.capacity_limit_mw
              )

    # The planned installed capacity of each resource in each period.
    # The cost of planned capacity is assumed to be sunk and consequently is not included in the optimization,
    # but fixed operations and maintenance costs are included for planned capacity
    # Indexed by RESOURCES_WITH_MW_CAPACITY and PERIODS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "planned_installed_capacities.tab"),
              param=(model_formulation.resolve_model.planned_installed_capacity_mw,
                     model_formulation.resolve_model.min_operational_planned_capacity_mw,
                     model_formulation.resolve_model.planned_capacity_fixed_o_and_m_dollars_per_kw_yr)
              )

    # The minimum amount of new capacity of each resource that must be built through each period.
    # The cost of building these resources is not assumed to be sunk (in contrast to planned_installed_capacities.tab)
    # Indexed by NEW_BUILD_RESOURCES and PERIODS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "min_cumulative_new_build.tab"),
              param=model_formulation.resolve_model.min_cumulative_new_build_mw
              )

    # The annual capital and fixed operations and maintenence cost per unit of capacity ($/kW-yr)
    # for each resource that can install new capacity.  Costs can vary by installation year (vintage).
    # Indexed by NEW_BUILD_RESOURCES and VINTAGES in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "resource_vintage_params.tab"),
              param=(model_formulation.resolve_model.capital_cost_per_kw_yr,
                     model_formulation.resolve_model.new_capacity_fixed_o_and_m_dollars_per_kw_yr)
              )

    # The net qualifying capacity (NQC) fraction for firm and storage capacity resources.
    data.load(filename=os.path.join(inputs_directory, "resource_prm_nqc.tab"),
              index=model_formulation.resolve_model.PRM_NQC_RESOURCES,
              param=model_formulation.resolve_model.net_qualifying_capacity_fraction
              )

    # The planned installed energy capacity of each storage resource in each period.
    # Indexed by STORAGE_RESOURCES and PERIODS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "planned_storage_energy_capacity.tab"),
              param=(model_formulation.resolve_model.planned_storage_energy_capacity_mwh,
                     model_formulation.resolve_model.planned_storage_energy_capacity_fixed_o_and_m_dollars_per_kwh_yr)
              )

    # The normalized profiles for each variable resource for each day and hour.
    # Indexed by VARIABLE_RESOURCES, DAYS, and HOURS_OF_DAY in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "shapes.tab"),
              param=(model_formulation.resolve_model.shape,
                     model_formulation.resolve_model.resource_downward_lf_req,
                     model_formulation.resolve_model.resource_upward_lf_req))

    # The daily energy budget, minimum generation level, and maximum generation level
    # for each hydro resource and each day.
    # Indexed by HYDRO_RESOURCES and DAYS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "hydro_daily_params.tab"),
              param=(model_formulation.resolve_model.hydro_daily_energy_fraction,
                     model_formulation.resolve_model.hydro_min_gen_fraction,
                     model_formulation.resolve_model.hydro_max_gen_fraction)
              )

    # The set of hydro resources for which multi-hour ramping limits will be defined.
    data.load(filename=os.path.join(inputs_directory, "hydro_resources_ramp_limited.tab"),
              set=model_formulation.resolve_model.RAMP_CONSTRAINED_HYDRO_RESOURCES
              )

    # Limits on hydro ramps for each ramp duration for each ramp-limited hydro resource.
    # Indexed by RAMP_CONSTRAINED_HYDRO_RESOURCES and HYDRO_RAMP_DURATIONS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "hydro_ramps.tab"),
              param=(model_formulation.resolve_model.hydro_ramp_up_limit_fraction,
                     model_formulation.resolve_model.hydro_ramp_down_limit_fraction)
              )

    # A range of single-value parameters including penalties for unserved energy, overgeneration,
    # and reserve violations; the durations of hydro and intertie ramps to constrain;
    # parameterizations of the sub-hourly behavior when providing regulation and load-following reserves;
    # parameterizations of the ability of variable generation to provide reserves;
    # whether to require renewable overbuild when satisfying RPS constraints;
    # whether to allow RPS banking;
    # whether to enforce GHG targets;
    # the number of hours of duration that receives full ELCC credit;
    # and the assumed timeframe for operational reserves.
    data.load(filename=os.path.join(inputs_directory, "system_params.tab"),
              param=(model_formulation.resolve_model.unserved_energy_penalty_per_mw,
                     model_formulation.resolve_model.overgen_penalty_per_mw,
                     model_formulation.resolve_model.spin_violation_penalty_per_mw,
                     model_formulation.resolve_model.upward_reg_violation_penalty_per_mw,
                     model_formulation.resolve_model.downward_reg_violation_penalty_per_mw,
                     model_formulation.resolve_model.upward_lf_reserve_violation_penalty_per_mw,
                     model_formulation.resolve_model.downward_lf_reserve_violation_penalty_per_mw,
                     model_formulation.resolve_model.max_hydro_ramp_duration_to_constrain,
                     model_formulation.resolve_model.max_intertie_ramp_duration_to_constrain,
                     model_formulation.resolve_model.reg_dispatch_fraction,
                     model_formulation.resolve_model.lf_reserve_dispatch_fraction,
                     model_formulation.resolve_model.var_rnw_available_for_lf_reserves,
                     model_formulation.resolve_model.max_var_rnw_lf_reserves,
                     model_formulation.resolve_model.require_overbuild,
                     model_formulation.resolve_model.optimize_rps_banking,
                     model_formulation.resolve_model.enforce_ghg_targets,
                     model_formulation.resolve_model.elcc_hours,
                     model_formulation.resolve_model.reserve_timeframe_fraction_of_hour,
                     model_formulation.resolve_model.starting_rps_bank_mwh,
                     model_formulation.resolve_model.count_storage_losses_as_rps_curtailment,
                     model_formulation.resolve_model.allow_hydro_spill,
                     model_formulation.resolve_model.allow_unserved_energy)
              )

    # The RPS target across all RPS zones by period (in MWh).
    data.load(filename=os.path.join(inputs_directory, "renewable_targets.tab"),
              index=model_formulation.resolve_model.PERIODS,
              param=(model_formulation.resolve_model.rps_nonmodeled_mwh,
                     model_formulation.resolve_model.rps_bank_planned_spend_mwh,
                     model_formulation.resolve_model.pipeline_biogas_available_mmbtu_per_year,
                     model_formulation.resolve_model.incremental_pipeline_biogas_cost_per_mmbtu,
                     model_formulation.resolve_model.rps_unbundled_fraction_limit,
                     model_formulation.resolve_model.retail_sales_mwh,
                     model_formulation.resolve_model.rps_fraction_of_retail_sales)
              )

    # curtailment cost by period specified for each contract zone.
    # indexed by ZONES and PERIODS
    data.load(filename=os.path.join(inputs_directory, "zone_curtailment_costs.tab"),
              param=model_formulation.resolve_model.curtailment_cost_per_mwh
              )

    # The transmission zone aggregations for which energy only or fully deliverable transmission capacity
    # will be built for new renewable resources.  Capacity limits for energy only and zero-cost fully deliverable
    # capacity are included, along with the cost to build new fully deliverable capacity.
    data.load(filename=os.path.join(inputs_directory, "tx_zones.tab"),
              index=model_formulation.resolve_model.TX_ZONES,
              param=(model_formulation.resolve_model.tx_deliverability_cost_per_mw_yr,
                     model_formulation.resolve_model.fully_deliverable_new_tx_threshold_mw,
                     model_formulation.resolve_model.energy_only_tx_limit_mw)
              )

    # The transmission zone for newly buildable renewable resources.
    data.load(filename=os.path.join(inputs_directory, "resource_tx_zones.tab"),
              index=model_formulation.resolve_model.TX_DELIVERABILITY_RESOURCES,
              param=(model_formulation.resolve_model.tx_zone_of_resource,
                     model_formulation.resolve_model.import_on_existing_tx,
                     model_formulation.resolve_model.import_on_new_tx,
                     model_formulation.resolve_model.tx_import_capacity_fraction))

    if feature_toggles['include_electric_vehicles']:
        # The charging efficiency of each EV resource.
        data.load(filename=os.path.join(inputs_directory, "ev_params.tab"),
                  index=model_formulation.resolve_model.EV_RESOURCES,
                  param=model_formulation.resolve_model.ev_charging_efficiency
                  )

        # The total battery capacity of each EV resource in each period,
        # and the minimum energy that must always be available in each resource's battery
        # Indexed by EV_RESOURCES and PERIODS in model_formulation.py
        data.load(filename=os.path.join(inputs_directory, "ev_period_params.tab"),
                  param=(model_formulation.resolve_model.total_ev_battery_energy_capacity_mwh,
                         model_formulation.resolve_model.minimum_energy_in_ev_batteries_mwh)
                  )

        # The amount of demand from each EV resource in each timepoint.
        # Indexed by EV_RESOURCES and TIMEPOINTS in model_formulation.py
        data.load(filename=os.path.join(inputs_directory, "ev_timepoint_params.tab"),
                  param=(model_formulation.resolve_model.driving_energy_demand_mw,
                         model_formulation.resolve_model.ev_battery_plugged_in_capacity_mw)
                  )

    if feature_toggles['include_hydrogen_electrolysis']:
        # The daily total hydrogen electrolysis energy demand and minimum hourly load in each period and day.
        # Indexed by HYDROGEN_ELECTROLYSIS_RESOURCES, PERIODS, and DAYS in model_formulation.py
        data.load(filename=os.path.join(inputs_directory, "hydrogen_electrolysis_daily_params.tab"),
                  param=(model_formulation.resolve_model.hydrogen_electrolysis_load_min_mw,
                         model_formulation.resolve_model.hydrogen_electrolysis_load_daily_mwh)
                  )

    # The maximum amount of energy that can be dispatched (shed) annually from conventional demand response resources
    # Indexed by CONVENTIONAL_DR_RESOURCES and PERIODS in model_formulation.py
    data.load(filename=os.path.join(inputs_directory, "conventional_dr_period_limits.tab"),
              param=(model_formulation.resolve_model.conventional_dr_availability_hours_per_year,
                     model_formulation.resolve_model.conventional_dr_daily_capacity_factor)
              )

    if feature_toggles['include_flexible_load']:
        # The amount of load that can be shifted up or down in each timepoint
        # as a fraction of the total daily flexible load potential.
        # Indexed by FLEXIBLE_LOAD_RESOURCES and TIMEPOINTS in model_formulation.py
        data.load(filename=os.path.join(inputs_directory, "flexible_load_timepoint_params.tab"),
                  param=(model_formulation.resolve_model.shift_load_down_potential_factor,
                         model_formulation.resolve_model.shift_load_up_potential_factor)
                  )

        # Indices that define each breakpoint in the flexible load (shift) supply curve.
        data.load(filename=os.path.join(inputs_directory, "flexible_load_cost_curve_index.tab"),
                  set=model_formulation.resolve_model.FLEXIBLE_LOAD_COST_CURVE_INDEX
                  )

        # Flexible load (shift) supply curve for each period.
        # Indexed by FLEXIBLE_LOAD_RESOURCES, FLEXIBLE_LOAD_COST_CURVE_INDEX and PERIODS in model_formulation.py
        data.load(filename=os.path.join(inputs_directory, "flexible_load_cost_curve.tab"),
                  param=(model_formulation.resolve_model.flexible_load_cost_curve_slope,
                         model_formulation.resolve_model.flexible_load_cost_curve_intercept)
                  )

        # Flexible load (shift) minimum and maximum resource potential limits for each period.
        # Indexed by FLEXIBLE_LOAD_RESOURCES and PERIODS in model_formulation.py
        data.load(filename=os.path.join(inputs_directory, "flexible_load_capacity_period_params.tab"),
                  param=(model_formulation.resolve_model.max_flexible_load_shift_potential_mwh,
                         model_formulation.resolve_model.min_cumulative_new_flexible_load_shift_mwh)
                  )


    # The planning reserve margin target across all PRM zones in each period,
    # and other quantities related to the planning reserve margin.
    # Also included is the amount of capacity needed in local areas in each period.
    data.load(filename=os.path.join(inputs_directory, "planning_reserve_margin.tab"),
              index=model_formulation.resolve_model.PERIODS,
              param=(model_formulation.resolve_model.planning_reserve_margin,
                     model_formulation.resolve_model.prm_peak_load_mw,
                     model_formulation.resolve_model.prm_annual_load_mwh,
                     model_formulation.resolve_model.prm_planned_import_capacity_mw,
                     model_formulation.resolve_model.prm_import_resource_capacity_adjustment_mw,
                     model_formulation.resolve_model.local_capacity_deficiency_mw,
                     model_formulation.resolve_model.allow_unspecified_import_contribution)
              )

    # Effective load carrying capability (ELCC) surface facet coefficients for wind and solar power.
    data.load(filename=os.path.join(inputs_directory, "elcc_surface.tab"),
              index=model_formulation.resolve_model.ELCC_SURFACE_FACETS,
              param=(model_formulation.resolve_model.solar_coefficient,
                     model_formulation.resolve_model.wind_coefficient,
                     model_formulation.resolve_model.facet_intercept)
              )

    if feature_toggles['energy_sufficiency']:
        data.load(filename=os.path.join(inputs_directory,
                                        "energy_sufficiency_horizon_id.tab"),
                  set=model_formulation.resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS)

        data.load(filename=os.path.join(inputs_directory,
                                        "energy_sufficiency_horizon_energy_demand.tab"),
                  param=model_formulation.resolve_model.energy_sufficiency_average_load_aMW)

        data.load(filename=os.path.join(inputs_directory,
                                        "energy_sufficiency_horizon_params.tab"),
                  param=(model_formulation.resolve_model.energy_sufficiency_horizon_hours))

        data.load(filename=os.path.join(inputs_directory,
                                        "energy_sufficiency_average_capacity_factors.tab"),
                  param=model_formulation.resolve_model.energy_sufficiency_average_capacity_factor)


    # Parameters for hydro sharing group logic
    if feature_toggles['multi_day_hydro_energy_sharing']:
        data.load(filename=os.path.join(inputs_directory, "hydro_sharing_interval_mapping.tab"),
                  index=model_formulation.resolve_model.DAYS,
                  param=model_formulation.resolve_model.hydro_sharing_interval_id
                  )

        data.load(filename=os.path.join(inputs_directory, "hydro_sharing_max_to_move_within_group.tab"),
                  param=model_formulation.resolve_model.max_hydro_to_move_around_hours
                  )

        data.load(filename=os.path.join(inputs_directory, "hydro_sharing_daily_max_changes.tab"),
                  param=(model_formulation.resolve_model.daily_max_hydro_budget_increase_hours,
                         model_formulation.resolve_model.daily_max_hydro_budget_decrease_hours)
                  )

    # parameters for ee program
    if feature_toggles['allow_ee_investment']:
        data.load(filename=os.path.join(inputs_directory, "ee_params.tab"),
                  index=model_formulation.resolve_model.EE_PROGRAMS,
                  param=(model_formulation.resolve_model.ee_t_and_d_losses_fraction,
                         model_formulation.resolve_model.ee_btm_peak_load_reduction_mw_per_amw,
                         model_formulation.resolve_model.ee_btm_local_capacity_mw_per_amw)
                  )

        data.load(filename=os.path.join(inputs_directory, "ee_period_params.tab"),
                  param=model_formulation.resolve_model.max_investment_in_period_aMW
                  )

        data.load(filename=os.path.join(inputs_directory, "ee_timepoint_params.tab"),
                  param=model_formulation.resolve_model.ee_shapes_btm_mwh_per_amw
                  )

    # parameters needed if you want to have existing resources generation being counted as using tx lines capacity
    if feature_toggles['resource_use_tx_capacity']:
        data.load(filename=os.path.join(inputs_directory, "resource_use_tx_capacity.tab"),
                  index=model_formulation.resolve_model.RESOURCE_TX_IDS,
                  param=(model_formulation.resolve_model.dedicated_import_resource,
                         model_formulation.resolve_model.tx_line_used,
                         model_formulation.resolve_model.resource_tx_direction)
                  )

    # parameters for semi-storage zones features where you can send and get back power to a "semi_storage_zone"
    # with hurdle rates
    if feature_toggles['allow_semi_storage_zones']:
        data.load(filename=os.path.join(inputs_directory, "semi_storage_zones_params.tab"),
                  index=model_formulation.resolve_model.SEMI_STORAGE_ZONES,
                  param=model_formulation.resolve_model.ssz_from_zone
                  )

    if feature_toggles['allow_semi_storage_zones']:
        data.load(filename=os.path.join(inputs_directory, "semi_storage_zones_period_params.tab"),
                  param=(model_formulation.resolve_model.ssz_max_flow_mw,
                         model_formulation.resolve_model.ssz_min_flow_mw,
                         model_formulation.resolve_model.ssz_positive_direction_hurdle_rate_per_mw,
                         model_formulation.resolve_model.ssz_negative_direction_hurdle_rate_per_mw)
                  )

    if feature_toggles['allow_tx_build']:
        data.load(filename=os.path.join(inputs_directory, "transmission_new_build_vintages.tab"),
                  param=(model_formulation.resolve_model.max_tx_build_mw,
                         model_formulation.resolve_model.min_tx_build_mw,
                         model_formulation.resolve_model.new_tx_fixed_cost_per_mw_yr,
                         model_formulation.resolve_model.new_build_local_capacity_contribution)
                        )

    # Flexible Param functionality reads in a CSV and adds directly to DataPortal's '_dict' attribute
    flexible_params = pd.read_csv(
        os.path.join(inputs_directory, "flexible_params.csv"),
        header=0,
        index_col=list(range(0, 6))
    )
    data = parse_flexible_params(data, flexible_params)

    return data, flexible_params
