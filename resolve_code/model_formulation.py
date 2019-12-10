#!/usr/bin/env python
# coding: utf-8

"""
This script contains the model formulation.

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

from __future__ import division

from pyomo.environ import *
from run_opt import DirStructure
import os

# load in feature toggles
code_directory = os.getcwd()
dir_str = DirStructure(code_directory)
dir_str.get_feature_toggles()

# ############ RESOLVE FORMULATION ############## #

resolve_model = AbstractModel()
for key in dir_str.feature_toggles.keys():
    setattr(resolve_model, key, dir_str.feature_toggles[key])


# SETS

# Temporal resolution

resolve_model.TIMEPOINTS = Set(domain=PositiveIntegers, ordered=True, doc="unique study timepoints")

resolve_model.period = Param(resolve_model.TIMEPOINTS, within=PositiveIntegers)
resolve_model.month = Param(resolve_model.TIMEPOINTS, within=PositiveIntegers)
resolve_model.day = Param(resolve_model.TIMEPOINTS, within=PositiveIntegers)
resolve_model.hour_of_day = Param(resolve_model.TIMEPOINTS, within=NonNegativeIntegers)


# Investment periods
def periods_init(model):
    periods = list()
    for tmp_p in model.TIMEPOINTS:
        periods.append(model.period[tmp_p])
    periods = list(set(periods))
    return sorted(periods)

resolve_model.PERIODS = Set(domain=PositiveIntegers, initialize=periods_init, ordered=True)
# The set PERIODS and the set VINTAGES are the same
# but VINTAGES denotes when a resource is built (as opposed to operated)
resolve_model.VINTAGES = Set(domain=PositiveIntegers, initialize=periods_init, ordered=True)


# find the first period
def first_period_init(model):
    return min(model.PERIODS)

resolve_model.first_period = Param(domain=PositiveIntegers, initialize=first_period_init)


def find_prev_period(model, period):
    """
    Returns the previous period, or none if the current period is the first period
    :param model:
    :param period:
    :return:
    """
    previous_periods = []
    for q in model.PERIODS:
        if q < period:
            previous_periods.append(q)

    if previous_periods != []:
        prev_period = max(previous_periods)
    else:
        prev_period = None

    return prev_period


def period_vintage_init(model):
    """
    No retirements yet, so this is simply the set of tuples with the first element being the period and the second
    element being all vintages smaller than the period (i.e. capacity installed before the current period)
    :param model:
    :return:
    """
    period_vintages = list()
    for p in model.PERIODS:
        for v in model.VINTAGES:
            if v <= p:
                period_vintages.append((p, v))
    return period_vintages

resolve_model.PERIOD_VINTAGES = Set(dimen=2,
                                    within=resolve_model.PERIODS * resolve_model.VINTAGES,
                                    initialize=period_vintage_init,
                                    ordered=True)


def days_init(model):
    """
    Days -- unique IDs within each period
    :param model:
    :return:
    """
    days = list()
    for tmp_d in model.TIMEPOINTS:
        days.append(model.day[tmp_d])
    days = list(set(days))
    return sorted(days)

resolve_model.DAYS = Set(domain=PositiveIntegers, initialize=days_init, ordered=True, doc="unique study days")


def hours_of_day_init(model):
    """
    Hours of day -- unique IDs within each day
    :param model:
    :return:
    """
    hours_of_day = list()
    for tmp in model.TIMEPOINTS:
        hours_of_day.append(model.hour_of_day[tmp])
    hours_of_day = list(set(hours_of_day))
    return sorted(hours_of_day)

resolve_model.HOURS_OF_DAY = Set(domain=NonNegativeIntegers, initialize=hours_of_day_init, ordered=True)


def first_timepoint_of_day_init(model, period, day):
    """
    Defines the first timepoint on each day.  Assumes timepoints are ordered.
    :param model:
    :param period:
    :param day:
    :return:
    """
    timepoints_on_day = list()
    for timepoint in model.TIMEPOINTS:
        if model.period[timepoint] == period and model.day[timepoint] == day:
            timepoints_on_day.append(timepoint)
    return min(timepoints_on_day)

resolve_model.first_timepoint_of_day = Param(resolve_model.PERIODS, resolve_model.DAYS,
                                             initialize=first_timepoint_of_day_init)


def last_timepoint_of_day_init(model, period, day):
    """
    Defines the last timepoint on each day.  Assumes timepoints are ordered.
    :param model:
    :param period:
    :param day:
    :return:
    """
    timepoints_on_day = list()
    for timepoint in model.TIMEPOINTS:
        if model.period[timepoint] == period and model.day[timepoint] == day:
            timepoints_on_day.append(timepoint)
    return max(timepoints_on_day)

resolve_model.last_timepoint_of_day = Param(resolve_model.PERIODS, resolve_model.DAYS,
                                            initialize=last_timepoint_of_day_init)


def previous_timepoint_init(model):
    """
    Define a "previous timepoint" for periodic boundary constraints
    The previous timepoint for the first hour of the day is the last hour of that day
    :param model:
    :return:
    """
    previous_tp = dict()
    for timepoint in model.TIMEPOINTS:
        if timepoint == model.first_timepoint_of_day[model.period[timepoint], model.day[timepoint]]:
            previous_tp[timepoint] = model.last_timepoint_of_day[model.period[timepoint], model.day[timepoint]]
        else:
            previous_tp[timepoint] = timepoint - 1
    return previous_tp

resolve_model.previous_timepoint = Param(resolve_model.TIMEPOINTS, initialize=previous_timepoint_init)


def next_timepoint_init(model):
    """
    Define a "next timepoint" for periodic boundary constraints
    The next timepoint for the last hour of the day is the first hour of that day
    :param model:
    :return:
    """
    next_tp = dict()
    for timepoint in model.TIMEPOINTS:
        if timepoint == model.last_timepoint_of_day[model.period[timepoint], model.day[timepoint]]:
            next_tp[timepoint] = model.first_timepoint_of_day[model.period[timepoint], model.day[timepoint]]
        else:
            next_tp[timepoint] = timepoint + 1
    return next_tp

resolve_model.next_timepoint = Param(resolve_model.TIMEPOINTS, initialize=next_timepoint_init)


def months_init(model):
    """
    Not currently used.
    :param model:
    :return:
    """
    months = []
    for tmp_m in model.TIMEPOINTS:
        months.append(model.month[tmp_m])
    months = list(set(months))  # set() gets the unique values from list; list() converts back to list
    return sorted(months)

resolve_model.MONTHS = Set(initialize=months_init, ordered=True)


# ### Spatial resolution ### #

resolve_model.ZONES = Set(ordered=True)

# Transmission
resolve_model.TRANSMISSION_LINES = Set(ordered=True)

resolve_model.transmission_from = Param(resolve_model.TRANSMISSION_LINES, within=resolve_model.ZONES)
resolve_model.transmission_to = Param(resolve_model.TRANSMISSION_LINES, within=resolve_model.ZONES)

resolve_model.SIMULTANEOUS_FLOW_GROUPS = Set(ordered=True)
resolve_model.simultaneous_flow_limit_mw = Param(resolve_model.SIMULTANEOUS_FLOW_GROUPS, resolve_model.PERIODS,
                                                 within=Reals)
resolve_model.SIMULTANEOUS_FLOW_GROUP_LINES = \
    Set(dimen=2,
        within=resolve_model.SIMULTANEOUS_FLOW_GROUPS * resolve_model.TRANSMISSION_LINES,
        ordered=True)
resolve_model.direction = Param(resolve_model.SIMULTANEOUS_FLOW_GROUP_LINES, within=Integers)


# Make sure direction is -1 or 1
def direction_abs_init(model, sfg, line):
    return abs(model.direction[(sfg, line)])


def direction_validate(model, a, sfg, line):
    return a == 1

resolve_model.direction_abs = Param(resolve_model.SIMULTANEOUS_FLOW_GROUP_LINES,
                                    initialize=direction_abs_init, validate=direction_validate)


# ### Technologies and resources ### #

resolve_model.TECHNOLOGIES = Set(ordered=True)  # technology type index

resolve_model.thermal = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.dispatchable = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.generate_at_max = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.variable = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.storage = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.hydro = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.firm_capacity = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.conventional_dr = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.hydrogen_electrolysis = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.electric_vehicle = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.energy_efficiency = Param(resolve_model.TECHNOLOGIES, within=Boolean)
resolve_model.flexible_load = Param(resolve_model.TECHNOLOGIES, within=Boolean)

resolve_model.THERMAL_TECHNOLOGIES = \
    Set(within=resolve_model.TECHNOLOGIES,
        initialize=resolve_model.TECHNOLOGIES,
        filter=lambda model, technology: model.thermal[technology],
        ordered=True)

resolve_model.DISPATCHABLE_TECHNOLOGIES = \
    Set(within=resolve_model.THERMAL_TECHNOLOGIES,
        initialize=resolve_model.THERMAL_TECHNOLOGIES,
        filter=lambda model, technology: model.dispatchable[technology],
        ordered=True)

resolve_model.STORAGE_TECHNOLOGIES = \
    Set(within=resolve_model.TECHNOLOGIES,
        initialize=resolve_model.TECHNOLOGIES,
        filter=lambda model, technology: model.storage[technology],
        ordered=True)


# Fuels set
resolve_model.FUELS = Set(ordered=True)


# ### Resources ### #
resolve_model.RESOURCES = Set(ordered=True)  # indexed by technology AND zone

resolve_model.technology = Param(resolve_model.RESOURCES, within=resolve_model.TECHNOLOGIES)
resolve_model.zone = Param(resolve_model.RESOURCES, within=resolve_model.ZONES)
resolve_model.can_build_new = Param(resolve_model.RESOURCES, within=Binary)
resolve_model.capacity_limited = Param(resolve_model.RESOURCES, within=Binary)
resolve_model.local_capacity = Param(resolve_model.RESOURCES, within=Binary)
resolve_model.capacity_limited_local = Param(resolve_model.RESOURCES, within=Binary)
resolve_model.rps_eligible = Param(resolve_model.RESOURCES, within=Boolean)
resolve_model.can_retire = Param(resolve_model.RESOURCES, within=Binary)

# Resource types, distinguished by operational characteristics
resolve_model.THERMAL_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.thermal[model.technology[resource]],
        validate=lambda model, resource: (
            model.dispatchable[model.technology[resource]] + model.generate_at_max[model.technology[resource]] == 1
        ),
        ordered=True)

resolve_model.DISPATCHABLE_RESOURCES = \
    Set(within=resolve_model.THERMAL_RESOURCES,
        initialize=resolve_model.THERMAL_RESOURCES,
        filter=lambda model, resource: model.dispatchable[model.technology[resource]],
        ordered=True)

resolve_model.GENERATE_AT_MAX_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.generate_at_max[model.technology[resource]],
        ordered=True)

resolve_model.CONVENTIONAL_DR_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.conventional_dr[model.technology[resource]],
        ordered=True)

resolve_model.HYDROGEN_ELECTROLYSIS_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.hydrogen_electrolysis[model.technology[resource]],
        ordered=True)

resolve_model.EV_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.electric_vehicle[model.technology[resource]],
        ordered=True)

# Resources that can only increase demand (that only act as a load)
resolve_model.LOAD_ONLY_RESOURCES = \
    Set(initialize=resolve_model.HYDROGEN_ELECTROLYSIS_RESOURCES | resolve_model.EV_RESOURCES,
        ordered=True)

resolve_model.EE_PROGRAMS = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.energy_efficiency[model.technology[resource]],
        ordered=True)

resolve_model.FLEXIBLE_LOAD_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.flexible_load[model.technology[resource]],
        ordered=True)

resolve_model.RPS_ELIGIBLE_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.rps_eligible[resource],
        ordered=True)

resolve_model.VARIABLE_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.variable[model.technology[resource]],
        ordered=True)

resolve_model.STORAGE_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.storage[model.technology[resource]],
        ordered=True)

resolve_model.HYDRO_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.hydro[model.technology[resource]],
        ordered=True)

# Set of resources for which installed capacity is specified in MW,
# which includes everything except flexible loads and EVs.
# This is used to define Operational_Capacity, retirements, and calculate fixed costs
resolve_model.RESOURCES_WITH_MW_CAPACITY = Set(
        within=resolve_model.RESOURCES,
        initialize=(resolve_model.RESOURCES - resolve_model.EV_RESOURCES - resolve_model.FLEXIBLE_LOAD_RESOURCES),
        ordered=True)

# New resources
resolve_model.NEW_BUILD_RESOURCES = \
    Set(within=resolve_model.RESOURCES_WITH_MW_CAPACITY,
        initialize=resolve_model.RESOURCES_WITH_MW_CAPACITY,
        filter=lambda model, resource: model.can_build_new[resource],
        ordered=True)

resolve_model.NEW_BUILD_STORAGE_RESOURCES = \
    Set(within=resolve_model.NEW_BUILD_RESOURCES,
        initialize=resolve_model.NEW_BUILD_RESOURCES,
        filter=lambda model, resource: model.storage[model.technology[resource]],
        ordered=True)

# Capacity-limited resources
resolve_model.CAPACITY_LIMITED_RESOURCES = \
    Set(within=resolve_model.NEW_BUILD_RESOURCES,
        initialize=resolve_model.NEW_BUILD_RESOURCES,
        filter=lambda model, resource: model.capacity_limited[resource],
        ordered=True)

resolve_model.capacity_limit_mw = Param(resolve_model.CAPACITY_LIMITED_RESOURCES,
                                        resolve_model.PERIODS,
                                        within=NonNegativeReals)

# only define LOCAL_CAPACITY_RESOURCES within NEW_BUILD_RESOURCES
# because local capacity constraints are on new builds only
resolve_model.LOCAL_CAPACITY_RESOURCES = \
    Set(within=resolve_model.NEW_BUILD_RESOURCES,
        initialize=resolve_model.NEW_BUILD_RESOURCES,
        filter=lambda model, resource: model.local_capacity[resource],
        ordered=True)

resolve_model.LOCAL_CAPACITY_LIMITED_RESOURCES = \
    Set(within=resolve_model.LOCAL_CAPACITY_RESOURCES,
        initialize=resolve_model.LOCAL_CAPACITY_RESOURCES,
        filter=lambda model, resource: model.capacity_limited_local[resource],
        ordered=True)

resolve_model.LOCAL_CAPACITY_STORAGE_RESOURCES = \
    Set(within=resolve_model.LOCAL_CAPACITY_RESOURCES & resolve_model.STORAGE_RESOURCES,
        initialize=resolve_model.LOCAL_CAPACITY_RESOURCES & resolve_model.STORAGE_RESOURCES,
        ordered=True)

# ### Reserve Resource Sets ### #
# Define the relationship between resources and reserve products
resolve_model.RESERVE_RESOURCES = Set(
        within=(resolve_model.RESOURCES - resolve_model.VARIABLE_RESOURCES),
        ordered=True)

resolve_model.can_provide_spin = Param(resolve_model.RESERVE_RESOURCES, within=Boolean)
resolve_model.SPINNING_RESERVE_RESOURCES = \
    Set(within=resolve_model.RESERVE_RESOURCES,
        initialize=resolve_model.RESERVE_RESOURCES,
        filter=lambda model, resource: model.can_provide_spin[resource],
        ordered=True)

resolve_model.can_provide_reg = Param(resolve_model.RESERVE_RESOURCES, within=Boolean)
resolve_model.REGULATION_RESERVE_RESOURCES = \
    Set(within=resolve_model.RESERVE_RESOURCES,
        initialize=resolve_model.RESERVE_RESOURCES,
        filter=lambda model, resource: model.can_provide_reg[resource],
        ordered=True)

resolve_model.can_provide_lf_reserves = Param(resolve_model.RESERVE_RESOURCES, within=Boolean)
resolve_model.LOAD_FOLLOWING_RESERVE_RESOURCES = \
    Set(within=resolve_model.RESERVE_RESOURCES,
        initialize=resolve_model.RESERVE_RESOURCES,
        filter=lambda model, resource: model.can_provide_lf_reserves[resource],
        ordered=True)

resolve_model.contributes_to_min_gen = Param(resolve_model.RESERVE_RESOURCES, within=Boolean)
resolve_model.MINIMUM_GENERATION_RESOURCES = \
    Set(within=resolve_model.RESERVE_RESOURCES,
        initialize=resolve_model.RESERVE_RESOURCES,
        filter=lambda model, resource: model.contributes_to_min_gen[resource],
        ordered=True)

resolve_model.contributes_to_freq_resp_total_req = Param(resolve_model.RESERVE_RESOURCES, within=Boolean)
resolve_model.TOTAL_FREQ_RESP_RESOURCES = \
    Set(within=resolve_model.RESERVE_RESOURCES,
        initialize=resolve_model.RESERVE_RESOURCES,
        filter=lambda model, resource: model.contributes_to_freq_resp_total_req[resource],
        ordered=True)

resolve_model.contributes_to_freq_resp_partial_req = Param(resolve_model.RESERVE_RESOURCES, within=Boolean)
# All resources that contribute to the partial frequency response requirement must also contribute to the total
resolve_model.PARTIAL_FREQ_RESP_RESOURCES = \
    Set(within=resolve_model.RESERVE_RESOURCES,
        initialize=resolve_model.TOTAL_FREQ_RESP_RESOURCES,
        filter=lambda model, resource: model.contributes_to_freq_resp_partial_req[resource],
        ordered=True)

resolve_model.thermal_freq_response_fraction_of_commitment = Param(resolve_model.RESERVE_RESOURCES,
                                                                   within=PercentFraction)


# ### planning reserve margin, transmission zones, and transmission deliverability ### #
resolve_model.include_in_prm = Param(resolve_model.ZONES, within=Boolean)
resolve_model.PRM_RESOURCES = \
    Set(within=resolve_model.RESOURCES - resolve_model.LOAD_ONLY_RESOURCES - resolve_model.FLEXIBLE_LOAD_RESOURCES,
        initialize=resolve_model.RESOURCES - resolve_model.LOAD_ONLY_RESOURCES - resolve_model.FLEXIBLE_LOAD_RESOURCES,
        filter=lambda model, resource: model.include_in_prm[model.zone[resource]],
        ordered=True)

resolve_model.TX_ZONES = Set(ordered=True, doc="transmission cost zones")

# transmission deliverability only applies to new renewable resources that are balanced by zones covered under the PRM,
# so the set TX_DELIVERABILITY_RESOURCES is defined as the intersection (&) of the three relevant sets.
resolve_model.TX_DELIVERABILITY_RESOURCES = \
    resolve_model.NEW_BUILD_RESOURCES & resolve_model.RPS_ELIGIBLE_RESOURCES & resolve_model.PRM_RESOURCES

resolve_model.tx_zone_of_resource = Param(resolve_model.TX_DELIVERABILITY_RESOURCES,
                                          within=resolve_model.TX_ZONES)

resolve_model.import_on_existing_tx = Param(resolve_model.TX_DELIVERABILITY_RESOURCES,
                                            within=Boolean)
resolve_model.import_on_new_tx = Param(resolve_model.TX_DELIVERABILITY_RESOURCES,
                                       within=Boolean)


def prm_variable_renewable_resources_init(model):
    prm_variable_renewable_resources = list()
    for r in model.PRM_RESOURCES:
        if r in model.VARIABLE_RESOURCES:
            if r not in model.TX_DELIVERABILITY_RESOURCES:
                prm_variable_renewable_resources.append(r)
            else:
                # don't include imported variable renewable resources as they will be included elsewhere
                if not model.import_on_new_tx[r] and not model.import_on_existing_tx[r]:
                    prm_variable_renewable_resources.append(r)
    return prm_variable_renewable_resources

resolve_model.PRM_VARIABLE_RENEWABLE_RESOURCES = \
    Set(within=resolve_model.PRM_RESOURCES & resolve_model.VARIABLE_RESOURCES,
        initialize=prm_variable_renewable_resources_init,
        ordered=True)


def prm_firm_capacity_resources_init(model):
    prm_firm_capacity_resources = list()
    for r in model.PRM_RESOURCES:
        if model.firm_capacity[model.technology[r]]:
            if r not in model.TX_DELIVERABILITY_RESOURCES:
                prm_firm_capacity_resources.append(r)
            else:
                # don't include imported firm renewable resources as they will be included elsewhere
                if not model.import_on_new_tx[r] and not model.import_on_existing_tx[r]:
                    prm_firm_capacity_resources.append(r)
    return prm_firm_capacity_resources

resolve_model.PRM_FIRM_CAPACITY_RESOURCES = \
    Set(within=resolve_model.PRM_RESOURCES,
        initialize=prm_firm_capacity_resources_init,
        ordered=True)

resolve_model.PRM_STORAGE_RESOURCES = \
    Set(initialize=resolve_model.PRM_RESOURCES & resolve_model.STORAGE_RESOURCES - resolve_model.PRM_FIRM_CAPACITY_RESOURCES,
        ordered=True)

resolve_model.PRM_HYDRO_RESOURCES = Set(
    initialize=resolve_model.PRM_RESOURCES & resolve_model.HYDRO_RESOURCES,
    ordered=True
)

resolve_model.PRM_CONVENTIONAL_DR_RESOURCES = Set(
    initialize=resolve_model.PRM_RESOURCES & resolve_model.CONVENTIONAL_DR_RESOURCES,
    ordered=True
)

resolve_model.PRM_NQC_RESOURCES = (
    resolve_model.PRM_FIRM_CAPACITY_RESOURCES |
    resolve_model.PRM_STORAGE_RESOURCES
)

resolve_model.PRM_EE_PROGRAMS = \
    Set(initialize=resolve_model.PRM_RESOURCES & resolve_model.EE_PROGRAMS,
        ordered=True)


# Validation rule for resources that can be retired
# Rule is necessary because subsequent code can handle retirements for some resources but not others
# Storage resources can't be retired because doing so would require retiring energy and power capacity
# and the current code only retires power capacity.
# TX_Deliverability_Resources (new renewable resources) can't be retired
# because the retirement logic hasn't been extended to transmission deliverability.

def can_retire_resources_validation_rule(model, resource):
    if resource in model.THERMAL_RESOURCES - model.STORAGE_RESOURCES - model.TX_DELIVERABILITY_RESOURCES:
        return True
    else:
        return False

resolve_model.CAN_RETIRE_RESOURCES = \
    Set(within=resolve_model.RESOURCES,
        initialize=resolve_model.RESOURCES,
        filter=lambda model, resource: model.can_retire[resource],
        ordered=True, validate=can_retire_resources_validation_rule)

resolve_model.CAN_RETIRE_RESOURCES_NEW = \
    Set(within=resolve_model.CAN_RETIRE_RESOURCES & resolve_model.NEW_BUILD_RESOURCES,
        initialize=resolve_model.CAN_RETIRE_RESOURCES & resolve_model.NEW_BUILD_RESOURCES,
        ordered=True)


##############################################################################
# ############################### PARAMETERS ############################### #
##############################################################################

# ##### Technology params ##### #

# Variable costs is simply O&M and does not include fuel costs
resolve_model.variable_cost_per_mwh = Param(resolve_model.TECHNOLOGIES, within=NonNegativeReals)

# ### Storage ### #
resolve_model.charging_efficiency = Param(resolve_model.STORAGE_TECHNOLOGIES, within=PercentFraction)
resolve_model.discharging_efficiency = Param(resolve_model.STORAGE_TECHNOLOGIES, within=PercentFraction)
resolve_model.min_duration_h = Param(resolve_model.STORAGE_TECHNOLOGIES, within=NonNegativeReals)

# # Thermal and fuel # #
resolve_model.fuel = Param(resolve_model.THERMAL_TECHNOLOGIES, within=resolve_model.FUELS)
resolve_model.fuel_burn_slope_mmbtu_per_mwh = Param(resolve_model.THERMAL_TECHNOLOGIES, within=NonNegativeReals)
resolve_model.fuel_burn_intercept_mmbtu_per_hr = Param(resolve_model.THERMAL_TECHNOLOGIES, within=NonNegativeReals)
resolve_model.tco2_per_mmbtu = Param(resolve_model.FUELS, within=NonNegativeReals)
# can this fuel be blended with biogas?
resolve_model.can_blend_with_pipeline_biogas = Param(resolve_model.FUELS, within=Boolean)

resolve_model.PIPELINE_BIOGAS_RESOURCES = \
    Set(within=resolve_model.THERMAL_RESOURCES,
        initialize=resolve_model.THERMAL_RESOURCES,
        filter=lambda model, resource: model.can_blend_with_pipeline_biogas[model.fuel[model.technology[resource]]],
        ordered=True)


# # Dispatchable # #
resolve_model.min_stable_level_fraction = Param(resolve_model.DISPATCHABLE_TECHNOLOGIES, within=PercentFraction)
resolve_model.ramp_rate_fraction = Param(resolve_model.DISPATCHABLE_TECHNOLOGIES, within=NonNegativeReals)

# Resolve cannot currently model sub-hourly, so make sure that the min up and down times are at least one hour
# by defining params within PositiveIntegers.
resolve_model.min_down_time_hours = Param(
    resolve_model.DISPATCHABLE_TECHNOLOGIES,
    within=PositiveIntegers
)
resolve_model.min_up_time_hours = Param(
    resolve_model.DISPATCHABLE_TECHNOLOGIES,
    within=PositiveIntegers
)
resolve_model.unit_size_mw = Param(resolve_model.DISPATCHABLE_TECHNOLOGIES, within=NonNegativeReals)
resolve_model.startup_cost_per_mw = Param(resolve_model.DISPATCHABLE_TECHNOLOGIES, within=NonNegativeReals)
resolve_model.shutdown_cost_per_mw = Param(resolve_model.DISPATCHABLE_TECHNOLOGIES, within=NonNegativeReals)
resolve_model.start_fuel_mmbtu_per_mw = Param(resolve_model.DISPATCHABLE_TECHNOLOGIES, within=NonNegativeReals)



def define_full_load_heat_rate(model, thermal_resource):
    """
    Calculate the full load heat rate for each thermal tech.
    Currently used for pipeline biogas and (in results reporting) production cost inputs
    :param model:
    :param thermal_resource:
    :return:
    """
    if thermal_resource in model.DISPATCHABLE_RESOURCES:
        full_load_heat_rate = \
            (model.fuel_burn_intercept_mmbtu_per_hr[model.technology[thermal_resource]]
             + model.unit_size_mw[model.technology[thermal_resource]]
             * model.fuel_burn_slope_mmbtu_per_mwh[model.technology[thermal_resource]]) \
            / model.unit_size_mw[model.technology[thermal_resource]]
    else:
        full_load_heat_rate = model.fuel_burn_slope_mmbtu_per_mwh[model.technology[thermal_resource]]

    return full_load_heat_rate

resolve_model.full_load_heat_rate_mmbtu_per_mwh = Param(resolve_model.THERMAL_RESOURCES,
                                                        rule=define_full_load_heat_rate)


def define_min_stable_level_heat_rate(model, thermal_resource):
    """
    Calculate the min stable level heat rate for each thermal tech.
    Currently used for pipeline biogas and (in results reporting) production cost inputs
    :param model:
    :param thermal_resource:
    :return:
    """

    if thermal_resource in model.DISPATCHABLE_RESOURCES:
        min_stable_level = model.min_stable_level_fraction[model.technology[thermal_resource]]
        if min_stable_level == 0:
            min_stable_level_heat_rate = 0
        else:
            min_capacity_mw = min_stable_level * model.unit_size_mw[model.technology[thermal_resource]]

            min_stable_level_heat_rate = \
                (model.fuel_burn_intercept_mmbtu_per_hr[model.technology[thermal_resource]]
                 + min_capacity_mw
                 * model.fuel_burn_slope_mmbtu_per_mwh[model.technology[thermal_resource]]) \
                / min_capacity_mw
    else:
        min_stable_level_heat_rate = model.fuel_burn_slope_mmbtu_per_mwh[model.technology[thermal_resource]]

    return min_stable_level_heat_rate

resolve_model.min_stable_level_heat_rate_mmbtu_per_mwh = Param(resolve_model.THERMAL_RESOURCES,
                                                               rule=define_min_stable_level_heat_rate)


# if the ramp rate of the resource is less than the unit's full capacity,
# write ramp constraints via the set DISPATCHABLE_RAMP_LIMITED_RESOURCES
resolve_model.DISPATCHABLE_RAMP_LIMITED_RESOURCES = \
    Set(within=resolve_model.DISPATCHABLE_RESOURCES,
        initialize=resolve_model.DISPATCHABLE_RESOURCES,
        filter=lambda model, resource: model.ramp_rate_fraction[model.technology[resource]] < 1,
        ordered=True)

# ##### Resource params ##### #

def planned_installed_capacity_validate(model, planned_installed_capacity, resource, period):
    """
    Currently any resource in TX_DELIVERABILITY_RESOURCES can't have planned capacity
    because that capacity is not subtracted from the deliverable and energy only capacity limits
    This check ensures that planned_installed_capacity_mw = 0 in all periods for these resources
    :param model:
    :param planned_installed_capacity:
    :param resource:
    :param period: not needed in statement below because the validation must pass for all periods
    :return:
    """
    if resource not in model.TX_DELIVERABILITY_RESOURCES:
        return True
    else:
        return planned_installed_capacity == 0

resolve_model.planned_installed_capacity_mw = \
    Param(resolve_model.RESOURCES_WITH_MW_CAPACITY,
          resolve_model.PERIODS,
          within=NonNegativeReals,
          validate=planned_installed_capacity_validate)


def min_operational_planned_capacity_validate(model, min_operational_planned_capacity, resource, period):
    """
    If a resource can't be retired then make sure that there is a zero value for min_operational_planned_capacity_mw
    because any value would not be meaningful
    If a resource can be retired, make sure that the minimum amount of planned capacity
    that the model must keep operational in a period is less than or equal to the planned capacity
    """
    if resource not in model.CAN_RETIRE_RESOURCES:
        return min_operational_planned_capacity == 0
    else:
        return min_operational_planned_capacity <= model.planned_installed_capacity_mw[resource, period]


resolve_model.min_operational_planned_capacity_mw = \
    Param(resolve_model.RESOURCES_WITH_MW_CAPACITY,
          resolve_model.PERIODS,
          within=NonNegativeReals,
          validate=min_operational_planned_capacity_validate)


# Calculate planned additions for resources
def calculate_planned_capacity_addition_init(model, resource, period):
    previous_period = find_prev_period(model, period)

    if period == model.first_period:
        capacity_addition = model.planned_installed_capacity_mw[resource, period]
    elif model.planned_installed_capacity_mw[resource, period] > \
            model.planned_installed_capacity_mw[resource, previous_period]:
        capacity_addition = model.planned_installed_capacity_mw[resource, period] - \
                            model.planned_installed_capacity_mw[resource, previous_period]
    else:
        capacity_addition = 0

    return capacity_addition

resolve_model.planned_addition_mw = \
    Param(resolve_model.RESOURCES_WITH_MW_CAPACITY,
          resolve_model.PERIODS,
          within=NonNegativeReals,
          initialize=calculate_planned_capacity_addition_init)


# Calculate planned subtractions (planned retirements) for resources.
# If the model can retire the resource, at least this amount of capacity will be retired before or in the period
def calculate_planned_capacity_subtraction_init(model, resource, period):
    previous_period = find_prev_period(model, period)

    if period == model.first_period:
        capacity_subtraction = 0
    elif model.planned_installed_capacity_mw[resource, period] < \
            model.planned_installed_capacity_mw[resource, previous_period]:
        capacity_subtraction = model.planned_installed_capacity_mw[resource, previous_period] - \
                            model.planned_installed_capacity_mw[resource, period]
    else:
        capacity_subtraction = 0

    return capacity_subtraction


resolve_model.planned_subtraction_mw = \
    Param(resolve_model.RESOURCES_WITH_MW_CAPACITY,
          resolve_model.PERIODS,
          within=NonNegativeReals,
          initialize=calculate_planned_capacity_subtraction_init)


# Parameters tracking cumulative planned capacity additions for every period
def cumulative_planned_capacity_additions_init(model, resource, period):
    cumulative_planned_capacity_additions = float()
    for p in model.PERIODS:
        if p <= period:
            cumulative_planned_capacity_additions += model.planned_addition_mw[resource, p]

    return cumulative_planned_capacity_additions

resolve_model.cumulative_planned_capacity_additions_mw = \
    Param(resolve_model.RESOURCES_WITH_MW_CAPACITY, resolve_model.PERIODS,
          within=NonNegativeReals, initialize=cumulative_planned_capacity_additions_init)


# Parameters tracking cumulative planned capacity subtractions (forced retirements) for every period
def cumulative_planned_capacity_subtractions_init(model, resource, period):
    cumulative_planned_capacity_subtractions = float()
    for p in model.PERIODS:
        if p <= period:
            cumulative_planned_capacity_subtractions += model.planned_subtraction_mw[resource, p]

    return cumulative_planned_capacity_subtractions

resolve_model.cumulative_planned_capacity_subtractions_mw = \
    Param(resolve_model.RESOURCES_WITH_MW_CAPACITY, resolve_model.PERIODS,
          within=NonNegativeReals, initialize=cumulative_planned_capacity_subtractions_init)


# Fixed O&M costs for planned capacity. Can vary by period.
resolve_model.planned_capacity_fixed_o_and_m_dollars_per_kw_yr = Param(resolve_model.RESOURCES_WITH_MW_CAPACITY,
                                                                       resolve_model.PERIODS,
                                                                       within=NonNegativeReals)

# ### New build only ### #
resolve_model.min_cumulative_new_build_mw = Param(resolve_model.NEW_BUILD_RESOURCES, resolve_model.PERIODS,
                                                  within=NonNegativeReals)

# New resource annualized capital cost
resolve_model.capital_cost_per_kw_yr = Param(resolve_model.NEW_BUILD_RESOURCES,
                                             resolve_model.VINTAGES,
                                             within=NonNegativeReals)

# New resource annual Fixed O&M costs, which can vary by vintage
resolve_model.new_capacity_fixed_o_and_m_dollars_per_kw_yr = Param(resolve_model.NEW_BUILD_RESOURCES,
                                                                   resolve_model.VINTAGES,
                                                                   within=NonNegativeReals)

# ### Storage ### #
resolve_model.planned_storage_energy_capacity_mwh = Param(resolve_model.STORAGE_RESOURCES, resolve_model.PERIODS,
                                                          within=NonNegativeReals)

resolve_model.planned_storage_energy_capacity_fixed_o_and_m_dollars_per_kwh_yr = \
    Param(resolve_model.STORAGE_RESOURCES,
          resolve_model.PERIODS,
          within=NonNegativeReals)

# Define only for storage resources with new build allowed
resolve_model.energy_storage_cost_per_kwh_yr = Param(resolve_model.NEW_BUILD_STORAGE_RESOURCES,
                                                     resolve_model.VINTAGES,
                                                     within=NonNegativeReals)

resolve_model.new_energy_capacity_fixed_o_and_m_dollars_per_kwh_yr = \
    Param(resolve_model.NEW_BUILD_STORAGE_RESOURCES,
          resolve_model.VINTAGES,
          within=NonNegativeReals)

# ### Maintenance ### #
resolve_model.maintenance_derate = Param(
    resolve_model.RESOURCES,
    resolve_model.TIMEPOINTS,
    within=PercentFraction,
    default=1.0
)

# ### Renewables ### #
# shape is the hourly capacity factor of variable renewables
resolve_model.shape = Param(resolve_model.VARIABLE_RESOURCES, resolve_model.DAYS, resolve_model.HOURS_OF_DAY,
                            within=PercentFraction)
# resource-specific limitations on the ability to curtail/dispatch variable renewables
resolve_model.curtailable = Param(resolve_model.VARIABLE_RESOURCES, within=Boolean)

# define the set of variable renewable resources that can be curtailed
resolve_model.CURTAILABLE_VARIABLE_RESOURCES = \
    Set(within=resolve_model.VARIABLE_RESOURCES,
        initialize=resolve_model.VARIABLE_RESOURCES,
        filter=lambda model, resource: model.curtailable[resource],
        ordered=True)

# ### Hydro ### #
resolve_model.hydro_daily_energy_fraction = Param(
    resolve_model.HYDRO_RESOURCES, resolve_model.DAYS,
    within=PercentFraction)
resolve_model.hydro_min_gen_fraction = Param(resolve_model.HYDRO_RESOURCES, resolve_model.DAYS, within=PercentFraction)
resolve_model.hydro_max_gen_fraction = Param(resolve_model.HYDRO_RESOURCES, resolve_model.DAYS, within=PercentFraction)
# should hydro spill be allowed?
resolve_model.allow_hydro_spill = Param(within=Boolean)

# this assumes at least 1-hour ramps will be constrained
resolve_model.max_hydro_ramp_duration_to_constrain = Param(within=PositiveIntegers)

# The set of hydro resources for which multi-hour ramping limits will be defined.
resolve_model.RAMP_CONSTRAINED_HYDRO_RESOURCES = Set(within=resolve_model.HYDRO_RESOURCES, ordered=True)


def hydro_ramp_durations_init(model):
    durations = list()
    for duration in range(1, model.max_hydro_ramp_duration_to_constrain + 1):
        durations.append(duration)
    return durations

resolve_model.HYDRO_RAMP_DURATIONS = Set(within=PositiveIntegers, initialize=hydro_ramp_durations_init, ordered=True)


resolve_model.hydro_ramp_up_limit_fraction = Param(resolve_model.RAMP_CONSTRAINED_HYDRO_RESOURCES,
                                                   resolve_model.HYDRO_RAMP_DURATIONS,
                                                   within=PercentFraction)
resolve_model.hydro_ramp_down_limit_fraction = Param(resolve_model.RAMP_CONSTRAINED_HYDRO_RESOURCES,
                                                     resolve_model.HYDRO_RAMP_DURATIONS,
                                                     within=PercentFraction)


# ### Transmission ### #


# ##### Transmission params ##### #
resolve_model.min_flow_planned_mw = Param(resolve_model.TRANSMISSION_LINES, within=Reals)
resolve_model.max_flow_planned_mw = Param(resolve_model.TRANSMISSION_LINES, within=Reals)
resolve_model.ramp_constrained = Param(resolve_model.TRANSMISSION_LINES, within=Boolean)
resolve_model.max_intertie_ramp_duration_to_constrain = Param(within=PositiveIntegers)
resolve_model.new_build_tx_flag = Param(resolve_model.TRANSMISSION_LINES, within=Boolean)

# Hurdle rate costs represent the cost to move power along each direction of a transmission line.
# Must be non-negative.
resolve_model.positive_direction_hurdle_rate_per_mw = Param(resolve_model.TRANSMISSION_LINES,
                                                            resolve_model.PERIODS, within=NonNegativeReals)
resolve_model.negative_direction_hurdle_rate_per_mw = Param(resolve_model.TRANSMISSION_LINES,
                                                            resolve_model.PERIODS, within=NonNegativeReals)


resolve_model.TRANSMISSION_LINES_NEW = Set(
    within=resolve_model.TRANSMISSION_LINES,
    initialize=resolve_model.TRANSMISSION_LINES,
    filter=lambda model, line: model.new_build_tx_flag[line],
    ordered=True)

resolve_model.RAMP_CONSTRAINED_TRANSMISSION_LINES = \
    Set(within=resolve_model.TRANSMISSION_LINES,
        initialize=resolve_model.TRANSMISSION_LINES,
        filter=lambda model, line: model.ramp_constrained[line],
        ordered=True)


if resolve_model.transmission_ramp_limit:
    def flow_ramp_durations_init(model):
        durations = list()
        for duration in range(1, model.max_intertie_ramp_duration_to_constrain + 1):
            durations.append(duration)
        return durations

    resolve_model.INTERTIE_FLOW_RAMP_DURATIONS = Set(
        within=PositiveIntegers,
        initialize=flow_ramp_durations_init,
        ordered=True)

    resolve_model.flow_ramp_up_limit_fraction = Param(
        resolve_model.RAMP_CONSTRAINED_TRANSMISSION_LINES,
        resolve_model.INTERTIE_FLOW_RAMP_DURATIONS,
        within=PercentFraction)

    resolve_model.flow_ramp_down_limit_fraction = Param(
        resolve_model.RAMP_CONSTRAINED_TRANSMISSION_LINES,
        resolve_model.INTERTIE_FLOW_RAMP_DURATIONS,
        within=PercentFraction)

# ## Transmission cost and deliverability params ## #
resolve_model.tx_deliverability_cost_per_mw_yr = Param(resolve_model.TX_ZONES, within=NonNegativeReals)
resolve_model.fully_deliverable_new_tx_threshold_mw = Param(resolve_model.TX_ZONES, within=NonNegativeReals)
resolve_model.energy_only_tx_limit_mw = Param(resolve_model.TX_ZONES, within=NonNegativeReals)


def tx_import_fraction_validate(model, tx_import_fraction, resource):
    """
    Make sure that a new renewable imported on transmission
    has a non-zero tx_import_capacity_fraction and that other renewables have tx_import_capacity_fraction = 0
    :param model:
    :param tx_import_fraction:
    :param resource:
    :return:
    """
    if model.import_on_new_tx[resource] or model.import_on_existing_tx[resource]:
        return tx_import_fraction >= 0
    else:
        return tx_import_fraction == 0

resolve_model.tx_import_capacity_fraction = Param(resolve_model.TX_DELIVERABILITY_RESOURCES,
                                                  within=PercentFraction,
                                                  validate=tx_import_fraction_validate)


# ## New tranmsmission line subset and params ## #
if resolve_model.allow_tx_build:
    # Params defining minimum and maximum available build decisions for each period for new and existing paths
    resolve_model.max_tx_build_mw = Param(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIODS,
        within=NonNegativeReals)

    resolve_model.min_tx_build_mw = Param(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIODS,
        within=NonNegativeReals)

    # Cost params
    resolve_model.new_tx_fixed_cost_per_mw_yr = Param(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIODS,
        within=NonNegativeReals)

    resolve_model.new_tx_fixed_cost_annualized_per_yr = Param(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIODS,
        within=NonNegativeReals)

    resolve_model.new_build_local_capacity_contribution = Param(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIODS,
        within=PercentFraction)

    # Build variables
    resolve_model.New_Tx_Period_Installed_Capacity_MW = Var(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIODS,
        within=NonNegativeReals)

    def new_tx_period_vintage_installed_capacity_mw(model, line, period, vintage):
        return model.New_Tx_Period_Installed_Capacity_MW[line, vintage]

    resolve_model.New_Tx_Period_Vintage_Installed_Capacity_MW = Expression(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIOD_VINTAGES,
        rule=new_tx_period_vintage_installed_capacity_mw)

    def new_tx_total_installed_capacity_mw(model, line, period):
        return sum(model.New_Tx_Period_Installed_Capacity_MW[line, vintage]
                   for vintage in model.VINTAGES if vintage <= period)

    resolve_model.New_Tx_Total_Installed_Capacity_MW = Expression(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIODS,
        rule=new_tx_total_installed_capacity_mw)

    def new_tx_local_capacity_contribution_rule(model, line, period):
        return (model.new_build_local_capacity_contribution[line, period] *
                model.New_Tx_Total_Installed_Capacity_MW[line, period])

    resolve_model.New_Tx_Local_Capacity_Contribution_MW = Expression(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIODS,
        rule=new_tx_local_capacity_contribution_rule)

    # Build constraints
    def new_tx_build_max_build(model, line, period):
        return (model.New_Tx_Total_Installed_Capacity_MW[line, period] <= model.max_tx_build_mw[line, period])

    resolve_model.New_Tx_Max_Build = Constraint(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIODS,
        rule=new_tx_build_max_build)

    def new_tx_build_min_build(model, line, period):
        return (model.New_Tx_Total_Installed_Capacity_MW[line, period] >= model.min_tx_build_mw[line, period])

    resolve_model.New_Tx_Min_Build = Constraint(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIODS,
        rule=new_tx_build_min_build)

    # Build cost expression
    def new_tx_build_cost(model, l, p, v):
        return model.new_tx_fixed_cost_per_mw_yr[l, v] * model.New_Tx_Period_Vintage_Installed_Capacity_MW[l, p, v]

    resolve_model.New_Tx_Period_Vintage_Build_Cost = Expression(
        resolve_model.TRANSMISSION_LINES_NEW, resolve_model.PERIOD_VINTAGES,
        rule=new_tx_build_cost)

# ##### Flexible loads ##### #
# ##### Flexible loads ##### #

# ### Electric Vehicles (EVs) ### #
if resolve_model.include_electric_vehicles:

    # EV charging efficiency
    resolve_model.ev_charging_efficiency = Param(resolve_model.EV_RESOURCES, within=PercentFraction)

    # Total energy capacity of EV resources
    resolve_model.total_ev_battery_energy_capacity_mwh = Param(resolve_model.EV_RESOURCES, resolve_model.PERIODS,
                                                               within=NonNegativeReals)

    # Minimum energy that must be available in EV batteries
    resolve_model.minimum_energy_in_ev_batteries_mwh = Param(resolve_model.EV_RESOURCES, resolve_model.PERIODS,
                                                             within=NonNegativeReals)

    # How much energy is used up driving in each hour
    resolve_model.driving_energy_demand_mw = Param(resolve_model.EV_RESOURCES, resolve_model.TIMEPOINTS,
                                                   within=NonNegativeReals)

    # Rate at which EV resources can charge (based on how much EV battery capacity is plugged in)
    resolve_model.ev_battery_plugged_in_capacity_mw = Param(resolve_model.EV_RESOURCES, resolve_model.TIMEPOINTS,
                                                            within=NonNegativeReals)

# ### Hydrogen Electrolysis ### #
# Note: values here should be synced with the hydrogen electrolysis installed capacity
if resolve_model.include_hydrogen_electrolysis:

    # Minimum hydrogen electrolysis load, specified by period and day
    resolve_model.hydrogen_electrolysis_load_min_mw = Param(resolve_model.HYDROGEN_ELECTROLYSIS_RESOURCES,
                                                            resolve_model.PERIODS,
                                                            resolve_model.DAYS,
                                                            within=NonNegativeReals)
    # Daily hydrogen electrolysis load, specified by period and day
    resolve_model.hydrogen_electrolysis_load_daily_mwh = Param(resolve_model.HYDROGEN_ELECTROLYSIS_RESOURCES,
                                                               resolve_model.PERIODS,
                                                               resolve_model.DAYS,
                                                               within=NonNegativeReals)

# ### Flexible Demand Response Shift Loads ### #
if resolve_model.include_flexible_load:
    resolve_model.min_cumulative_new_flexible_load_shift_mwh = Param(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                                     resolve_model.PERIODS,
                                                                     within=NonNegativeReals)
    resolve_model.max_flexible_load_shift_potential_mwh = Param(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                                resolve_model.PERIODS,
                                                                within=NonNegativeReals)
    resolve_model.shift_load_down_potential_factor = Param(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                           resolve_model.TIMEPOINTS,
                                                           within=PercentFraction)
    resolve_model.shift_load_up_potential_factor = Param(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                         resolve_model.TIMEPOINTS,
                                                         within=PercentFraction)

    # Flexible Load Cost Curve Params
    resolve_model.FLEXIBLE_LOAD_COST_CURVE_INDEX = Set(ordered=True, doc="flexible load cost curve index")
    resolve_model.flexible_load_cost_curve_slope = Param(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                         resolve_model.FLEXIBLE_LOAD_COST_CURVE_INDEX,
                                                         resolve_model.PERIODS,
                                                         within=NonNegativeReals)
    resolve_model.flexible_load_cost_curve_intercept = Param(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                             resolve_model.FLEXIBLE_LOAD_COST_CURVE_INDEX,
                                                             resolve_model.PERIODS,
                                                             within=NonPositiveReals)

# #### Conventional (shed) demand response #### #
resolve_model.conventional_dr_availability_hours_per_year = \
    Param(resolve_model.CONVENTIONAL_DR_RESOURCES,
          resolve_model.PERIODS,
          within=NonNegativeReals)

resolve_model.conventional_dr_daily_capacity_factor = Param(
    resolve_model.CONVENTIONAL_DR_RESOURCES,
    resolve_model.PERIODS,
    within=PercentFraction
)

# ##### System params ##### #

# ### Load ### #
resolve_model.input_load_mw = Param(resolve_model.ZONES, resolve_model.TIMEPOINTS, within=NonNegativeReals)
resolve_model.unserved_energy_penalty_per_mw = Param(within=NonNegativeReals)
resolve_model.allow_unserved_energy = Param(within=Boolean)
resolve_model.overgen_penalty_per_mw = Param(within=NonNegativeReals)
resolve_model.spin_violation_penalty_per_mw = Param(within=NonNegativeReals)
resolve_model.upward_lf_reserve_violation_penalty_per_mw = Param(within=NonNegativeReals)
resolve_model.downward_lf_reserve_violation_penalty_per_mw = Param(within=NonNegativeReals)
resolve_model.upward_reg_violation_penalty_per_mw = Param(within=NonNegativeReals)
resolve_model.downward_reg_violation_penalty_per_mw = Param(within=NonNegativeReals)
resolve_model.reserve_timeframe_fraction_of_hour = Param(within=PercentFraction)

# ### RPS ### #
resolve_model.rps_nonmodeled_mwh = Param(resolve_model.PERIODS, within=NonNegativeReals)
# should storage losses be counted as renewable curtailment in the RPS constraint?
resolve_model.count_storage_losses_as_rps_curtailment = Param(within=Boolean)
# Require overbuild of renewables to meet RPS requirements?
resolve_model.require_overbuild = Param(within=Boolean)
# should resolve be able to optimize banking of rps credits?
resolve_model.optimize_rps_banking = Param(within=Boolean)
# as a fraction of the RPS target, what is the limit on unbundled RECs?
resolve_model.rps_unbundled_fraction_limit = Param(resolve_model.PERIODS, within=PercentFraction)
# use for adjusting RPS target based on EE adoption
# retail sales
resolve_model.retail_sales_mwh = Param(resolve_model.PERIODS, within=NonNegativeReals)
# use to calculate rps target: RPS target as a percentage of retail sales
resolve_model.rps_fraction_of_retail_sales = Param(resolve_model.PERIODS, within=NonNegativeReals)
# should each zone's demand and storage losses be included in the RPS constraint?
resolve_model.include_in_rps_target = Param(resolve_model.ZONES, within=Boolean)


resolve_model.RPS_ZONES = \
    Set(within=resolve_model.ZONES,
        initialize=resolve_model.ZONES,
        filter=lambda model, zone: model.include_in_rps_target[zone],
        ordered=True)


def rps_starting_input_validate(model, starting_bank):
    """
    The starting_rps_bank_mwh param is only used with optimized banking
    so check that this param is zero unless optimize_rps_banking is turned on
    :param model:
    :param starting_bank:
    :return:
    """
    if not model.optimize_rps_banking:
        return starting_bank == 0
    else:
        return starting_bank >= 0

# if optimized banking is allowed, at what level should the bank start?
resolve_model.starting_rps_bank_mwh = Param(within=NonNegativeReals,
                                            validate=rps_starting_input_validate)


def rps_planned_spend_input_validate(model, planned_spend, period):
    """
    The rps_bank_planned_spend_mwh param cannot be used with optimized banking
    :param model:
    :param planned_spend:
    :param period:
    :return:
    """
    if model.optimize_rps_banking:
        return planned_spend == 0
    else:
        return planned_spend >= 0

# if optimized banking isn't allowed, is there any planned spending of existing banks?
resolve_model.rps_bank_planned_spend_mwh = Param(resolve_model.PERIODS,
                                                 within=NonNegativeReals,
                                                 validate=rps_planned_spend_input_validate)


def curtailment_cost_zone_validate(model, curtailment_cost, zone, period):
    """
    # Curtailment cost should be zero if the zone is included in an RPS target
    # because in this case the cost of curtailment will be calculated endogenously
    :param model:
    :param curtailment_cost:
    :param zone:
    :param period:
    :return:
    """
    if zone in model.RPS_ZONES and model.rps_fraction_of_retail_sales[period] > 0:
        return curtailment_cost == 0
    else:
        return curtailment_cost >= 0

# cost of curtailment - the exogenously assumed cost at which different contract zones
# would be willing to curtail their variable renewable generation
resolve_model.curtailment_cost_per_mwh = Param(resolve_model.ZONES,
                                               resolve_model.PERIODS,
                                               within=NonNegativeReals,
                                               validate=curtailment_cost_zone_validate)


def define_resource_contract(model, resource):
    """
    Used for results reporting only. - backwards compatible.
    :param model:
    :param resource:
    :return:
    """
    # as a placeholder for unbundled RPS resources
    # (resources that are contracted to the RPS zone but are balanced elsewhere),
    # return the first RPS Zone from the set of RPS Zones (element 1)
    if resource in model.RPS_ELIGIBLE_RESOURCES and model.zone[resource] not in model.RPS_ZONES:
        return model.RPS_ZONES[1]
    else:
        return model.zone[resource]

resolve_model.contract = Param(resolve_model.RESOURCES,
                               rule=define_resource_contract)


def define_zone_contract_combinations_init(model):
    """
    Used for results reporting only. - backwards compatible.
    :param model:
    :return:
    """
    zone_contract_combinations = list()
    for resource in model.RESOURCES:
        zone_contract_combinations.append((model.zone[resource], model.contract[resource]))
    zone_contract_combinations = sorted(list(set(zone_contract_combinations)))

    return zone_contract_combinations

resolve_model.ZONE_CONTRACT_COMBINATIONS = Set(dimen=2,
                                               initialize=define_zone_contract_combinations_init,
                                               ordered=True)


# how much biogas (in MMBtu) is available in the natural gas pipeline?
resolve_model.pipeline_biogas_available_mmbtu_per_year = Param(resolve_model.PERIODS, within=NonNegativeReals)
# At what incremental cost ($/MMBtu) is biogas available to be blended?
# Should be nonnegative.
resolve_model.incremental_pipeline_biogas_cost_per_mmbtu = Param(resolve_model.PERIODS, within=NonNegativeReals)

# ### Reserves ### #
# zones for which the load is assumed to be covered under load following requirements
resolve_model.include_in_load_following = Param(resolve_model.ZONES, within=Boolean)
resolve_model.LOAD_FOLLOWING_ZONES = \
    Set(within=resolve_model.ZONES,
        initialize=resolve_model.ZONES,
        filter=lambda model, zone: model.include_in_load_following[zone],
        ordered=True)

resolve_model.LOAD_FOLLOWING_ZONE_CURTAILABLE_RESOURCES = Set(
    within=resolve_model.CURTAILABLE_VARIABLE_RESOURCES,
    initialize=resolve_model.CURTAILABLE_VARIABLE_RESOURCES,
    filter=lambda model, resource: model.zone[resource] in model.LOAD_FOLLOWING_ZONES)

resolve_model.spin_reserve_fraction_of_load = Param(resolve_model.ZONES, within=PercentFraction)
resolve_model.upward_reg_req = Param(resolve_model.TIMEPOINTS, within=NonNegativeReals)
resolve_model.downward_reg_req = Param(resolve_model.TIMEPOINTS, within=NonNegativeReals)
resolve_model.upward_lf_reserve_req = Param(resolve_model.TIMEPOINTS, within=NonNegativeReals)
resolve_model.downward_lf_reserve_req = Param(resolve_model.TIMEPOINTS, within=NonNegativeReals)
resolve_model.min_gen_committed_mw = Param(resolve_model.TIMEPOINTS, within=NonNegativeReals)
resolve_model.freq_resp_total_req_mw = Param(resolve_model.TIMEPOINTS, within=NonNegativeReals)
resolve_model.freq_resp_partial_req_mw = Param(resolve_model.TIMEPOINTS, within=NonNegativeReals)

resolve_model.resource_upward_lf_req = Param(
    resolve_model.VARIABLE_RESOURCES,
    resolve_model.DAYS,
    resolve_model.HOURS_OF_DAY,
    within=NonNegativeReals)

resolve_model.resource_downward_lf_req = Param(
    resolve_model.VARIABLE_RESOURCES,
    resolve_model.DAYS,
    resolve_model.HOURS_OF_DAY,
    within=NonNegativeReals)

# These parameters characterize subhourly reserve mileage,
# the amount of energy dispatched within the hour per unit of reserve provision.
resolve_model.reg_dispatch_fraction = Param(within=PercentFraction)
resolve_model.lf_reserve_dispatch_fraction = Param(within=PercentFraction)

# What fraction of curtailable variable renewable generation is available for load following reserves?
# Currently variable renewables are not assumed to provide regulation
resolve_model.var_rnw_available_for_lf_reserves = Param(within=PercentFraction)

# What fraction of the downward load following reserve requirement can be met with renewables?
resolve_model.max_var_rnw_lf_reserves = Param(within=PercentFraction)

# ### Fuel prices ### #
resolve_model.fuel_price_per_mmbtu = Param(resolve_model.FUELS,
                                           resolve_model.PERIODS,
                                           resolve_model.MONTHS,
                                           within=NonNegativeReals)


# ##### Timekeeping params ##### #
resolve_model.discount_factor = Param(resolve_model.PERIODS, within=NonNegativeReals)
resolve_model.years_in_period = Param(resolve_model.PERIODS, within=NonNegativeReals)
resolve_model.day_weight = Param(resolve_model.DAYS, within=NonNegativeReals)
resolve_model.hours_per_year = Param(initialize=8760.0)
resolve_model.timepoints_per_day = Param(initialize=24)

# ##### Tuning params ##### #
# Tuning params remove degeneracies or rounding errors in the solution
# These should be small enough to not change decisions with non-zero cost
# but large enough to not cause numerical problems
resolve_model.local_capacity_tuning_cost = Param(initialize=10 ** -4)
resolve_model.ramp_relax = Param(initialize=10 ** -4)
resolve_model.favor_deliverability_tuning_cost = Param(initialize=1)

# ##### Planning Reserve Margin params ##### #
resolve_model.planning_reserve_margin = Param(resolve_model.PERIODS, within=PercentFraction)
resolve_model.prm_peak_load_mw = Param(resolve_model.PERIODS, within=NonNegativeReals)
resolve_model.prm_annual_load_mwh = Param(resolve_model.PERIODS, within=NonNegativeReals)
resolve_model.prm_planned_import_capacity_mw = Param(resolve_model.PERIODS, within=NonNegativeReals)
resolve_model.prm_import_resource_capacity_adjustment_mw = Param(resolve_model.PERIODS, within=Reals)
resolve_model.net_qualifying_capacity_fraction = Param(resolve_model.PRM_NQC_RESOURCES,
                                                       within=PercentFraction)
resolve_model.elcc_hours = Param(within=PositiveReals)
resolve_model.allow_unspecified_import_contribution = Param(resolve_model.PERIODS, within=Boolean)


# ELCC surface facets and coefficients - surface must be convex
resolve_model.ELCC_SURFACE_FACETS = Set(ordered=True)
# Solar and wind coefficients have units of (fraction of 1-in-2 peak)/(fraction of annual load)
resolve_model.solar_coefficient = Param(resolve_model.ELCC_SURFACE_FACETS, within=NonNegativeReals)
resolve_model.wind_coefficient = Param(resolve_model.ELCC_SURFACE_FACETS, within=NonNegativeReals)
# Facet intercept has units of (fraction of 1-in-2 peak)
resolve_model.facet_intercept = Param(resolve_model.ELCC_SURFACE_FACETS, within=PercentFraction)
# annual capacity factor - used to calculate energy penetration of variable renewables in ELCC surface constraint
resolve_model.capacity_factor = Param(resolve_model.PRM_VARIABLE_RENEWABLE_RESOURCES, within=PercentFraction)
# flag to denote which resources are associated with each ELCC coefficient
resolve_model.elcc_solar_bin = Param(resolve_model.PRM_VARIABLE_RENEWABLE_RESOURCES, within=Binary)
resolve_model.elcc_wind_bin = Param(resolve_model.PRM_VARIABLE_RENEWABLE_RESOURCES, within=Binary)

# local capacity constraint params
# total MW of new capacity needed in all local areas in each period
resolve_model.local_capacity_deficiency_mw = Param(resolve_model.PERIODS, within=NonNegativeReals)
# in the local capacity constraint, renewables located in local areas have a fixed net qualifying capacity (NQC)
resolve_model.local_variable_renewable_nqc_fraction = Param(resolve_model.PRM_VARIABLE_RENEWABLE_RESOURCES,
                                                            within=PercentFraction)
# the amount of new capacity of each resource that can be counted towards local needs
resolve_model.capacity_limit_local_mw = Param(resolve_model.LOCAL_CAPACITY_LIMITED_RESOURCES,
                                              resolve_model.PERIODS,
                                              within=NonNegativeReals)


def planning_reserve_margin_resource_membership_init(model, resource):
    """
    Add up the number of times each planning reserve margin (PRM) resource is going to appear in the PRM constraint
    :param model:
    :param resource: All prm resources - each of these should have one and only one PRM representation
    :return:
    """
    memberships = 0
    if resource in model.PRM_NQC_RESOURCES:
        memberships += 1
    if resource in model.PRM_VARIABLE_RENEWABLE_RESOURCES:
        if model.elcc_solar_bin[resource]:
            memberships += 1
        if model.elcc_wind_bin[resource]:
            memberships += 1
    # In the PRM constraints, imported TX_DELIVERABILITY_RESOURCES
    # are handled differently than those balanced by the PRM zone
    # a resource can't be brought in on both existing and new transmission,
    # so the PRM validation will fail if both existing and new flags are true.
    if resource in model.TX_DELIVERABILITY_RESOURCES:
        if model.import_on_existing_tx[resource]:
            memberships += 1
        if model.import_on_new_tx[resource]:
            memberships += 1
    if resource in model.EE_PROGRAMS:
        memberships += 1
    return memberships


def planning_reserve_margin_resource_membership_validate(model, memberships, resource):
    """
    Check that all PRM resources are included in the PRM (memberships = 1)
    If some have been left out, then memberships = 0 and an error is returned
    Also, if some have been counted twice, then memberships > 1 and an error is returned
    :param model:
    :param memberships:
    :param resource:
    :return:
    """
    return memberships == 1

resolve_model.prm_memberships = Param(resolve_model.PRM_RESOURCES,
                                      initialize=planning_reserve_margin_resource_membership_init,
                                      validate=planning_reserve_margin_resource_membership_validate)

# ##### GHG target params ##### #
resolve_model.enforce_ghg_targets = Param(within=Boolean)
resolve_model.ghg_emissions_target_tco2_per_year = Param(resolve_model.PERIODS, within=NonNegativeReals)
# the emissions credit adjusts the target for factors outside of the modeled resources and transmission lines.
# it can be positive (relaxing the target) or negative (making the target more stringent)
resolve_model.ghg_emissions_credit_tco2_per_year = Param(resolve_model.PERIODS, within=Reals)


# The set GHG_TARGET_RESOURCES selects resources to be covered under a GHG target
resolve_model.include_in_ghg_target = Param(resolve_model.ZONES, within=Boolean)
resolve_model.GHG_TARGET_ZONES = \
    Set(within=resolve_model.ZONES,
        initialize=resolve_model.ZONES,
        filter=lambda model, zone: model.include_in_ghg_target[zone],
        ordered=True)

resolve_model.GHG_TARGET_RESOURCES = \
    Set(within=resolve_model.THERMAL_RESOURCES,
        initialize=resolve_model.THERMAL_RESOURCES,
        filter=lambda model, resource: model.zone[resource] in model.GHG_TARGET_ZONES,
        ordered=True)


# The set TRANSMISSION_LINES_GHG_TARGET selects transmission lines to be covered under a GHG target
# Include all lines into or out of zones covered under the GHG target,
# but don't include lines if both to and from directions are covered under the GHG target
def transmission_lines_ghg_target_init(model):
    transmission_lines_ghg_target = list()
    for line in model.TRANSMISSION_LINES:
        if not (model.transmission_to[line] in model.GHG_TARGET_ZONES and
                    model.transmission_from[line] in model.GHG_TARGET_ZONES):
            if (model.transmission_to[line] in model.GHG_TARGET_ZONES or
                    model.transmission_from[line] in model.GHG_TARGET_ZONES):
                transmission_lines_ghg_target.append(line)
    return transmission_lines_ghg_target

resolve_model.TRANSMISSION_LINES_GHG_TARGET = \
    Set(within=resolve_model.TRANSMISSION_LINES,
        initialize=transmission_lines_ghg_target_init,
        ordered=True)


# GHG import factors representing the amount of CO2
# assumed to be flowing along each direction of each transmission line.
# Must be non-negative.
resolve_model.positive_direction_tco2_per_mwh = Param(resolve_model.TRANSMISSION_LINES_GHG_TARGET,
                                                      resolve_model.PERIODS,
                                                      within=NonNegativeReals)
resolve_model.negative_direction_tco2_per_mwh = Param(resolve_model.TRANSMISSION_LINES_GHG_TARGET,
                                                      resolve_model.PERIODS,
                                                      within=NonNegativeReals)


# ############ Multi-day hydro sharing params ###########
if resolve_model.multi_day_hydro_energy_sharing:
    resolve_model.hydro_sharing_interval_id = Param(resolve_model.DAYS, within=NonNegativeReals)

    # hydro sharing group set
    def hydro_sharing_interval_init(model):
        """
        Hydro sharing group -- the days within the same hydro sharing group and move hydro around
        :param model:
        :return:
        """
        hydro_sharing_interval_ids = list()
        for day in model.DAYS:
            hydro_sharing_interval_ids.append(model.hydro_sharing_interval_id[day])
        hydro_sharing_interval_ids = list(set(hydro_sharing_interval_ids))
        return sorted(hydro_sharing_interval_ids)

    resolve_model.HYDRO_SHARING_INTERVAL = Set(domain=NonNegativeIntegers,
                                               initialize=hydro_sharing_interval_init,
                                               ordered=True)

    resolve_model.daily_max_hydro_budget_increase_hours = Param(resolve_model.HYDRO_RESOURCES, resolve_model.DAYS,
                                                                within=NonNegativeReals)
    resolve_model.daily_max_hydro_budget_decrease_hours = Param(resolve_model.HYDRO_RESOURCES, resolve_model.DAYS,
                                                                within=NonNegativeReals)
    resolve_model.max_hydro_to_move_around_hours = Param(resolve_model.HYDRO_RESOURCES,
                                                       resolve_model.HYDRO_SHARING_INTERVAL,
                                                       within=NonNegativeReals)

# ############ EE program related params ###########
if resolve_model.allow_ee_investment:

    # EE program params
    resolve_model.ee_t_and_d_losses_fraction = Param(resolve_model.EE_PROGRAMS, within=PercentFraction)
    resolve_model.ee_btm_peak_load_reduction_mw_per_amw = Param(resolve_model.EE_PROGRAMS, within=NonNegativeReals)
    resolve_model.ee_btm_local_capacity_mw_per_amw = \
        Param(resolve_model.EE_PROGRAMS, within=NonNegativeReals)

    # EE period params
    resolve_model.max_investment_in_period_aMW = Param(resolve_model.EE_PROGRAMS, resolve_model.VINTAGES,
                                                    within=NonNegativeReals)

    # EE timepoint params
    resolve_model.ee_shapes_btm_mwh_per_amw = \
        Param(resolve_model.EE_PROGRAMS, resolve_model.DAYS, resolve_model.HOURS_OF_DAY,
              within=NonNegativeReals)

# ---------------------- semi-storage zones related parameters --------------------
if resolve_model.allow_semi_storage_zones:
    resolve_model.SEMI_STORAGE_ZONES = Set(ordered=True)

    resolve_model.ssz_from_zone = Param(resolve_model.SEMI_STORAGE_ZONES)

    semi_storage_zones_params = ['ssz_positive_direction_hurdle_rate_per_mw',
                                 'ssz_negative_direction_hurdle_rate_per_mw']

    for param in semi_storage_zones_params:
        setattr(resolve_model, param, Param(resolve_model.SEMI_STORAGE_ZONES, resolve_model.PERIODS,
                                            within=NonNegativeReals))

    semi_storage_zones_reals_params = ['ssz_max_flow_mw', 'ssz_min_flow_mw']

    for param in semi_storage_zones_reals_params:
        setattr(resolve_model, param, Param(resolve_model.SEMI_STORAGE_ZONES, resolve_model.PERIODS,
                                            within=Reals))


# ############ resources using existing tx lines related parameters ###########
if resolve_model.resource_use_tx_capacity:

    resolve_model.RESOURCE_TX_IDS = Set(ordered=True)

    # the name of the dedicated import resources
    resolve_model.dedicated_import_resource = Param(resolve_model.RESOURCE_TX_IDS)

    # the name the of tx line that the resources are used to transmit power
    resolve_model.tx_line_used = Param(resolve_model.RESOURCE_TX_IDS)

    # which direction of transmission line is used by the resource (1 or -1)
    resolve_model.resource_tx_direction = Param(resolve_model.RESOURCE_TX_IDS,
                                                within=Integers)


#########################
# ##### VARIABLES ##### #
#########################

# ##### Build variables ##### #

resolve_model.Build_Capacity_MW = Var(resolve_model.NEW_BUILD_RESOURCES, resolve_model.VINTAGES,
                                      within=NonNegativeReals)

resolve_model.Build_Storage_Energy_Capacity_MWh = Var(resolve_model.NEW_BUILD_STORAGE_RESOURCES, resolve_model.VINTAGES,
                                                      within=NonNegativeReals)

# Retirement variables for planned capacity
resolve_model.Retire_Planned_Capacity_MW = Var(resolve_model.CAN_RETIRE_RESOURCES,
                                               resolve_model.PERIODS,
                                               within=NonNegativeReals)

# Retirement variables for new capacity.
# Fixed O&M costs can vary by vintage, so retirements must be tracked by vintage.
# Represents all retirements of a given vintage made up to and including the period in question.
resolve_model.Retire_New_Capacity_By_Vintage_Cumulative_MW = \
    Var(resolve_model.CAN_RETIRE_RESOURCES_NEW,
        resolve_model.PERIOD_VINTAGES,
        within=NonNegativeReals)


def new_installed_capacity_tracking_rule(model, new_build_resource, period):
    """
    Track how much new capacity we have of each resource in each period.
    For each period, calculate how much capacity was installed in prior periods up to and including the current period.
    Used in results reporting.
    :param model:
    :param new_build_resource:
    :param period:
    :return:
    """
    new_installed_capacity = float()
    for vintage in model.VINTAGES:
        if vintage <= period:
            new_installed_capacity += model.Build_Capacity_MW[new_build_resource, vintage]

    return new_installed_capacity


resolve_model.Cumulative_New_Installed_Capacity_MW = Expression(resolve_model.NEW_BUILD_RESOURCES,
                                                                resolve_model.PERIODS,
                                                                rule=new_installed_capacity_tracking_rule)


def retire_new_capacity_period_total_rule(model, resource, period):
    """
    Track how much new capacity has been retired up to and including the current period
    Used in results reporting.
    """
    retire_new_capacity = float()
    for vintage in model.VINTAGES:
        if period >= vintage:
            retire_new_capacity += model.Retire_New_Capacity_By_Vintage_Cumulative_MW[resource, period, vintage]

    return retire_new_capacity


resolve_model.Retire_New_Capacity_In_Period_Cumulative_MW = \
    Expression(resolve_model.CAN_RETIRE_RESOURCES_NEW,
               resolve_model.PERIODS,
               rule=retire_new_capacity_period_total_rule)


def operational_new_capacity_in_period_by_vintage_rule(model, resource, period, vintage):
    """
    The amount of new capacity that is still in operation (not retired) in a period
    following installation in a previous vintage. Elsewhere retirements when period = vintage are prohibited.
    """

    if resource in model.CAN_RETIRE_RESOURCES_NEW:
        retired_capacity = model.Retire_New_Capacity_By_Vintage_Cumulative_MW[resource, period, vintage]
    else:
        retired_capacity = 0

    return model.Build_Capacity_MW[resource, vintage] - retired_capacity


resolve_model.Operational_New_Capacity_In_Period_By_Vintage_MW = \
    Expression(resolve_model.NEW_BUILD_RESOURCES,
               resolve_model.PERIOD_VINTAGES,
               rule=operational_new_capacity_in_period_by_vintage_rule)


def operational_new_capacity_in_period_rule(model, resource, period):
    """
    Track how much new capacity is still operational (has not been retired) in each period.
    """
    operational_new_capacity = float()
    for vintage in model.VINTAGES:
        if period >= vintage:
            operational_new_capacity += \
                model.Operational_New_Capacity_In_Period_By_Vintage_MW[resource, period, vintage]

    return operational_new_capacity


resolve_model.Operational_New_Capacity_MW = Expression(resolve_model.NEW_BUILD_RESOURCES,
                                                       resolve_model.PERIODS,
                                                       rule=operational_new_capacity_in_period_rule)


def cumulative_retired_planned_capacity_rule(model, resource, period):
    """
    Track how much planned capacity has been retired up to and including the current period
    Used in results reporting.
    :param model:
    :param resource:
    :param period:
    :return:
    """
    cumulative_retired_planned_capacity = float()
    for p in model.PERIODS:
        if p <= period:
            cumulative_retired_planned_capacity += model.Retire_Planned_Capacity_MW[resource, p]

    return cumulative_retired_planned_capacity


resolve_model.Retire_Planned_Capacity_Cumulative_MW = \
    Expression(resolve_model.CAN_RETIRE_RESOURCES,
               resolve_model.PERIODS,
               rule=cumulative_retired_planned_capacity_rule)


# Define the planned capacity actually operational in each period
# This will only diverge from the planned capacity input values if retirements are allowed
def operational_planned_capacity_in_period_rule(model, resource, period):

    if resource in model.CAN_RETIRE_RESOURCES:
        cumulative_planned_retirements_mw = model.Retire_Planned_Capacity_Cumulative_MW[resource, period]
    else:
        # if endogenous retirements aren't allowed, the planned capacity can still be reduced over time
        # via the schedule of planned capacity subtractions
        cumulative_planned_retirements_mw = model.cumulative_planned_capacity_subtractions_mw[resource, period]

    # planned capacity in the first period is an "addition"
    return model.cumulative_planned_capacity_additions_mw[resource, period] - cumulative_planned_retirements_mw


resolve_model.Operational_Planned_Capacity_MW = Expression(resolve_model.RESOURCES_WITH_MW_CAPACITY,
                                                           resolve_model.PERIODS,
                                                           rule=operational_planned_capacity_in_period_rule)


def operational_capacity_tracking_rule(model, resource, period):
    """
    Track how much capacity of each resource is operational in each period,
    including planned capacity, new builds, and retirements
    :param model:
    :param resource:
    :param period:
    :return:
    """
    if resource in model.NEW_BUILD_RESOURCES:
        operational_new_capacity = model.Operational_New_Capacity_MW[resource, period]
    else:
        operational_new_capacity = 0

    return model.Operational_Planned_Capacity_MW[resource, period] + operational_new_capacity


resolve_model.Operational_Capacity_MW = \
    Expression(resolve_model.RESOURCES_WITH_MW_CAPACITY,
               resolve_model.PERIODS,
               rule=operational_capacity_tracking_rule)

def operational_nqc_tracking_rule(model, resource, period):
    return (
        model.net_qualifying_capacity_fraction[resource] *
        model.Operational_Capacity_MW[resource, period]
    )

resolve_model.Operational_NQC_MW = Expression(
    resolve_model.PRM_NQC_RESOURCES,
    resolve_model.PERIODS,
    rule=operational_nqc_tracking_rule
)


def available_capacity_def(model, resource, timepoint):
    """
    Define the amount of capacity available for dispatch in a given timepoint,
    which is the Operational Capacity in the period, derated by outages.
    """

    return model.Operational_Capacity_MW[resource, model.period[timepoint]] \
           * model.maintenance_derate[resource, timepoint]


resolve_model.Available_Capacity_In_Timepoint_MW = \
    Expression(resolve_model.RESOURCES_WITH_MW_CAPACITY,
               resolve_model.TIMEPOINTS,
               rule=available_capacity_def)

# The cumulative new installed capacity for TX_DELIVERABILITY_RESOURCES is chosen
# as either fully deliverable or energy only by the following two variables
resolve_model.Fully_Deliverable_Installed_Capacity_MW = Var(resolve_model.TX_DELIVERABILITY_RESOURCES,
                                                            resolve_model.PERIODS,
                                                            within=NonNegativeReals)
resolve_model.Energy_Only_Installed_Capacity_MW = Var(resolve_model.TX_DELIVERABILITY_RESOURCES,
                                                      resolve_model.PERIODS,
                                                      within=NonNegativeReals)


# Storage energy capacity expressions
def new_storage_installed_energy_capacity_tracking_rule(model, new_build_storage_resource, current_period):
    """
    Track how much new energy capacity we have of each storage resource in each period.
    For each period, calculate how much energy capacity was installed in prior periods up to and including the current
    period.
    :param model:
    :param new_build_storage_resource:
    :param current_period:
    :return:
    """
    new_storage_installed_energy_capacity = float()
    for vintage in model.VINTAGES:
        if vintage <= current_period:
            new_storage_installed_energy_capacity += \
                model.Build_Storage_Energy_Capacity_MWh[new_build_storage_resource, vintage]

    return new_storage_installed_energy_capacity


resolve_model.Cumulative_New_Storage_Energy_Capacity_MWh = \
    Expression(resolve_model.NEW_BUILD_STORAGE_RESOURCES,
               resolve_model.PERIODS,
               rule=new_storage_installed_energy_capacity_tracking_rule)


def total_storage_installed_energy_capacity_tracking_rule(model, storage_resource, period):
    """
    Track how much total energy capacity we have of each storage resource in each period,
    including planned capacity and new builds.
    For each period, calculate the sum of planned capacity in the period and how much capacity was installed in prior
    periods up to and including the current period.
    :param model:
    :param storage_resource:
    :param period:
    :return:
    """
    if storage_resource in model.NEW_BUILD_RESOURCES:
        cumulative_new_build_mwh = model.Cumulative_New_Storage_Energy_Capacity_MWh[storage_resource, period]
    else:
        cumulative_new_build_mwh = 0

    return model.planned_storage_energy_capacity_mwh[storage_resource, period] + cumulative_new_build_mwh


resolve_model.Total_Storage_Energy_Capacity_MWh = \
    Expression(resolve_model.STORAGE_RESOURCES,
               resolve_model.PERIODS,
               rule=total_storage_installed_energy_capacity_tracking_rule)


# ELCC Variables
resolve_model.ELCC_Variable_Renewables_MW = Var(resolve_model.PERIODS, within=NonNegativeReals)
resolve_model.ELCC_Storage_MW = Var(resolve_model.PRM_STORAGE_RESOURCES,
                                    resolve_model.PERIODS,
                                    within=NonNegativeReals)

# Capacity that counts towards local deficiencies
resolve_model.Local_New_Capacity_MW = Var(resolve_model.LOCAL_CAPACITY_RESOURCES,
                                          resolve_model.PERIODS,
                                          within=NonNegativeReals)
# storage energy capacity for storage resources that can count towards local constraints
# must be apportioned between local and nonlocal such that the energy duration can be separately constrained
resolve_model.Local_New_Storage_Energy_Capacity_MWh = Var(resolve_model.LOCAL_CAPACITY_STORAGE_RESOURCES,
                                                          resolve_model.PERIODS,
                                                          within=NonNegativeReals)


# ##### Unit-commitment and dispatch variables ##### #

# Variable to track power provided by each resource
# Will be restricted differently depending on resource tech type
resolve_model.Provide_Power_MW = \
    Var(resolve_model.RESOURCES
            - resolve_model.LOAD_ONLY_RESOURCES
            - resolve_model.EE_PROGRAMS
            - resolve_model.FLEXIBLE_LOAD_RESOURCES,
        resolve_model.TIMEPOINTS,
        within=NonNegativeReals)

# Unit commitment variables #
resolve_model.commit_all_capacity = Param(
    resolve_model.DISPATCHABLE_RESOURCES,
    resolve_model.TIMEPOINTS,
    within=Boolean,
    default=False
)
# Thermal units that are not must run (i.e. are dispatchable) have to be committed to provide power
resolve_model.Commit_Units = Var(resolve_model.DISPATCHABLE_RESOURCES, resolve_model.TIMEPOINTS,
                                 within=NonNegativeReals)  # may change to int
resolve_model.Start_Units = Var(resolve_model.DISPATCHABLE_RESOURCES, resolve_model.TIMEPOINTS,
                                within=NonNegativeReals)  # may change to int
resolve_model.Shut_Down_Units = Var(resolve_model.DISPATCHABLE_RESOURCES, resolve_model.TIMEPOINTS,
                                    within=NonNegativeReals)  # may change to int


def prestart_to_start_definition(model, resource, timepoint):
    """
    A unit starts (adds to Commit_Units) min_down_time_hours after it was pre-started
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    min_down_time = model.min_down_time_hours[model.technology[resource]]


    # Resolve days are circular, so if adding min_down_time moves past the end of the day, wrap around to the start
    if timepoint + min_down_time > model.last_timepoint_of_day[model.period[timepoint], model.day[timepoint]]:
        day_wrap = model.timepoints_per_day
    else:
        day_wrap = 0

    return model.Start_Units[resource, timepoint + min_down_time - day_wrap]


resolve_model.PreStart_Units = Expression(resolve_model.DISPATCHABLE_RESOURCES,
                                          resolve_model.TIMEPOINTS,
                                          rule=prestart_to_start_definition)


def preshut_down_to_shut_down_definition(model, resource, timepoint):
    """
    A unit shuts down (subtracts from to Commit_Units) min_up_time_hours after it was preshut down
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    min_up_time = model.min_up_time_hours[model.technology[resource]]


    # Resolve days are circular, so if adding min_down_time moves past the end of the day, wrap around to the start
    if timepoint + min_up_time > model.last_timepoint_of_day[model.period[timepoint], model.day[timepoint]]:
        day_wrap = model.timepoints_per_day
    else:
        day_wrap = 0

    return model.Shut_Down_Units[resource, timepoint + min_up_time - day_wrap]


resolve_model.PreShut_Down_Units = Expression(resolve_model.DISPATCHABLE_RESOURCES,
                                              resolve_model.TIMEPOINTS,
                                              rule=preshut_down_to_shut_down_definition)


def define_starting_units(model, resource, timepoint):
    """
    Track how many units are in the process of starting in each timepoint
    by summing over previous timepoints within the min down time for each resource.
    This variable will then be used to determine commitment from timepoint to timepoint
    (in conjunction with the variable tracking units scheduled to shut down).
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    starting_not_yet_committed_units = float()

    min_down_time = model.min_down_time_hours[model.technology[resource]]

    # Days are treated as circular, so if min down time puts us across the boundary (hour 24 to hour 1),
    # add 24 hours to avoid negative numbers (for example if we are in timepoint 3 and have a 5-hour min down time,
    # we'll need to look at units scheduled to start in the four previous hours,
    # namely hours (3+24)-4=23, (3+24)-3=24, 1, and 2.
    if timepoint - min_down_time < model.first_timepoint_of_day[model.period[timepoint], model.day[timepoint]]:
        previous_timepoints = list()
        for pt in range(1, min_down_time):
            if timepoint - pt >= model.first_timepoint_of_day[model.period[timepoint], model.day[timepoint]]:
                previous_timepoints.append(timepoint - pt)
            else:
                previous_timepoints.append(timepoint + model.timepoints_per_day - pt)

        for t in previous_timepoints:
            starting_not_yet_committed_units += model.PreStart_Units[resource, t]
    else:
        for t in range(1, min_down_time):
            starting_not_yet_committed_units += model.PreStart_Units[resource, timepoint - t]

    return starting_not_yet_committed_units


resolve_model.Starting_Units = Expression(resolve_model.DISPATCHABLE_RESOURCES,
                                          resolve_model.TIMEPOINTS,
                                          rule=define_starting_units)


def define_shutting_down_units(model, resource, timepoint):
    """
    Track how many units are in the process of shutting down in each timepoint
    by summing over previous timepoints within the min up time for each resource.
    This variable will then be used to determine commitment from timepoint to timepoint
    (in conjunction with the variable tracking units scheduled to start up).
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """

    shutting_down_still_committed_units = float()

    min_up_time = model.min_up_time_hours[model.technology[resource]]

    # We'll treat the day as circular, so if min up time puts us across the boundary (hour 24 to hour 1), we'll have
    # to add 24 hours to avoid negative numbers (for example if we are in timepoint 3 and have a 5-hour min up time,
    # we'll need to look at units scheduled to shut down in the four previous hours,
    # namely hours (3+24)-4=23, (3+24)-3=24, 1, and 2.
    if timepoint - min_up_time < model.first_timepoint_of_day[model.period[timepoint], model.day[timepoint]]:
        previous_timepoints = list()
        for pt in range(1, min_up_time):
            if timepoint - pt >= model.first_timepoint_of_day[model.period[timepoint], model.day[timepoint]]:
                previous_timepoints.append(timepoint - pt)
            else:
                previous_timepoints.append(timepoint + model.timepoints_per_day - pt)

        for t in previous_timepoints:
            shutting_down_still_committed_units += model.PreShut_Down_Units[resource, t]
    else:
        for t in range(1, min_up_time):
            shutting_down_still_committed_units += model.PreShut_Down_Units[resource, timepoint - t]

    return shutting_down_still_committed_units


resolve_model.Shutting_Down_Units = Expression(resolve_model.DISPATCHABLE_RESOURCES,
                                               resolve_model.TIMEPOINTS,
                                               rule=define_shutting_down_units)


def fully_operational_units_def_rule(model, resource, timepoint):
    """
    The number of units that are fully operational is the number that aren't in their start or stop sequence,
    which is currently to hold the unit at PMin for one timestep.
    Shut_Down_Units from the next timepoint is used because this variable is non-zero in
    the timestep *after* the unit has finished its stop sequence
    Fully_Operational_Units is only defined for the set DISPATCHABLE_RAMP_LIMITED_RESOURCES because
    if a unit can ramp quickly then all committed units are fully operational
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.Commit_Units[resource, timepoint] \
        - model.Start_Units[resource, timepoint] \
        - model.Shut_Down_Units[resource, model.next_timepoint[timepoint]]


resolve_model.Fully_Operational_Units = Expression(resolve_model.DISPATCHABLE_RAMP_LIMITED_RESOURCES,
                                                   resolve_model.TIMEPOINTS,
                                                   rule=fully_operational_units_def_rule)


def define_start_capacity(model, resource, timepoint):
    """Calculate MW of capacity started in timepoint

    Args:
        resource: dispatchable resource
        timepoint
    """
    return (
        model.Start_Units[resource, timepoint] *
        model.unit_size_mw[model.technology[resource]]
    )
resolve_model.Start_Capacity_MW = Expression(
    resolve_model.DISPATCHABLE_RESOURCES,
    resolve_model.TIMEPOINTS,
    rule=define_start_capacity
)

def define_commit_capacity(model, resource, timepoint):
    """Calculate MW of capacity committed in timepoint

    Args:
        resource: dispatchable resource
        timepoint
    """
    return (
        model.Commit_Units[resource, timepoint] *
        model.unit_size_mw[model.technology[resource]]
    )
resolve_model.Commit_Capacity_MW = Expression(
    resolve_model.DISPATCHABLE_RESOURCES,
    resolve_model.TIMEPOINTS,
    rule=define_commit_capacity
)

# Multi day hydro feature variables
if resolve_model.multi_day_hydro_energy_sharing:
    # daily hydro budget increase can be positive and negative (positive: budget increase, negative: budget decrease)
    resolve_model.Daily_Hydro_Budget_Increase_MWh = Var(resolve_model.HYDRO_RESOURCES, resolve_model.PERIODS,
                                                        resolve_model.DAYS, within=Reals)
    # the absolute amount of hydro budget being moved (=|Daily_Hydro_Budget_Increase_MWh|)
    resolve_model.Positive_Hydro_Budget_Moved_MWh = Var(resolve_model.HYDRO_RESOURCES, resolve_model.PERIODS,
                                                        resolve_model.DAYS, within=NonNegativeReals)


def define_rps_target(model, period):
    """
    Reduce the RPS target when the model builds EE
    The capacity of EE resources is in average MW - multiplying by hours_per_year gives yearly MWh
    :param model:
    :param period:
    :return:
    """
    total_ee_mwh = float()
    for resource in model.EE_PROGRAMS:
        if model.zone[resource] in model.RPS_ZONES:
            total_ee_mwh += \
                model.Operational_Capacity_MW[resource, period] * model.hours_per_year

    return (model.retail_sales_mwh[period] - total_ee_mwh) \
        * model.rps_fraction_of_retail_sales[period]


def define_ee_program_load_in_timepoint(model, resource, timepoint):
    """
    Derive EE program load reduction contribution based on the total EE program investment and EE impact shape
    BTM = behind the meter - there are avoided T & D losses from EE investments.
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.Operational_Capacity_MW[resource, model.period[timepoint]] \
        * model.ee_shapes_btm_mwh_per_amw[resource, model.day[timepoint], model.hour_of_day[timepoint]] \
        * (1 + model.ee_t_and_d_losses_fraction[resource])


def define_prm_peak_load(model, period):
    """
    Define the peak load for the planning reserve margin (PRM), subtracting energy efficiency (ee) impacts
    :param model:
    :param period:
    :return:
    """

    prm_peak_load_mw = model.prm_peak_load_mw[period]

    if resolve_model.allow_ee_investment:
        for resource in model.PRM_EE_PROGRAMS:
            prm_peak_load_mw -= model.Operational_Capacity_MW[resource, period] \
                                      * model.ee_btm_peak_load_reduction_mw_per_amw[resource] \
                                      * (1 + model.ee_t_and_d_losses_fraction[resource])

    return prm_peak_load_mw


if resolve_model.allow_ee_investment:
    resolve_model.EE_Reduced_Load_FTM_MW = Expression(resolve_model.EE_PROGRAMS,
                                                      resolve_model.TIMEPOINTS,
                                                      rule=define_ee_program_load_in_timepoint)

resolve_model.RPS_Target_MWh = Expression(resolve_model.PERIODS, rule=define_rps_target)
resolve_model.PRM_Peak_Load_MW = Expression(resolve_model.PERIODS,
                                            rule=define_prm_peak_load)

# Additional storage variables including charging of storage and variable to track available energy in storage
resolve_model.Charge_Storage_MW = Var(resolve_model.STORAGE_RESOURCES, resolve_model.TIMEPOINTS,
                                      within=NonNegativeReals)


if resolve_model.allow_semi_storage_zones:
    # power transmit decision variables: positives means power flow from the "from zone" to the semi storage zone,
    # negative means power flow from the semi storage zone to the "from zone".
    # "from zones" are in the whole functional zone set. semi storage zone is a virtual concept act similarly as a
    # very large battery without efficiency losses but limit by charge and discharge capacity (MW). hurdle rates are
    # applied for transmitting between the from zones and ssz.
    # total power transmit need to be net 0 in the period
    resolve_model.SSZ_Transmit_Power_MW = Var(resolve_model.SEMI_STORAGE_ZONES, resolve_model.TIMEPOINTS, within=Reals)
    resolve_model.SSZ_Positive_Transmit_Power_MW = Var(resolve_model.SEMI_STORAGE_ZONES, resolve_model.TIMEPOINTS,
                                                       within=NonNegativeReals)
    resolve_model.SSZ_Negative_Transmit_Power_MW = Var(resolve_model.SEMI_STORAGE_ZONES, resolve_model.TIMEPOINTS,
                                                       within=NonNegativeReals)


resolve_model.Energy_in_Storage_MWh = Var(resolve_model.STORAGE_RESOURCES, resolve_model.TIMEPOINTS,
                                          within=NonNegativeReals)

# Reserves
resolve_model.Provide_Upward_Reg_MW = Var(resolve_model.REGULATION_RESERVE_RESOURCES, resolve_model.TIMEPOINTS,
                                          within=NonNegativeReals)
resolve_model.Provide_Downward_Reg_MW = Var(resolve_model.REGULATION_RESERVE_RESOURCES, resolve_model.TIMEPOINTS,
                                            within=NonNegativeReals)
resolve_model.Provide_LF_Upward_Reserve_MW = Var(resolve_model.LOAD_FOLLOWING_RESERVE_RESOURCES,
                                                 resolve_model.TIMEPOINTS,
                                                 within=NonNegativeReals)
resolve_model.Provide_LF_Downward_Reserve_MW = Var(resolve_model.LOAD_FOLLOWING_RESERVE_RESOURCES,
                                                   resolve_model.TIMEPOINTS,
                                                   within=NonNegativeReals)
resolve_model.Provide_Spin_MW = Var(resolve_model.SPINNING_RESERVE_RESOURCES,
                                    resolve_model.TIMEPOINTS,
                                    within=NonNegativeReals)
resolve_model.Provide_Frequency_Response_MW = Var(resolve_model.TOTAL_FREQ_RESP_RESOURCES,
                                                  resolve_model.TIMEPOINTS,
                                                  within=NonNegativeReals)
resolve_model.Upward_Reg_Violation_MW = Var(resolve_model.TIMEPOINTS,
                                            within=NonNegativeReals)
resolve_model.Downward_Reg_Violation_MW = Var(resolve_model.TIMEPOINTS,
                                              within=NonNegativeReals)
resolve_model.Upward_LF_Reserve_Violation_MW = Var(resolve_model.TIMEPOINTS,
                                                   within=NonNegativeReals)
resolve_model.Downward_LF_Reserve_Violation_MW = Var(resolve_model.TIMEPOINTS,
                                                     within=NonNegativeReals)
resolve_model.Spin_Violation_MW = Var(resolve_model.TIMEPOINTS,
                                      within=NonNegativeReals)

# define an hourly (scheduled) curtailment variable for variable renewable resources that can be curtailed
resolve_model.Scheduled_Curtailment_MW = Var(resolve_model.CURTAILABLE_VARIABLE_RESOURCES,
                                             resolve_model.TIMEPOINTS,
                                             within=NonNegativeReals)


# with endogenous load following, allow variable resources to provide upward load following (if pre-curtailed)
resolve_model.Variable_Resource_Provide_Downward_LF_MW = Var(
    resolve_model.TIMEPOINTS,
    within=NonNegativeReals)

resolve_model.Variable_Resource_Provide_Upward_LF_MW = Var(
    resolve_model.TIMEPOINTS,
    within=NonNegativeReals)


def downward_load_following_subhourly_energy_rule(model, timepoint):
    """Calculate energy dispatch by variable resources providing LF up."""
    return (model.lf_reserve_dispatch_fraction *
            model.Variable_Resource_Provide_Downward_LF_MW[timepoint])

resolve_model.Subhourly_Downward_LF_Energy_MWh = Expression(
    resolve_model.TIMEPOINTS,
    rule=downward_load_following_subhourly_energy_rule)


def upward_load_following_subhourly_energy_rule(model, timepoint):
    """Calculate energy dispatch by variable resources providing LF up."""
    return (model.lf_reserve_dispatch_fraction *
            model.Variable_Resource_Provide_Upward_LF_MW[timepoint])

resolve_model.Subhourly_Upward_LF_Energy_MWh = Expression(
    resolve_model.TIMEPOINTS,
    rule=upward_load_following_subhourly_energy_rule)


# ##### Transmission flows ##### #
resolve_model.Transmit_Power_Unspecified_MW = Var(resolve_model.TRANSMISSION_LINES,
                                                  resolve_model.TIMEPOINTS,
                                                  within=Reals)


def define_transmit_power(model, transmission_line, timepoint):
    """
    Expression that adds unspecified flows along each transmission line along to specified imports and exports
    to arrive at the net flow along the line.
    This represents the metered flow at the boundary between balancing areas.
    :param model:
    :param transmission_line:
    :param timepoint:
    :return:
    """
    transmission_reserved_for_dedicated_resources = 0.0

    if model.resource_use_tx_capacity:
        for resource_line_pair in model.RESOURCE_TX_IDS:
            resource = model.dedicated_import_resource[resource_line_pair]
            if transmission_line == model.tx_line_used[resource_line_pair]:
                if resource in model.STORAGE_RESOURCES:
                    charge_storage = model.Charge_Storage_MW[resource, timepoint]
                else:
                    charge_storage = 0.0

                transmission_reserved_for_dedicated_resources += \
                    (model.Provide_Power_MW[resource, timepoint] - charge_storage) \
                    * model.resource_tx_direction[resource_line_pair]

    return model.Transmit_Power_Unspecified_MW[transmission_line, timepoint] \
           + transmission_reserved_for_dedicated_resources


resolve_model.Transmit_Power_MW = Expression(resolve_model.TRANSMISSION_LINES,
                                             resolve_model.TIMEPOINTS,
                                             rule=define_transmit_power)

# positive and negative direction version of Transmit_Power_Unspecified_MW
# The constraints that define these variables assume that the variables are within NonNegativeReals,
# which means that the negative direction variable will always be >= 0, even though
# Transmit_Power_Unspecified_MW for the negative direction is negative (we're in effect taking ABS(Transmit_Power_MW)).

# before adjusting for dedicated import resources that are located outside of the specified zone,
# what is the positive and negative direction
# this is used only in hurdle rates and GHG calculation: because the dedicated import resources are counted for GHG
# and for hurdle rates directly, we assumed dedicated import resources have long term tx contract and we calculate
# CO2 costs directly
resolve_model.Transmit_Power_Unspecified_Positive_Direction_MW = Var(resolve_model.TRANSMISSION_LINES,
                                                                     resolve_model.TIMEPOINTS,
                                                                     within=NonNegativeReals)
resolve_model.Transmit_Power_Unspecified_Negative_Direction_MW = Var(resolve_model.TRANSMISSION_LINES,
                                                                     resolve_model.TIMEPOINTS,
                                                                     within=NonNegativeReals)


# Expressions for hurdle rate costs associated with unspecified imports in each timepoint.
def define_hurdle_cost_per_timepoint_positive_direction(model, line, timepoint):

    return model.Transmit_Power_Unspecified_Positive_Direction_MW[line, timepoint] \
        * model.positive_direction_hurdle_rate_per_mw[line, model.period[timepoint]]


def define_hurdle_cost_per_timepoint_negative_direction(model, line, timepoint):

    return model.Transmit_Power_Unspecified_Negative_Direction_MW[line, timepoint] \
        * model.negative_direction_hurdle_rate_per_mw[line, model.period[timepoint]]

resolve_model.Hurdle_Cost_Per_Timepoint_Positive_Direction = \
    Expression(resolve_model.TRANSMISSION_LINES,
               resolve_model.TIMEPOINTS,
               rule=define_hurdle_cost_per_timepoint_positive_direction)
resolve_model.Hurdle_Cost_Per_Timepoint_Negative_Direction = \
    Expression(resolve_model.TRANSMISSION_LINES,
               resolve_model.TIMEPOINTS,
               rule=define_hurdle_cost_per_timepoint_negative_direction)


# Expressions for GHG emissions attributed to unspecified imports in each timepoint. Cannot be negative.
# Transmit_Power_Unspecified is used here because dedicated imports
# are modeled as supplying power to the "to" zone directly
def define_ghg_unspecified_import_emissions_per_timepoint_positive_direction(model, line, timepoint):

    return model.Transmit_Power_Unspecified_Positive_Direction_MW[line, timepoint] \
        * model.positive_direction_tco2_per_mwh[line, model.period[timepoint]]


def define_ghg_unspecified_import_emissions_per_timepoint_negative_direction(model, line, timepoint):

    return model.Transmit_Power_Unspecified_Negative_Direction_MW[line, timepoint] \
        * model.negative_direction_tco2_per_mwh[line, model.period[timepoint]]

resolve_model.GHG_Unspecified_Imports_tCO2_Per_Timepoint_Positive_Direction = \
    Expression(resolve_model.TRANSMISSION_LINES_GHG_TARGET,
               resolve_model.TIMEPOINTS,
               rule=define_ghg_unspecified_import_emissions_per_timepoint_positive_direction)
resolve_model.GHG_Unspecified_Imports_tCO2_Per_Timepoint_Negative_Direction = \
    Expression(resolve_model.TRANSMISSION_LINES_GHG_TARGET,
               resolve_model.TIMEPOINTS,
               rule=define_ghg_unspecified_import_emissions_per_timepoint_negative_direction)


def define_ghg_unspecified_import_emissions(model, period):
    """
    Expression that sums the emissions from imports into the ghg target area for each period
    :param model:
    :param period:
    :return:
    """
    ghg_unspecified_import_tco2_per_year = float()

    for timepoint in model.TIMEPOINTS:
        if model.period[timepoint] == period:
            for line in model.TRANSMISSION_LINES_GHG_TARGET:
                ghg_unspecified_import_tco2_per_year += \
                    (model.GHG_Unspecified_Imports_tCO2_Per_Timepoint_Positive_Direction[line, timepoint]
                    + model.GHG_Unspecified_Imports_tCO2_Per_Timepoint_Negative_Direction[line, timepoint]) \
                * model.day_weight[model.day[timepoint]]

    return ghg_unspecified_import_tco2_per_year

resolve_model.GHG_Unspecified_Imports_tCO2_Per_Year = \
    Expression(resolve_model.PERIODS,
               rule=define_ghg_unspecified_import_emissions)


# ##### Transmission builds for deliverability  ##### #
resolve_model.New_Transmission_Capacity_MW = Var(resolve_model.TX_ZONES, resolve_model.PERIODS, within=NonNegativeReals)

# ##### Flexible loads ##### #
resolve_model.Charge_EV_Batteries_MW = Var(resolve_model.EV_RESOURCES, resolve_model.TIMEPOINTS,
                                           within=NonNegativeReals)
resolve_model.Energy_in_EV_Batteries_MWh = Var(resolve_model.EV_RESOURCES, resolve_model.TIMEPOINTS,
                                               within=NonNegativeReals)
resolve_model.Hydrogen_Electrolysis_Load_MW = Var(resolve_model.HYDROGEN_ELECTROLYSIS_RESOURCES,
                                                  resolve_model.TIMEPOINTS,
                                                  within=NonNegativeReals)
if resolve_model.include_flexible_load:
    resolve_model.Shift_Load_Down_MW = Var(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                           resolve_model.TIMEPOINTS,
                                           within=NonNegativeReals)
    resolve_model.Shift_Load_Up_MW = Var(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                         resolve_model.TIMEPOINTS,
                                         within=NonNegativeReals)
    # Flexible Load Build Variables
    resolve_model.Flexible_Load_DR_Cost = Var(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                              resolve_model.PERIODS,
                                              within=NonNegativeReals)
    resolve_model.Build_Flexible_Load_Energy_Capacity_MWh = Var(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                                resolve_model.PERIODS,
                                                                within=NonNegativeReals)

    def flexible_load_installed_energy_capacity_tracking_rule(model, resource, current_period):
        """
        Track how much new energy capacity we have of flexible load resource in each period.
        For each period, calculate how much energy capacity was installed in prior periods
        up to and including the current period.
        No retirements allowed.
        :param model:
        :param resource:
        :param current_period:
        :return:
        """
        new_flexible_load_installed_energy_capacity = float()
        for vintage in model.VINTAGES:
            if vintage <= current_period:
                new_flexible_load_installed_energy_capacity += \
                    model.Build_Flexible_Load_Energy_Capacity_MWh[resource, vintage]

        return new_flexible_load_installed_energy_capacity

    resolve_model.Total_Daily_Flexible_Load_Potential_MWh = \
        Expression(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                   resolve_model.PERIODS,
                   rule=flexible_load_installed_energy_capacity_tracking_rule)


# ##### System Variables ##### #

resolve_model.Unserved_Energy_MW = Var(resolve_model.ZONES, resolve_model.TIMEPOINTS, within=NonNegativeReals)
resolve_model.Overgeneration_MW = Var(resolve_model.ZONES, resolve_model.TIMEPOINTS, within=NonNegativeReals)

# RPS, GHG, and Biogas
resolve_model.Bank_RPS_MWh = Var(resolve_model.PERIODS, within=NonNegativeReals)
resolve_model.Pipeline_Biogas_Consumption_MMBtu = Var(resolve_model.PIPELINE_BIOGAS_RESOURCES,
                                                      resolve_model.TIMEPOINTS,
                                                      within=NonNegativeReals)
resolve_model.Pipeline_Biogas_Generation_MW = Var(resolve_model.PIPELINE_BIOGAS_RESOURCES,
                                                  resolve_model.TIMEPOINTS,
                                                  within=NonNegativeReals)


def define_yearly_biogas_pipeline_consumption(model, period):
    """
    derived variable that represents the yearly consumption of pipeline biogas
    :param model:
    :param period:
    :return:
    """
    yearly_pipeline_consumption = float()
    for timepoint in model.TIMEPOINTS:
        if model.period[timepoint] == period:
            for resource in model.PIPELINE_BIOGAS_RESOURCES:
                yearly_pipeline_consumption += model.Pipeline_Biogas_Consumption_MMBtu[resource, timepoint] \
                                               * model.day_weight[model.day[timepoint]] \

    return yearly_pipeline_consumption

resolve_model.Pipeline_Biogas_Consumption_MMBtu_Per_Year = Expression(resolve_model.PERIODS,
                                                                      rule=define_yearly_biogas_pipeline_consumption)


def define_yearly_rps_biogas_pipeline_generation(model, period):
    """
    derived variable that represents the yearly generation of electricity from pipeline biogas
    that counts towards the RPS target
    :param model:
    :param period:
    :return:
    """
    yearly_pipeline_generation = float()
    for resource in model.PIPELINE_BIOGAS_RESOURCES:
        if model.zone[resource] in model.RPS_ZONES:
            for timepoint in model.TIMEPOINTS:
                if model.period[timepoint] == period:
                    yearly_pipeline_generation += model.Pipeline_Biogas_Generation_MW[resource, timepoint] \
                                                  * model.day_weight[model.day[timepoint]] \

    return yearly_pipeline_generation

resolve_model.RPS_Pipeline_Biogas_Generation_MWh_Per_Year = \
    Expression(resolve_model.PERIODS,
               rule=define_yearly_rps_biogas_pipeline_generation)

def define_start_fuel_in_timepoint(model, r, tmp):
    """Calculates start fuel consumption for each dispatchable resource in each timepoint.

    Args:
        r: dispatchable resource
        tmp: timepoint
    """
    return (
        model.Start_Capacity_MW[r, tmp] *
        model.start_fuel_mmbtu_per_mw[model.technology[r]]
    )
resolve_model.Start_Fuel_MMBtu_In_Timepoint = Expression(
    resolve_model.DISPATCHABLE_RESOURCES,
    resolve_model.TIMEPOINTS,
    rule=define_start_fuel_in_timepoint
)


def define_fuel_consumption(model, thermal_resource, timepoint):
    """
    Derived variable that represents the fuel consumption of each thermal resource in each timepoint.
    Includes the dispatch up/down from providing reserves and the associated fuel increase/savings.
    :param model:
    :param thermal_resource:
    :param timepoint:
    :return:
    """

    power_output_mwh = model.Provide_Power_MW[thermal_resource, timepoint]

    # Regulation reserve dispatch
    if thermal_resource in model.REGULATION_RESERVE_RESOURCES:
        power_output_mwh += (model.Provide_Upward_Reg_MW[thermal_resource, timepoint]
                             - model.Provide_Downward_Reg_MW[thermal_resource, timepoint]) \
                             * model.reg_dispatch_fraction

    # Load-following reserve dispatch
    if thermal_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
        power_output_mwh += (model.Provide_LF_Upward_Reserve_MW[thermal_resource, timepoint]
                             - model.Provide_LF_Downward_Reserve_MW[thermal_resource, timepoint]) \
                             * model.lf_reserve_dispatch_fraction

    # Calculate fuel burn using the fuel burn slope
    fuel_consumption = power_output_mwh \
        * model.fuel_burn_slope_mmbtu_per_mwh[model.technology[thermal_resource]]

    # add intercept times commitment for dispatchable thermal gen
    if thermal_resource in model.DISPATCHABLE_RESOURCES:
        fuel_consumption += model.Commit_Units[thermal_resource, timepoint] \
            * model.fuel_burn_intercept_mmbtu_per_hr[model.technology[thermal_resource]]

        # add start fuel burn
        fuel_consumption += model.Start_Fuel_MMBtu_In_Timepoint[thermal_resource, timepoint]

    return fuel_consumption

resolve_model.Fuel_Consumption_MMBtu = Expression(resolve_model.THERMAL_RESOURCES,
                                                  resolve_model.TIMEPOINTS,
                                                  rule=define_fuel_consumption)


# Cost for fuel for each thermal resource for each timepoint
def define_fuel_cost(model, resource, timepoint):

    return model.Fuel_Consumption_MMBtu[resource, timepoint] * \
           model.fuel_price_per_mmbtu[ \
               model.fuel[model.technology[resource]], model.period[timepoint], model.month[timepoint]]


resolve_model.Fuel_Cost_Dollars_Per_Timepoint = Expression(resolve_model.THERMAL_RESOURCES,
                                                           resolve_model.TIMEPOINTS,
                                                           rule=define_fuel_cost)


def define_ghg_resource_timepoint_emissions(model, resource, timepoint):
    """
    Hourly GHG emissions for each thermal resource in each timepoint
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """

    if resource in model.PIPELINE_BIOGAS_RESOURCES:
        biogas_consumption = model.Pipeline_Biogas_Consumption_MMBtu[resource, timepoint]
    else:
        biogas_consumption = 0.0

    return (model.Fuel_Consumption_MMBtu[resource, timepoint] - biogas_consumption) \
           * model.tco2_per_mmbtu[model.fuel[model.technology[resource]]]


resolve_model.GHG_Resource_Emissions_tCO2_Per_Timepoint = Expression(resolve_model.THERMAL_RESOURCES,
                                                                     resolve_model.TIMEPOINTS,
                                                                     rule=define_ghg_resource_timepoint_emissions)



def define_ghg_resource_emissions(model, period):
    """
    Expression that in each period that sums the emissions from resources within the ghg target area
    :param model:
    :param period:
    :return:
    """
    resource_ghg_tco2_per_year = float()

    for timepoint in model.TIMEPOINTS:
        if model.period[timepoint] == period:
            for resource in model.GHG_TARGET_RESOURCES:
                resource_ghg_tco2_per_year += model.GHG_Resource_Emissions_tCO2_Per_Timepoint[resource, timepoint] \
                    * model.day_weight[model.day[timepoint]]

    return resource_ghg_tco2_per_year

resolve_model.GHG_Resource_Emissions_tCO2_Per_Year = Expression(resolve_model.PERIODS,
                                                                rule=define_ghg_resource_emissions)


##################################
# ##### OBJECTIVE FUNCTION ##### #
##################################
def define_variable_cost_in_timepoint(model, resource, timepoint):
    """
    Derived variable that represents the variable cost of each resource in each timepoint (not weighted or discounted)
    All resources are included here, even if variable cost is zero
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """

    if resource in model.HYDROGEN_ELECTROLYSIS_RESOURCES:
        power_var = model.Hydrogen_Electrolysis_Load_MW[resource, timepoint]
    elif resource in model.EV_RESOURCES:
        power_var = model.Charge_EV_Batteries_MW[resource, timepoint]
    # define the variable cost of EE programs behind the meter.
    elif resource in model.EE_PROGRAMS and resolve_model.allow_ee_investment:
        power_var = model.Operational_Capacity_MW[resource, model.period[timepoint]] \
            * model.ee_shapes_btm_mwh_per_amw[resource, model.day[timepoint], model.hour_of_day[timepoint]]
    elif resource in model.FLEXIBLE_LOAD_RESOURCES and resolve_model.include_flexible_load:
        power_var = model.Shift_Load_Down_MW[resource, timepoint]
    else:
        power_var = model.Provide_Power_MW[resource, timepoint]

    return power_var * model.variable_cost_per_mwh[model.technology[resource]]

resolve_model.Variable_Cost_In_Timepoint = Expression(resolve_model.RESOURCES,
                                                      resolve_model.TIMEPOINTS,
                                                      rule=define_variable_cost_in_timepoint)

def define_start_cost_in_timepoint(model, r, tmp):
    """Calculates start costs for each dispatchable resource in each timepoint.

    Args:
        r: dispatchable resource
        tmp: timepoint
    """
    return (
        model.Start_Capacity_MW[r, tmp] *
        model.startup_cost_per_mw[model.technology[r]]
    )
resolve_model.Start_Cost_In_Timepoint = Expression(
    resolve_model.DISPATCHABLE_RESOURCES,
    resolve_model.TIMEPOINTS,
    rule=define_start_cost_in_timepoint
)


def define_shutdown_cost_in_timepoint(model, r, tmp):
    """Calculates shutdown costs for each dispatchable resource in each timepoint.

    Args:
        r: dispatchable resource
        tmp: timepoint
    """
    return (
        model.Shut_Down_Units[r, tmp] *
        model.unit_size_mw[model.technology[r]] *
        model.shutdown_cost_per_mw[model.technology[r]]
    )
resolve_model.Shutdown_Cost_In_Timepoint = Expression(
    resolve_model.DISPATCHABLE_RESOURCES,
    resolve_model.TIMEPOINTS,
    rule=define_shutdown_cost_in_timepoint
)


def capital_cost_annual_in_period_dollars_rule(model, resource, period):
    # add levelized capital costs for all resource additions from previous periods and the current period
    # Note that capital cost inputs are in terms of kW and kWh instead of MW or MWh
    # because industry practice is to express levelized capital costs as $/kW-yr

    capital_cost_total = 0.0

    for vintage in model.VINTAGES:
        if period >= vintage:
            capital_cost_total += model.Build_Capacity_MW[resource, vintage] \
                                  * model.capital_cost_per_kw_yr[resource, vintage] * 10 ** 3

            # if storage, also add energy capacity costs
            if resource in model.NEW_BUILD_STORAGE_RESOURCES:
                capital_cost_total += model.Build_Storage_Energy_Capacity_MWh[resource, vintage] \
                                      * model.energy_storage_cost_per_kwh_yr[resource, vintage] * 10 ** 3

    return capital_cost_total


resolve_model.Capital_Cost_Annual_In_Period_Dollars = Expression(
    resolve_model.NEW_BUILD_RESOURCES,
    resolve_model.PERIODS,
    rule=capital_cost_annual_in_period_dollars_rule)


def fixed_o_and_m_annual_in_period_dollars_rule(model, resource, period):

    fixed_om_total = 0.0

    # Fixed O&M for all planned capacity that is still operational.
    # For storage, this is only the power-related portion of Fixed O&M
    fixed_om_total += model.Operational_Planned_Capacity_MW[resource, period] \
                      * model.planned_capacity_fixed_o_and_m_dollars_per_kw_yr[resource, period] * 10 ** 3

    # Energy/duration-related portion of Fixed O&M for storage
    # Note: storage retirements are not currently allowed, so for storage energy capacity, planned = operational
    if resource in model.STORAGE_RESOURCES:
        fixed_om_total += model.planned_storage_energy_capacity_mwh[resource, period] \
            * model.planned_storage_energy_capacity_fixed_o_and_m_dollars_per_kwh_yr[resource, period]  * 10 ** 3

    # Fixed O&M for new build resources, which varies by installation date (vintage)
    if resource in model.NEW_BUILD_RESOURCES:
        for vintage in model.VINTAGES:
            if period >= vintage:
                fixed_om_total += model.Operational_New_Capacity_In_Period_By_Vintage_MW[resource, period, vintage] \
                                  * model.new_capacity_fixed_o_and_m_dollars_per_kw_yr[resource, vintage] * 10 ** 3

                # if storage, also add fixed O&M costs for maintaining energy capacity
                # Note: storage retirements are not currently allowed, so new = operational.
                if resource in model.NEW_BUILD_STORAGE_RESOURCES:
                    fixed_om_total += model.Build_Storage_Energy_Capacity_MWh[resource, vintage] \
                                      * model.new_energy_capacity_fixed_o_and_m_dollars_per_kwh_yr[resource, vintage] \
                                      * 10 ** 3

    return fixed_om_total


resolve_model.Fixed_OM_Annual_In_Period_Dollars = Expression(
    resolve_model.RESOURCES_WITH_MW_CAPACITY,
    resolve_model.PERIODS,
    rule=fixed_o_and_m_annual_in_period_dollars_rule)


def total_cost_rule(model):
    """
    Total incremental cost of the new resources + system operational costs including variable and fuel costs,
    and cost of unserved energy and unserved reserves.
    :param model:
    :return:
    """

    # ### Annual (periodic) costs ### #

    # Capital and Fixed costs of existing and new resources
    capital_and_fixed_resource_costs = float()
    for period in model.PERIODS:
        for resource in model.RESOURCES_WITH_MW_CAPACITY:
            capital_and_fixed_resource_costs += \
                model.Fixed_OM_Annual_In_Period_Dollars[resource, period] * model.discount_factor[period]

            # for new resources, add capital costs
            if resource in model.NEW_BUILD_RESOURCES:
                capital_and_fixed_resource_costs += \
                    model.Capital_Cost_Annual_In_Period_Dollars[resource, period] * model.discount_factor[period]
        # Flexible Load fixed costs
        for resource in model.FLEXIBLE_LOAD_RESOURCES:
            capital_and_fixed_resource_costs += \
                model.Flexible_Load_DR_Cost[resource, period] * model.discount_factor[period]

    # Transmission costs
    transmission_costs = float()
    fully_deliverable_tuning_costs = float()
    for p in model.PERIODS:
        for tx_zone in model.TX_ZONES:
            transmission_costs += model.New_Transmission_Capacity_MW[tx_zone, p] \
                * model.tx_deliverability_cost_per_mw_yr[tx_zone] * model.discount_factor[p]
        # Many new renewable resources have both zero cost fully deliverable and energy only transmission availability.
        # In reality the fully deliverable portion would likely be picked first,
        # so add a tiny tuning cost on new energy only capacity to guide the model to pick fully deliverable first
        for r in model.TX_DELIVERABILITY_RESOURCES:
            fully_deliverable_tuning_costs += model.Energy_Only_Installed_Capacity_MW[r, p] \
                * model.favor_deliverability_tuning_cost * model.discount_factor[p]

    if model.allow_tx_build:
        transmission_build_costs = float()
        for (p, v) in model.PERIOD_VINTAGES:
            for l in model.TRANSMISSION_LINES_NEW:
                transmission_build_costs += (model.New_Tx_Period_Vintage_Build_Cost[l, p, v] * model.discount_factor[p])

    # Add a tiny additional cost on localizing capacity
    # This forces the model to only install the minimum amount of local capacity necessary to satisfy local constraints
    local_capacity_tuning_costs = float()
    for p in model.PERIODS:
        for r in model.LOCAL_CAPACITY_RESOURCES:
            local_capacity_tuning_costs += model.Local_New_Capacity_MW[r, p] \
                * model.local_capacity_tuning_cost * model.discount_factor[p]
            if r in model.LOCAL_CAPACITY_STORAGE_RESOURCES:
                local_capacity_tuning_costs += model.Local_New_Storage_Energy_Capacity_MWh[r, p] \
                    * model.local_capacity_tuning_cost * model.discount_factor[p]

    # incremental cost per MMBtu of blending biogas into the natural gas pipeline
    # this cost could be negative if biogas is cheaper than natural gas
    incremental_pipeline_biogas_cost = float()
    for p in model.PERIODS:
        incremental_pipeline_biogas_cost += \
            model.Pipeline_Biogas_Consumption_MMBtu_Per_Year[p] \
            * model.incremental_pipeline_biogas_cost_per_mmbtu[p] \
            * model.discount_factor[p]

    # ### Hourly costs ### #
    variable_costs = float()
    fuel_costs = float()
    unit_start_costs = float()
    unit_shutdown_costs = float()
    unserved_energy_costs = float()
    overgen_costs = float()
    scheduled_curtailment_costs = float()
    upward_reg_violation_costs = float()
    downward_reg_violation_costs = float()
    upward_lf_reserve_violation_costs = float()
    downward_lf_reserve_violation_costs = float()
    spin_violation_costs = float()
    hurdle_rate_costs = float()

    for tmp in model.TIMEPOINTS:

        timepoint_weight = model.day_weight[model.day[tmp]] * model.discount_factor[model.period[tmp]]

        # ### Resource hourly costs ### #
        for r in model.RESOURCES:

            # Variable costs, excluding fuel
            variable_costs += model.Variable_Cost_In_Timepoint[r, tmp] * timepoint_weight

            # Thermal fuel cost
            if r in model.THERMAL_RESOURCES:
                fuel_costs += model.Fuel_Cost_Dollars_Per_Timepoint[r, tmp] * timepoint_weight

            if r in model.DISPATCHABLE_RESOURCES:
                unit_start_costs += (
                    model.Start_Cost_In_Timepoint[r, tmp] *
                    timepoint_weight
                )

                unit_shutdown_costs += (
                    model.Shutdown_Cost_In_Timepoint[r, tmp] *
                    timepoint_weight
                )

            # Scheduled curtailment costs
            # the assumed net cost of procuring additional renewable energy certificates
            # for each curtailable resource that isn't covered under an RPS target
            if r not in model.RPS_ELIGIBLE_RESOURCES:
                if r in model.CURTAILABLE_VARIABLE_RESOURCES:
                    scheduled_curtailment_costs += model.curtailment_cost_per_mwh[model.zone[r], model.period[tmp]] \
                        * model.Scheduled_Curtailment_MW[r, tmp] \
                        * timepoint_weight

        # ### Hurdle rates ### #
        # Only for unspecified power because dedicated imports and exports aren't charged hurdle rates
        for line in model.TRANSMISSION_LINES:
            hurdle_rate_costs += (model.Hurdle_Cost_Per_Timepoint_Positive_Direction[line, tmp]
                                  + model.Hurdle_Cost_Per_Timepoint_Negative_Direction[line, tmp]) \
                * timepoint_weight

        # add in hurdle rates for semi storage zones transmitted power
        if model.allow_semi_storage_zones:
            for ssz in model.SEMI_STORAGE_ZONES:
                hurdle_rate_costs += (model.SSZ_Positive_Transmit_Power_MW[ssz, tmp]
                                     * model.ssz_positive_direction_hurdle_rate_per_mw[ssz, model.period[tmp]]
                                     + model.SSZ_Negative_Transmit_Power_MW[ssz, tmp]
                                     * model.ssz_negative_direction_hurdle_rate_per_mw[ssz, model.period[tmp]]) \
                    * timepoint_weight

        # ### Penalties ### #
        # Unserved energy and overgeneration penalties for each zone
        for z in model.ZONES:
            # Unserved energy costs
            if model.allow_unserved_energy:
                unserved_energy_costs += model.Unserved_Energy_MW[z, tmp] * model.unserved_energy_penalty_per_mw \
                    * timepoint_weight
            # Overgen costs
            overgen_costs += model.Overgeneration_MW[z, tmp] * model.overgen_penalty_per_mw \
                * timepoint_weight

        # Reserve violation penalties
        # spinning reserve violation costs
        spin_violation_costs += model.Spin_Violation_MW[tmp] \
            * model.spin_violation_penalty_per_mw * timepoint_weight

        # Upward regulation violation costs
        upward_reg_violation_costs += model.Upward_Reg_Violation_MW[tmp] \
            * model.upward_reg_violation_penalty_per_mw * timepoint_weight
        # Downward regulation violation costs
        downward_reg_violation_costs += model.Downward_Reg_Violation_MW[tmp] \
            * model.downward_reg_violation_penalty_per_mw * timepoint_weight

        # Upward load-following reserve violation costs
        upward_lf_reserve_violation_costs += model.Upward_LF_Reserve_Violation_MW[tmp] \
            * model.upward_lf_reserve_violation_penalty_per_mw * timepoint_weight
        # Downward load-following reserve violation costs
        downward_lf_reserve_violation_costs += model.Downward_LF_Reserve_Violation_MW[tmp] \
            * model.downward_lf_reserve_violation_penalty_per_mw * timepoint_weight

    total_cost = \
        capital_and_fixed_resource_costs + \
        transmission_costs + \
        fully_deliverable_tuning_costs + \
        local_capacity_tuning_costs + \
        incremental_pipeline_biogas_cost + \
        variable_costs + \
        fuel_costs + \
        unit_start_costs + \
        unit_shutdown_costs + \
        hurdle_rate_costs + \
        unserved_energy_costs + \
        overgen_costs + \
        scheduled_curtailment_costs + \
        upward_reg_violation_costs + \
        downward_reg_violation_costs + \
        upward_lf_reserve_violation_costs + \
        downward_lf_reserve_violation_costs + \
        spin_violation_costs

    if model.allow_tx_build:
        total_cost += transmission_build_costs

    return total_cost

resolve_model.Total_Cost = Objective(rule=total_cost_rule, sense=minimize)


###########################
# ##### CONSTRAINTS ##### #
###########################

# ##### Planning Reserve Margin Constraints ##### #

def PRM_Available_Planned_Import_MW(model, period):
    """
    If unspecified imports are allowed, the full planned import capacity counts toward PRM,
    except for any capacity that is reserved for planned dedicated (specified) imports
    due to external resources being modeled as balanced directly by the PRM zone
    (via the param) prm_import_resource_capacity_adjustment_mw (typically a negative number)
    If unspecified imports are not allowed, include only new specified renewables on existing transmission.
    """
    if model.allow_unspecified_import_contribution[period]:
        return (model.prm_planned_import_capacity_mw[period] +
                model.prm_import_resource_capacity_adjustment_mw[period])
    else:
        return sum(model.import_on_existing_tx[resource] *
                   model.tx_import_capacity_fraction[resource] *
                   model.Operational_Capacity_MW[resource, period]
                   for resource in model.TX_DELIVERABILITY_RESOURCES)

resolve_model.PRM_Available_Planned_Import_MW = Expression(
    resolve_model.PERIODS,
    rule=PRM_Available_Planned_Import_MW)


def planning_reserve_margin_rule(model, period):
    """
    Ensure that there is enough capacity to meet a percentage - the planning_reserve_margin - above peak load.
    :param model:
    :param period:
    :return:
    """
    # Sum the capacity of firm capacity technologies,
    # This will generally include thermal, (large-scale) hydro, conventional DR, and firm RPS technologies
    # net_qualifying_capacity_fraction derates the capacity that is used in the PRM constraint
    # relative to the installed capacity of the resource
    firm_capacity = 0.0
    for resource in model.PRM_FIRM_CAPACITY_RESOURCES:
        firm_capacity += \
            model.Operational_NQC_MW[resource, period]

    storage_elcc = 0.0
    for resource in model.PRM_STORAGE_RESOURCES:
        storage_elcc += model.ELCC_Storage_MW[resource, period]

    # renewables imported on existing tx capacity don't appear here because existing import
    # capacity is already included via prm_planned_import_capacity_mw.
    # renewables imported on new transmission have an assumed per MW contribution to the PRM
    # of tx_import_capacity_fraction
    new_renewable_import_capacity = 0.0
    for resource in model.TX_DELIVERABILITY_RESOURCES:
        if model.import_on_new_tx[resource]:
            new_renewable_import_capacity += model.Fully_Deliverable_Installed_Capacity_MW[resource, period] \
                * model.tx_import_capacity_fraction[resource]

    return firm_capacity \
        + model.PRM_Available_Planned_Import_MW[period] \
        + storage_elcc \
        + new_renewable_import_capacity \
        + model.ELCC_Variable_Renewables_MW[period] \
        >= model.PRM_Peak_Load_MW[period] * (1 + model.planning_reserve_margin[period])

resolve_model.Planning_Reserve_Margin_Constraint = Constraint(resolve_model.PERIODS,
                                                              rule=planning_reserve_margin_rule)


def elcc_surface_rule(model, period, elcc_surface_facet):
    """
    Write a constraint for each facet of the ELCC surface that defines the ELCC of
    all variable renewables in the PRM zone via their installed capacity and capacity factor
    note: imported variable renewables are included in the PRM elsewhere
    - the ELCC surface applies to just the ones located in the PRM zone
    :param model:
    :param elcc_surface_facet:
    :param period:
    :return:
    """

    # Calculate the energy from variable resources in each period that contributes to the elcc surfaces
    # such that the elcc implied by each facet of the surface can be calculated below
    solar_fraction_of_annual_load = 0.0
    wind_fraction_of_annual_load = 0.0

    for resource in model.PRM_VARIABLE_RENEWABLE_RESOURCES:
        # existing renewable resources are assumed to be fully deliverable,
        # whereas a choice is made for new renewable resources whether to be energy only or fully deliverable
        if resource in model.TX_DELIVERABILITY_RESOURCES:
            elcc_surface_capacity = model.Fully_Deliverable_Installed_Capacity_MW[resource, period]
        else:
            elcc_surface_capacity = model.Operational_Capacity_MW[resource, period]

        if model.elcc_solar_bin[resource]:
            solar_fraction_of_annual_load += \
                elcc_surface_capacity * model.hours_per_year * model.capacity_factor[resource]\
                / model.prm_annual_load_mwh[period]
        elif model.elcc_wind_bin[resource]:
            wind_fraction_of_annual_load += \
                elcc_surface_capacity * model.hours_per_year * model.capacity_factor[resource] \
                / model.prm_annual_load_mwh[period]

    solar_elcc_mw_per_fraction_of_annual_load = \
        model.solar_coefficient[elcc_surface_facet] * model.prm_peak_load_mw[period]

    solar_elcc_mw = solar_elcc_mw_per_fraction_of_annual_load * solar_fraction_of_annual_load

    wind_elcc_mw_per_fraction_of_annual_load = \
        model.wind_coefficient[elcc_surface_facet] * model.prm_peak_load_mw[period]

    wind_elcc_mw = wind_elcc_mw_per_fraction_of_annual_load * wind_fraction_of_annual_load

    intercept_elcc_mw = model.facet_intercept[elcc_surface_facet] * model.prm_peak_load_mw[period]

    facet_elcc_mw = solar_elcc_mw + wind_elcc_mw + intercept_elcc_mw

    return model.ELCC_Variable_Renewables_MW[period] <= facet_elcc_mw

resolve_model.ELCC_Surface_Constraint = Constraint(resolve_model.PERIODS,
                                                   resolve_model.ELCC_SURFACE_FACETS,
                                                   rule=elcc_surface_rule)


def elcc_storage_power_rule(model, storage_resource, period):
    """
    The ELCC of a storage resource must be less than or equal to the power capacity of the resource
    This constraint works in conjunction with ELCC_Storage_Duration_Constraint to define storage ELCC
    because storage devices with short durations will not be able to contribute all of their power capacity to ELCC
    :param model:
    :param storage_resource:
    :param period:
    :return:
    """
    return (
        model.ELCC_Storage_MW[storage_resource, period]
        <=
        model.Operational_NQC_MW[storage_resource, period]
    )

resolve_model.ELCC_Storage_Power_Constraint = Constraint(resolve_model.PRM_STORAGE_RESOURCES,
                                                         resolve_model.PERIODS,
                                                         rule=elcc_storage_power_rule)


def elcc_storage_duration_rule(model, storage_resource, period):
    """
    The ELCC of a storage resource must be less than or equal to the energy duration of the resource
    divided by the number of hours of storage duration that it would take to count for full ELCC
    This constraint works in conjunction with ELCC_Storage_Power_Constraint to define storage ELCC
    because storage devices with short durations will not be able to contribute all of their power capacity to ELCC
    :param model:
    :param storage_resource:
    :param period:
    :return:
    """
    return (
        model.ELCC_Storage_MW[storage_resource, period]
        <=
        model.net_qualifying_capacity_fraction[storage_resource] *
        model.Total_Storage_Energy_Capacity_MWh[storage_resource, period] /
        model.elcc_hours
    )

resolve_model.ELCC_Storage_Duration_Constraint = Constraint(resolve_model.PRM_STORAGE_RESOURCES,
                                                            resolve_model.PERIODS,
                                                            rule=elcc_storage_duration_rule)

# ### Multi-day Energy Sufficiency ### #
if resolve_model.energy_sufficiency:
    # ### Sets for energy sufficiency ### #
    resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS = Set(dimen=2,
        ordered=True,
        doc='Two-dimensional set composed of (ENERGY_SUFFICIENCY_HORIZON_NAMES, HORIZON_IDS)')

    def horizon_init(model):
        return list(set([horizon[0] for horizon in model.ENERGY_SUFFICIENCY_HORIZON_GROUPS]))

    resolve_model.ENERGY_SUFFICIENCY_HORIZON_NAMES = Set(initialize=horizon_init,
        ordered=True,
        doc='Name (decsription of duration) of energy sufficiency constraint')

    # ENERGY_SUFFICIENCY_FIRM_RESOURCES are all FIRM_CAPACITY_PRM_RESOURCES except for
    # HYDRO_RESOURCES and CONVENTIONAL_DR_RESOURCES because they may be energy constrained
    resolve_model.ENERGY_SUFFICIENCY_FIRM_RESOURCES = (
        resolve_model.PRM_FIRM_CAPACITY_RESOURCES -
        resolve_model.PRM_CONVENTIONAL_DR_RESOURCES -
        resolve_model.PRM_HYDRO_RESOURCES
    )

    if resolve_model.allow_ee_investment:
        resolve_model.ENERGY_LIMITED_RESOURCES = (
            resolve_model.PRM_VARIABLE_RENEWABLE_RESOURCES |
            resolve_model.PRM_HYDRO_RESOURCES |
            resolve_model.PRM_EE_PROGRAMS
        )
    else:
        resolve_model.ENERGY_LIMITED_RESOURCES = (
            resolve_model.PRM_VARIABLE_RENEWABLE_RESOURCES |
            resolve_model.PRM_HYDRO_RESOURCES
        )

    # ### energy sufficiency params ### #
    resolve_model.energy_sufficiency_horizon_hours = Param(
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_NAMES,
        within=PositiveIntegers,
        doc='Effective duration (hours) of each energy sufficiency constraint in this group')

    resolve_model.energy_sufficiency_average_capacity_factor = Param(
        resolve_model.ENERGY_LIMITED_RESOURCES,
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS,
        resolve_model.PERIODS,
        within=NonNegativeReals,
        doc='Capacity factor contributions from EE can be greater than 1 depending on definition')

    resolve_model.energy_sufficiency_average_load_aMW = Param(
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS,
        resolve_model.PERIODS,
        within=NonNegativeReals,
        doc='Average energy demanded across the length of each energy sufficiency constraint group')

    # ### energy sufficiency vars, expressions, and constraints ### #
    resolve_model.Energy_Sufficiency_Available_Storage_aMW = Var(
        resolve_model.STORAGE_RESOURCES,
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_NAMES,
        resolve_model.PERIODS,
        within=NonNegativeReals)


    def energy_sufficiency_storage_power_bound_def(model, resource, sufficiency_horizon, period):
        """Constrain storage energy sufficiency contribution by its power capacity.
        """
        return (model.Energy_Sufficiency_Available_Storage_aMW[resource, sufficiency_horizon, period] <=
                model.Operational_Capacity_MW[resource, period])

    resolve_model.Energy_Sufficiency_Storage_Power_Bound = Constraint(
        resolve_model.PRM_STORAGE_RESOURCES,
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_NAMES,
        resolve_model.PERIODS,
        rule=energy_sufficiency_storage_power_bound_def)


    def energy_sufficiency_storage_energy_def(model, resource, sufficiency_horizon, period):
        """        For energy capacity, spread the total energy capacity of the storage
        resource over the energy_sufficiency_horizon_hours, accounting for discharge efficiency
        in getting energy out of the storage resource.
        """
        return (model.Total_Storage_Energy_Capacity_MWh[resource, period]
               * model.discharging_efficiency[model.technology[resource]]
               / model.energy_sufficiency_horizon_hours[sufficiency_horizon])

    resolve_model.Energy_Sufficiency_Storage_Energy_aMW = Expression(
        resolve_model.PRM_STORAGE_RESOURCES,
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_NAMES,
        resolve_model.PERIODS,
        rule=energy_sufficiency_storage_energy_def)


    def energy_sufficiency_storage_energy_bound_def(model, resource, sufficiency_horizon, period):
        """Constrain storage energy sufficiency contribution by energy capacity.
        """
        return (model.Energy_Sufficiency_Available_Storage_aMW[resource, sufficiency_horizon, period] <=
                model.Energy_Sufficiency_Storage_Energy_aMW[resource, sufficiency_horizon, period])

    resolve_model.Energy_Sufficiency_Storage_Energy_Bound_aMW = Constraint(
        resolve_model.PRM_STORAGE_RESOURCES,
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_NAMES,
        resolve_model.PERIODS,
        rule=energy_sufficiency_storage_energy_bound_def)


    def energy_sufficiency_available_planned_import_amw_def(model, sufficiency_horizon, horizon_id, period):
        """
        If unspecified imports are allowed, the full planned import capacity counts toward PRM,
            except for any capacity that is reserved for planned dedicated (specified) imports
            due to external resources being modeled as balanced directly by the PRM zone
            (via the param) prm_import_resource_capacity_adjustment_mw (typically a negative number)
        If unspecified imports are not allowed, include only new specified renewables on existing transmission.

        """
        if model.allow_unspecified_import_contribution[period]:
            return (model.prm_planned_import_capacity_mw[period] +
                    model.prm_import_resource_capacity_adjustment_mw[period])
        else:
            return sum(model.import_on_existing_tx[resource] *
                       model.energy_sufficiency_average_capacity_factor[resource, sufficiency_horizon, horizon_id, period] *
                       model.Operational_Capacity_MW[resource, period]
                       for resource in model.TX_DELIVERABILITY_RESOURCES)

    resolve_model.Energy_Sufficiency_Available_Planned_Import_aMW = Expression(
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS,
        resolve_model.PERIODS,
        rule=energy_sufficiency_available_planned_import_amw_def)


    def energy_sufficiency_firm_capacity_amw_def(model, period):
        """Calculate contribution of all ENERGY_SUFFICIENCY_FIRM_RESOURCES to each energy sufficiency constraint.
        """
        return sum(model.Operational_NQC_MW[resource, period]
                   for resource in model.ENERGY_SUFFICIENCY_FIRM_RESOURCES)

    resolve_model.Energy_Sufficiency_Firm_Capacity_aMW = Expression(
        resolve_model.PERIODS,
        rule=energy_sufficiency_firm_capacity_amw_def)


    def energy_sufficiency_storage_contribution_amw_def(model, sufficiency_horizon, period):
        """Calculate contribution of all PRM_STORAGE_RESOURCES to each energy sufficiency constraint.
        """
        return sum(model.Energy_Sufficiency_Available_Storage_aMW[resource, sufficiency_horizon, period]
                   for resource in model.PRM_STORAGE_RESOURCES)

    resolve_model.Energy_Sufficiency_Storage_Contribution_aMW = Expression(
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_NAMES,
        resolve_model.PERIODS,
        rule=energy_sufficiency_storage_contribution_amw_def)


    def energy_sufficiency_variable_renewables_amw_def(model, sufficiency_horizon, horizon_id, period):
        """Calculation contribution of all PRM_VARIABLE_RENEWABLE_RESOURCES to each energy sufficiency constraint.

        PRM_VARIABLE_RENEWABLE_RESOURCES are existing renewables that are located in the PRM zone
        or new renewables that are located in the PRM zone. New renewable resources that lie on the
        other side of a transmission constraint are defined accounted for in Energy_Sufficiency_Import_Renewables_aMW
        and Energy_Sufficiency_Available_Planned_Import_aMW.
        """
        prm_variable_renewables_contribution = float()
        for resource in model.PRM_VARIABLE_RENEWABLE_RESOURCES:
            prm_variable_renewables_contribution += model.Operational_Capacity_MW[resource, period] \
                * model.energy_sufficiency_average_capacity_factor[resource, sufficiency_horizon, horizon_id, period]

        return prm_variable_renewables_contribution

    resolve_model.Energy_Sufficiency_Variable_Renewables_aMW = Expression(
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS,
        resolve_model.PERIODS,
        rule=energy_sufficiency_variable_renewables_amw_def)


    def energy_sufficiency_import_renewables_amw_def(model, sufficiency_horizon, horizon_id, period):
        """Calculate contribution of new renewables traveling on new transmission into the PRM zone.

        Operational_Capacity_MW instead of Fully_Deliverable_Installed_Capacity_MW
        because we think that the times when this constraint would be binding are not times
        where transmission constraints are also binding.
        """
        new_renewable_import_capacity = 0.0
        for resource in model.TX_DELIVERABILITY_RESOURCES:
            if model.import_on_new_tx[resource]:
                new_renewable_import_capacity += model.Operational_Capacity_MW[resource, period] \
                    * model.tx_import_capacity_fraction[resource]

        return new_renewable_import_capacity

    resolve_model.Energy_Sufficiency_Import_Renewables_aMW = Expression(
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS,
        resolve_model.PERIODS,
        rule=energy_sufficiency_import_renewables_amw_def)


    if resolve_model.allow_ee_investment:
        def energy_sufficiency_ee_amw_def(model, sufficiency_horizon, horizon_id, period):
            """Calculate contribution of EE resources to each energy sufficiency constraint.
            """
            return sum(model.Operational_Capacity_MW[resource, period] *
                       model.energy_sufficiency_average_capacity_factor[resource, sufficiency_horizon, horizon_id, period]
                       for resource in model.PRM_EE_PROGRAMS)

        resolve_model.Energy_Sufficiency_EE_aMW = Expression(
            resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS,
            resolve_model.PERIODS,
            rule=energy_sufficiency_ee_amw_def)


    def energy_sufficiency_hydro_amw_def(model, sufficiency_horizon, horizon_id, period):
        """Calculate contribution of hydro resources to each energy sufficiency constraint.
        """
        return sum(model.Operational_Capacity_MW[resource, period] *
                   model.energy_sufficiency_average_capacity_factor[resource, sufficiency_horizon, horizon_id, period]
                   for resource in model.PRM_HYDRO_RESOURCES)

    resolve_model.Energy_Sufficiency_Hydro_aMW = Expression(
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS,
        resolve_model.PERIODS,
        rule=energy_sufficiency_hydro_amw_def)

    def energy_sufficiency_conventional_dr_rule(model, dr_resource, sufficiency_horizon, period):
        """Constrains the energy contribution of shed DR within each horizon group by annual hours of dispatch available.

        The binding conventional capacity factor constraint is either:
            1. min(1.0, energy sufficiency hours / daily call hours limit)
                The limit associated with daily capacity factor scales with horizon hours up to 1.0
                (i.e., if horizon and call hours are both the same duration)
            2. annual capacity factor

        """
        conventional_dr_annual_capacity_factor_limit = (
            model.conventional_dr_availability_hours_per_year[dr_resource, period] /
            model.energy_sufficiency_horizon_hours[sufficiency_horizon]
        )

        # if horizon < 1-day, the contribution is limited by the number of hours within the horizon
        # and the number of hours that the resource could be called if dispatched at the daily capacity factor
        if model.energy_sufficiency_horizon_hours[sufficiency_horizon] < 24:
            conventional_dr_daily_capacity_factor_limit = min(
                1.0,
                model.conventional_dr_daily_capacity_factor[dr_resource, period] *
                (24 / model.energy_sufficiency_horizon_hours[sufficiency_horizon])
            )
        # if horizon > 1-day, the capacity factor is the daily capacity factor
        else:
            conventional_dr_daily_capacity_factor_limit = (
               model.conventional_dr_daily_capacity_factor[dr_resource, period]
            )

        conventional_dr_capacity_factor_bound = min(
            conventional_dr_annual_capacity_factor_limit,
            conventional_dr_daily_capacity_factor_limit
        )

        return (
            conventional_dr_capacity_factor_bound * model.Operational_Capacity_MW[dr_resource, period]
        )

    resolve_model.Energy_Sufficiency_Conventional_DR_aMW = Expression(
        resolve_model.PRM_CONVENTIONAL_DR_RESOURCES,
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_NAMES,
        resolve_model.PERIODS,
        rule=energy_sufficiency_conventional_dr_rule)

    def energy_sufficiency_total_conventional_dr_contribution_rule(model, sufficiency_horizon, period):
        return sum(
            model.Energy_Sufficiency_Conventional_DR_aMW[dr_resource, sufficiency_horizon, period]
            for dr_resource in model.PRM_CONVENTIONAL_DR_RESOURCES
        )

    resolve_model.Energy_Sufficiency_Total_Conventional_DR_aMW = Expression(
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_NAMES,
        resolve_model.PERIODS,
        rule=energy_sufficiency_total_conventional_dr_contribution_rule
    )


    def energy_sufficiency_total_resources_amw_def(model, sufficiency_horizon, horizon_id, period):
        """Calculate the total contribution across all resources types.
        """
        total_contribution = float()

        total_contribution += (model.Energy_Sufficiency_Firm_Capacity_aMW[period] +
                               model.Energy_Sufficiency_Storage_Contribution_aMW[sufficiency_horizon, period] +
                               model.Energy_Sufficiency_Variable_Renewables_aMW[sufficiency_horizon, horizon_id, period] +
                               model.Energy_Sufficiency_Import_Renewables_aMW[sufficiency_horizon, horizon_id, period] +
                               model.Energy_Sufficiency_Hydro_aMW[sufficiency_horizon, horizon_id, period] +
                               model.Energy_Sufficiency_Available_Planned_Import_aMW[sufficiency_horizon, horizon_id, period] +
                               model.Energy_Sufficiency_Total_Conventional_DR_aMW[sufficiency_horizon, period])

        if model.allow_ee_investment:
            total_contribution += model.Energy_Sufficiency_EE_aMW[sufficiency_horizon, horizon_id, period]

        return total_contribution

    resolve_model.Energy_Sufficiency_Total_Resources_aMW = Expression(
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS,
        resolve_model.PERIODS,
        rule=energy_sufficiency_total_resources_amw_def)


    def energy_sufficiency_rule(model, sufficiency_horizon, horizon_id, period):
        """Constrain total contribution of resources providing energy to meet energy demand.
        """
        return (model.Energy_Sufficiency_Total_Resources_aMW[sufficiency_horizon, horizon_id, period] >=
                model.energy_sufficiency_average_load_aMW[sufficiency_horizon, horizon_id, period])

    resolve_model.Energy_Sufficiency_Constraint = Constraint(
        resolve_model.ENERGY_SUFFICIENCY_HORIZON_GROUPS,
        resolve_model.PERIODS,
        rule=energy_sufficiency_rule)


# ##### Local Capacity Constraints ##### #
def local_capacity_limit_rule(model, resource, period):
    """
    Limit the amount of new capacity of each resource that can be installed in local capacity areas.
    :param model:
    :param resource:
    :param period:
    :return:
    """
    return model.Local_New_Capacity_MW[resource, period] <= model.capacity_limit_local_mw[resource, period]

resolve_model.Local_Capacity_Limit_Constraint = Constraint(resolve_model.LOCAL_CAPACITY_LIMITED_RESOURCES,
                                                           resolve_model.PERIODS,
                                                           rule=local_capacity_limit_rule)


def local_capacity_resource_system_limit_rule(model, resource, period):
    """
    Generic system resources are assumed to be preferentially built in local areas,
    so their system capacity can count fully towards local capacity
    A tuning cost in the objective forces Local_New_Capacity_MW to be as small as possible.
    Also, local capacity needs are currently specified for new builds only,
    so existing capacity has already been subtracted.  This is why the new installed capacity only is used here.
    Energy efficiency resources are handled separately from other resources.
    :param model:
    :param resource:
    :param period:
    :return:
    """
    if resource in model.EE_PROGRAMS:
        return model.Local_New_Capacity_MW[resource, period] == \
               model.Operational_New_Capacity_MW[resource, period] \
               * model.ee_btm_local_capacity_mw_per_amw[resource]
    else:
        return model.Local_New_Capacity_MW[resource, period] <= \
               model.Operational_New_Capacity_MW[resource, period]


resolve_model.Local_Capacity_Resource_Definition_Constraint = Constraint(resolve_model.LOCAL_CAPACITY_RESOURCES,
                                                                         resolve_model.PERIODS,
                                                                         rule=local_capacity_resource_system_limit_rule)


def local_storage_energy_system_limit_rule(model, resource, period):
    """
    Local new storage energy capacity should be <= the system new energy capacity
    :param model:
    :param resource:
    :param period:
    :return:
    """
    return model.Local_New_Storage_Energy_Capacity_MWh[resource, period] <= \
        model.Cumulative_New_Storage_Energy_Capacity_MWh[resource, period]

resolve_model.Local_Storage_Energy_System_Limit_Constraint = Constraint(resolve_model.LOCAL_CAPACITY_STORAGE_RESOURCES,
                                                                        resolve_model.PERIODS,
                                                                        rule=local_storage_energy_system_limit_rule)


def local_storage_minimum_duration_rule(model, storage_resource, period):
    """
    Minimum duration for new storage resources located in local areas
    :param model:
    :param storage_resource:
    :param period:
    :return:
    """
    return model.Local_New_Storage_Energy_Capacity_MWh[storage_resource, period] \
        >= model.Local_New_Capacity_MW[storage_resource, period] \
        * model.min_duration_h[model.technology[storage_resource]]

resolve_model.Min_Local_Storage_Duration_Constraint = Constraint(resolve_model.LOCAL_CAPACITY_STORAGE_RESOURCES,
                                                                 resolve_model.PERIODS,
                                                                 rule=local_storage_minimum_duration_rule)


def nonlocal_storage_minimum_duration_rule(model, storage_resource, period):
    """
    Storage resources not located in local areas must have min_duration_h.
    Cumulative - Local = NonLocal for both MW and MWh.
    A similar constraint exists on the system-wide level.
    :param model:
    :param storage_resource:
    :param period:
    :return:
    """
    return model.Cumulative_New_Storage_Energy_Capacity_MWh[storage_resource, period] \
        - model.Local_New_Storage_Energy_Capacity_MWh[storage_resource, period] \
        >= (model.Operational_New_Capacity_MW[storage_resource, period]
            - model.Local_New_Capacity_MW[storage_resource, period]) \
        * model.min_duration_h[model.technology[storage_resource]]

resolve_model.Min_NonLocal_Storage_Duration_Constraint = Constraint(resolve_model.LOCAL_CAPACITY_STORAGE_RESOURCES,
                                                                    resolve_model.PERIODS,
                                                                    rule=nonlocal_storage_minimum_duration_rule)


def storage_local_duration_nqc_rule(model, storage_resource, period):
    """
    Similar to the system-level storage ELCC constraints,
    the local capacity contribution of a storage resource must be less than or equal to
    the energy duration of the resource divided by the number of hours of storage duration
    that it would take to count for full ELCC/NQC
    :param model:
    :param storage_resource:
    :param period:
    :return:
    """
    return model.Local_New_Capacity_MW[storage_resource, period] <= \
        model.Local_New_Storage_Energy_Capacity_MWh[storage_resource, period] / model.elcc_hours

resolve_model.Storage_Local_Duration_NQC_Constraint = Constraint(resolve_model.LOCAL_CAPACITY_STORAGE_RESOURCES,
                                                                 resolve_model.PERIODS,
                                                                 rule=storage_local_duration_nqc_rule)


def local_capacity_deficiency_rule(model, period):
    """New capacity must be built to satisfy the combined capacity needs (local_capacity_deficiency_mw) of all local areas

    Args:
        model (pyo.AbstractModel)
        period (pyo.Set)

    Raises:
        RuntimeError: Ensure that every local resource has a capacity contribution defined.

    Returns:
        pyo.Constraint:
    """

    local_capacity_total = float()

    for resource in model.LOCAL_CAPACITY_RESOURCES:
        # system nqc assumed to be local nqc
        if resource in model.PRM_NQC_RESOURCES:
            local_capacity_total += \
                model.Local_New_Capacity_MW[resource, period] * model.net_qualifying_capacity_fraction[resource]
        # renewables located in local areas are assumed to have a fixed net qualifying capacity (NQC)
        elif resource in model.PRM_VARIABLE_RENEWABLE_RESOURCES:
            local_capacity_total += \
                model.Local_New_Capacity_MW[resource, period] * model.local_variable_renewable_nqc_fraction[resource]
        # EE local capacity avoids T & D losses.
        elif resource in model.PRM_EE_PROGRAMS:
            local_capacity_total += model.Local_New_Capacity_MW[resource, period] \
                                    * (1 + model.ee_t_and_d_losses_fraction[resource])
        # raise an error if anything has been left out
        else:
            raise RuntimeError('must define local capacity for all local resources')

    # Transmission expansion might contribute to local capacity
    if model.allow_tx_build:
        for line in model.TRANSMISSION_LINES_NEW:
            local_capacity_total += model.New_Tx_Local_Capacity_Contribution_MW[line, period]

    return local_capacity_total >= model.local_capacity_deficiency_mw[period]


resolve_model.Local_Capacity_Deficiency_Constraint = Constraint(resolve_model.PERIODS,
                                                                rule=local_capacity_deficiency_rule)

# Retirements ########
# Retirement for planned and new capacity are treated separately because some constraints
# (local capacity and transmission deliverability) only relate to new capacity.


# Minimum cumulative planned retirements for every period (including forced and economic planned capacity retirements)
def minimum_planned_retirements_rule(model, resource, period):
    # NOTE: For the first period there is no forced retirement
    # because the planned capacity in the first period (an input) should already be net of any planned retirements.
    # The model can still choose economically retire planned capacity in the first period via other constraints.
    if period == model.first_period:
        return Constraint.Skip
    else:
        # the planned capacity input values may decrease from period to period, implying retirements by a certain date
        # this constraint forces retirements by that date, but also allows for the capacity to be retired earlier
        return model.cumulative_planned_capacity_subtractions_mw[resource, period] <= \
               model.Retire_Planned_Capacity_Cumulative_MW[resource, period]


resolve_model.Minimum_Planned_Retirements_Constraint = \
    Constraint(resolve_model.CAN_RETIRE_RESOURCES,
               resolve_model.PERIODS,
               rule=minimum_planned_retirements_rule)


# Minimum_Planned_Retirements_Constraint
# The planned capacity in the first period is equal to the cumulative planned additions
# this constraint works in concert with Minimum_Planned_Retirements_Constraint
# to force scheduled retirements by a specific date while also allowing the model freedom to retire resources earlier
def maximum_planned_retirements_rule(model, resource, period):
    return model.Retire_Planned_Capacity_Cumulative_MW[resource, period] <= \
           model.cumulative_planned_capacity_additions_mw[resource, period]

resolve_model.Maximum_Planned_Retirements_Constraint = \
    Constraint(resolve_model.CAN_RETIRE_RESOURCES,
               resolve_model.PERIODS,
               rule=maximum_planned_retirements_rule)


def retire_new_increasing_only_rule(model, resource, period, vintage):
    # retired capacity of each vintage is strictly increasing overtime - no mothballing

    # Don't allow retirements the year in which the resource was installed
    # there should be natural disincentives to do this, but just in case explicitly remove the option.
    # Also, the else below looks back to the previous period, which wouldn't exist when period == vintage
    if period == vintage:
        return model.Retire_New_Capacity_By_Vintage_Cumulative_MW[resource, period, vintage] == 0
    # From the second period onwards, retire new capacity that was built in the previous period.
    else:
        return model.Retire_New_Capacity_By_Vintage_Cumulative_MW[resource, period, vintage] >= \
               model.Retire_New_Capacity_By_Vintage_Cumulative_MW[resource, find_prev_period(model, period), vintage]


resolve_model.Retire_New_Increasing_Only_Constraint = \
    Constraint(resolve_model.CAN_RETIRE_RESOURCES_NEW,
               resolve_model.PERIOD_VINTAGES,
               rule=retire_new_increasing_only_rule)


def retire_new_upper_bound_rule(model, resource, period, vintage):
    # can't retire more capacity of a given vintage than was installed in the first place
    return model.Retire_New_Capacity_By_Vintage_Cumulative_MW[resource, period, vintage] <= \
           model.Build_Capacity_MW[resource, vintage]


resolve_model.Retire_New_Upper_Bound_Constraint = \
    Constraint(resolve_model.CAN_RETIRE_RESOURCES_NEW,
               resolve_model.PERIOD_VINTAGES,
               rule=retire_new_upper_bound_rule)


def min_operational_planned_capacity_rule(model, resource, period):
    """
    Retain (don't retire) a minimum amount of planned capacity in each period.
    Typically used to model factors outside the scope of the model that cause generation capacity to be retained.
    """
    if model.min_operational_planned_capacity_mw[resource, period] == 0:
        return Constraint.Skip
    else:
        return model.Operational_Planned_Capacity_MW[resource, period] \
            >= model.min_operational_planned_capacity_mw[resource, period]


resolve_model.Minimum_Operational_Planned_Capacity_Constraint = \
    Constraint(resolve_model.CAN_RETIRE_RESOURCES,
               resolve_model.PERIODS,
               rule=min_operational_planned_capacity_rule)


def min_cumulative_new_build_rule(model, new_build_resource, period):
    """
    For resources that can be built, how much cumulative capacity must be built by a certain year.
    Note that there is not currently an analogous constraint for storage energy capacity min new build,
    but any storage resource for which power capacity is installed via this constraint
    will be forced to have at least min_duration_h over the total power capacity of the resource.
    :param model:
    :param new_build_resource:
    :param period:
    :return:
    """
    return model.Operational_New_Capacity_MW[new_build_resource, period] \
        >= model.min_cumulative_new_build_mw[new_build_resource, period]

resolve_model.Minimum_Cumulative_New_Build_Constraint = Constraint(resolve_model.NEW_BUILD_RESOURCES,
                                                                   resolve_model.PERIODS,
                                                                   rule=min_cumulative_new_build_rule)


def capacity_limit_rule(model, capacity_limited_resource, period):
    """
    Limit on amount of capacity that can be installed for capacity-limited resources.
    For energy efficiency the limit should be specified in average MWs (aMW)
    :param model:
    :param capacity_limited_resource:
    :param period:
    :return:
    """
    return model.Operational_Capacity_MW[capacity_limited_resource, period] \
        <= model.capacity_limit_mw[capacity_limited_resource, period]


resolve_model.Capacity_Limit_Constraint = Constraint(resolve_model.CAPACITY_LIMITED_RESOURCES, resolve_model.PERIODS,
                                                     rule=capacity_limit_rule)


def storage_minimum_duration_rule(model, new_storage_resource, period):
    """
    Minimum duration for new storage by technology.
    Similar constraints are included for storage resources that can count towards local capacity needs,
    making this constraint redundant for those resources.
    :param model:
    :param new_storage_resource:
    :param period:
    :return:
    """
    return model.Cumulative_New_Storage_Energy_Capacity_MWh[new_storage_resource, period] \
        >= model.Operational_New_Capacity_MW[new_storage_resource, period] \
        * model.min_duration_h[model.technology[new_storage_resource]]


resolve_model.Min_Storage_Duration_Constraint = Constraint(resolve_model.NEW_BUILD_STORAGE_RESOURCES,
                                                           resolve_model.PERIODS,
                                                           rule=storage_minimum_duration_rule)


# ## Pipeline Biogas ## #
def maximum_pipeline_biogas_potential_rule(model, period):
    """
    Limit the amount of biogas consumption from the natural gas pipeline to a pre-defined quantity
    that represents the amount of biogas injected into the natural gas pipeline
    :param model:
    :param period:
    :return:
    """
    return model.Pipeline_Biogas_Consumption_MMBtu_Per_Year[period] <= \
        model.pipeline_biogas_available_mmbtu_per_year[period]

resolve_model.Maximum_Pipeline_Biogas_Potential_Constraint = Constraint(resolve_model.PERIODS,
                                                                        rule=maximum_pipeline_biogas_potential_rule)


def maximum_pipeline_biogas_consumption_rule(model, resource, timepoint):
    """
    Limit the amount of biogas consumption to the amount of natural gas consumption for each resource in each timepoint
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.Pipeline_Biogas_Consumption_MMBtu[resource, timepoint] <= \
        model.Fuel_Consumption_MMBtu[resource, timepoint]

resolve_model.Maximum_Pipeline_Biogas_Consumption_Constraint = Constraint(resolve_model.PIPELINE_BIOGAS_RESOURCES,
                                                                          resolve_model.TIMEPOINTS,
                                                                          rule=maximum_pipeline_biogas_consumption_rule)


def maximum_pipeline_biogas_generation_rule(model, resource, timepoint):
    """
    Limit the amount of biogas generation to the amount of natural gas generation for each resource in each timepoint
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.Pipeline_Biogas_Generation_MW[resource, timepoint] <= \
        model.Provide_Power_MW[resource, timepoint]

resolve_model.Maximum_Pipeline_Biogas_Generation_Constraint = Constraint(resolve_model.PIPELINE_BIOGAS_RESOURCES,
                                                                         resolve_model.TIMEPOINTS,
                                                                         rule=maximum_pipeline_biogas_generation_rule)


def minimum_pipeline_biogas_heat_rate_rule(model, resource, timepoint):
    """
    This constraint forces a minimum amount of biogas to be consumed per MW of generation
    given the modeling limitation that the heat rate of dispatchable generators is a combination of decision variables
    and therefore can't be multiplied by other decision variables.
    For some resources (the else in this constraint) the heat rate doesn't vary as a function of generator output,
    so the min heat rate = average = max
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    if resource in model.DISPATCHABLE_RESOURCES and \
            model.fuel_burn_intercept_mmbtu_per_hr[model.technology[resource]] > 0:
        return model.Pipeline_Biogas_Consumption_MMBtu[resource, timepoint] >= \
            model.Pipeline_Biogas_Generation_MW[resource, timepoint] * model.full_load_heat_rate_mmbtu_per_mwh[resource]
    else:
        return model.Pipeline_Biogas_Consumption_MMBtu[resource, timepoint] == \
            model.Pipeline_Biogas_Generation_MW[resource, timepoint] * model.full_load_heat_rate_mmbtu_per_mwh[resource]

resolve_model.Minimum_Pipeline_Biogas_Heat_Rate_Constraint = Constraint(resolve_model.PIPELINE_BIOGAS_RESOURCES,
                                                                        resolve_model.TIMEPOINTS,
                                                                        rule=minimum_pipeline_biogas_heat_rate_rule)


# ##### RPS constraints ##### #
def define_previously_banked_rps(model, period):
    """
    # RPS credits banked from previous period or planned spending of historical bank
    :param model:
    :param period:
    :return:
    """
    if not model.optimize_rps_banking:
        # if optimized banking is not enabled, no rps credits are banked from any previous period
        # other than those projected to be spent in a given period.
        # to completely eliminate banking, set rps_bank_planned_spend_mwh to zero in all periods
        return model.rps_bank_planned_spend_mwh[period]
    else:
        if period == model.first_period:
            # the first period starts with starting_rps_bank_mwh
            # starting_rps_bank_mwh can be zero if you don't want to start with any bank
            return model.starting_rps_bank_mwh / model.years_in_period[period]
        else:
            # Each period can have a different length (years_in_period) so rps credits that are banked
            # in a period must be multiplied by the years_in_period when the credits go into the bank (in prev_period).
            # The credits are divided by years_in_period when they come out of the bank in the subsequent period
            prev_period = find_prev_period(model, period)
            return model.Bank_RPS_MWh[prev_period] * \
                model.years_in_period[prev_period] / model.years_in_period[period]

resolve_model.Previously_Banked_RPS_MWh = Expression(resolve_model.PERIODS,
                                                     rule=define_previously_banked_rps)


def define_yearly_rps_storage_losses(model, period):
    """
    Derived variable that represents the total amount of storage losses in RPS zones over the course of a year.
    This will be zero if storage losses aren't counted against the RPS requirement.

    Storage losses count as curtailment on the assumption that RPS-eligible energy is going into storage.
    Storage losses are incurred when providing reserves because reserves will be dispatched some fraction of the time:
    the reserve_dispatch_fraction.
    :param model:
    :param period:
    :return:
    """
    yearly_storage_losses = 0.0

    if model.count_storage_losses_as_rps_curtailment:
        for storage_resource in model.STORAGE_RESOURCES:
            if model.zone[storage_resource] in model.RPS_ZONES:
                for timepoint in model.TIMEPOINTS:
                    if model.period[timepoint] == period:

                        charging_mwh = 0.0
                        discharging_mwh = 0.0

                        charging_mwh += model.Charge_Storage_MW[storage_resource, timepoint]
                        discharging_mwh += model.Provide_Power_MW[storage_resource, timepoint]

                        # Regulation reserve dispatch
                        if storage_resource in model.REGULATION_RESERVE_RESOURCES:
                            charging_mwh += model.Provide_Downward_Reg_MW[storage_resource, timepoint] \
                                * model.reg_dispatch_fraction
                            discharging_mwh += model.Provide_Upward_Reg_MW[storage_resource, timepoint] \
                                * model.reg_dispatch_fraction

                        # Load-following reserve dispatch
                        if storage_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
                            charging_mwh += model.Provide_LF_Downward_Reserve_MW[storage_resource, timepoint] \
                                * model.lf_reserve_dispatch_fraction
                            discharging_mwh += model.Provide_LF_Upward_Reserve_MW[storage_resource, timepoint] \
                                * model.lf_reserve_dispatch_fraction

                        # Calculate losses
                        # To calculate a yearly total, losses are weighted by day_weight
                        # The values charging_mwh/discharging_mwh represent the load/generation as seen by the grid
                        # For example, discharging_mwh represents energy put onto the grid by the storage device,
                        # which is less than the amount of energy taken
                        # out of the storage device if discharging_efficiency is < 100%
                        yearly_storage_losses += \
                            charging_mwh * model.day_weight[model.day[timepoint]] \
                            * (1.0 - model.charging_efficiency[model.technology[storage_resource]]) \
                            + discharging_mwh * model.day_weight[model.day[timepoint]] \
                            * (1.0 / model.discharging_efficiency[model.technology[storage_resource]] - 1.0)

    return yearly_storage_losses

resolve_model.RPS_Storage_Losses_MWh_Per_Year = Expression(resolve_model.PERIODS,
                                                           rule=define_yearly_rps_storage_losses)


def define_yearly_rps_eligible_generation(model, period):
    """
    How much renewable power contracted to all zones included in the RPS is produced in each period?
    This derived variable represents the amount of power actually produced by generators,
    not the pre-curtailment potential.
    :param model:
    :param period:
    :return:
    """

    total_rps_eligible_generation = 0.0

    for rps_r in model.RPS_ELIGIBLE_RESOURCES:
        for timepoint in model.TIMEPOINTS:
            if model.period[timepoint] == period:
                total_rps_eligible_generation += \
                    model.Provide_Power_MW[rps_r, timepoint] * model.day_weight[model.day[timepoint]]

    return total_rps_eligible_generation

resolve_model.RPS_Eligible_Generation_MWh_Per_Year = Expression(resolve_model.PERIODS,
                                                                rule=define_yearly_rps_eligible_generation)


def define_scheduled_rps_curtailment_per_year(model, period):
    """
    Derived variable that represents the total MWh curtailed from RPS-eligible resources.
    :param model:
    :param period:
    :return:
    """
    scheduled_rps_curtailment = 0.0

    for resource in model.RPS_ELIGIBLE_RESOURCES:
        if resource in model.CURTAILABLE_VARIABLE_RESOURCES:
            for timepoint in model.TIMEPOINTS:
                if model.period[timepoint] == period:
                    scheduled_rps_curtailment += model.Scheduled_Curtailment_MW[resource, timepoint] \
                        * model.day_weight[model.day[timepoint]]

    return scheduled_rps_curtailment

resolve_model.Scheduled_RPS_Curtailment_Per_Year = Expression(resolve_model.PERIODS,
                                                              rule=define_scheduled_rps_curtailment_per_year)


def define_subhourly_rps_curtailment_per_year(model, period):
    """
    Derived variable that represents the total MWh curtailed from RPS-eligible resources on the sub-hourly timescale.
    :param model:
    :param period:
    :return:
    """
    total_subhourly_curtailment = 0.0

    for timepoint in model.TIMEPOINTS:
        if model.period[timepoint] == period:
            total_subhourly_curtailment += (
                model.day_weight[model.day[timepoint]] * (
                    model.Subhourly_Downward_LF_Energy_MWh[timepoint] -
                    model.Subhourly_Upward_LF_Energy_MWh[timepoint]))

    return total_subhourly_curtailment

resolve_model.Subhourly_RPS_Curtailment_Per_Year = Expression(resolve_model.PERIODS,
                                                              rule=define_subhourly_rps_curtailment_per_year)


def achieve_rps_rule(model, period):
    """
    Ensure that the RPS target is met in each period.
    :param model:
    :param period:
    :return:
    """

    # if overbuild is required, curtailment does not count towards the RPS
    if model.require_overbuild:
        scheduled_curtailment_counted_towards_rps = 0
    else:
        scheduled_curtailment_counted_towards_rps = model.Scheduled_RPS_Curtailment_Per_Year[period]

    # Bank_RPS_MWh is the slack variable - if optimize_rps_banking is false, then Bank_RPS_MWh will still represent
    # any additional rps credits that are generated above the rps target, but these credits are not allowed to count
    # towards the rps target in the subsequent period
    # because in this case Previously_Banked_RPS_MWh does not include the variable Bank_RPS_MWh[prev_period]
    return model.Previously_Banked_RPS_MWh[period] \
        + model.RPS_Eligible_Generation_MWh_Per_Year[period] \
        + scheduled_curtailment_counted_towards_rps \
        + model.RPS_Pipeline_Biogas_Generation_MWh_Per_Year[period] \
        - model.RPS_Storage_Losses_MWh_Per_Year[period] \
        - model.Subhourly_RPS_Curtailment_Per_Year[period] * model.require_overbuild \
        + model.rps_nonmodeled_mwh[period] \
        == model.RPS_Target_MWh[period] + model.Bank_RPS_MWh[period]

resolve_model.Achieve_RPS_Constraint = Constraint(resolve_model.PERIODS,
                                                  rule=achieve_rps_rule)


def define_unbundled_flag(model, period):
    """
    Determine whether the model will enforce the RPS_Unbundled_Fraction_Limit_Constraint
    :param model:
    :param period:
    :return:
    """
    number_of_unbundled_resources = 0
    for rps_r in model.RPS_ELIGIBLE_RESOURCES:
        if model.zone[rps_r] not in model.RPS_ZONES:
            number_of_unbundled_resources += 1

    # Don't write constraint if there aren't unbundled resources.
    if number_of_unbundled_resources == 0:
        return False
    # Don't write constraint if an RPS target isn't enforced in the period.
    elif model.rps_fraction_of_retail_sales[period] == 0:
        return False
    else:
        return True

resolve_model.enforce_unbundled_fraction_limit = Param(resolve_model.PERIODS,
                                                       rule=define_unbundled_flag,
                                                       within=Boolean)


def rps_unbundled_fraction_limit_rule(model, period):
    """
    Limit the amount of unbundled RECs to a fraction of the total RPS target.
    If rps_unbundled_fraction_limit = 1 then the limit isn't binding.
    If rps_unbundled_fraction_limit = 0 then no unbundled RECs are allowed.
    Be careful with = 0 as this could cause an infeasibility with existing/planned unbundled non-curtailable resources
    or curtailment of all power from existing/planned unbundled curtailable resources.
    Storage losses and subhourly curtailment in the location zone of the unbundled resources
    aren't currently included in this limit.
    :param model:
    :param period:
    :return:
    """

    if model.enforce_unbundled_fraction_limit[period]:
        # How much renewable power contracted to RPS zones but balanced elsewhere is produced in each period?
        unbundled_rps_in_period = 0.0

        for rps_r in model.RPS_ELIGIBLE_RESOURCES:
            if model.zone[rps_r] not in model.RPS_ZONES:
                for timepoint in model.TIMEPOINTS:
                    if model.period[timepoint] == period:
                        # Sum the amount of power actually produced by generators (not the pre-curtailment potential).
                        unbundled_rps_in_period += \
                            model.Provide_Power_MW[rps_r, timepoint] * model.day_weight[model.day[timepoint]]
                        # if overbuild is not required,
                        # count curtailment of unbundled resources towards the unbundled limit
                        if not model.require_overbuild:
                            unbundled_rps_in_period += model.Scheduled_Curtailment_MW[rps_r, timepoint] \
                                    * model.day_weight[model.day[timepoint]]

        return unbundled_rps_in_period <= model.rps_unbundled_fraction_limit[period] * model.RPS_Target_MWh[period]
    else:
        return Constraint.Skip

resolve_model.RPS_Unbundled_Fraction_Limit_Constraint = Constraint(resolve_model.PERIODS,
                                                                   rule=rps_unbundled_fraction_limit_rule)


# ##### GHG Target Constraints ##### #
# GHG constraint by period
def ghg_target_rule(model, period):
    """
    GHG emissions in a given period in the GHG target area must be less than or equal to a target
    Currently only CO2 is modeled, so "GHG" and "CO2" are functionally equivalent
    :param model:
    :param period:
    :return:
    """

    if model.enforce_ghg_targets:
        return model.GHG_Resource_Emissions_tCO2_Per_Year[period] \
               + model.GHG_Unspecified_Imports_tCO2_Per_Year[period] <= \
               model.ghg_emissions_target_tco2_per_year[period] \
               + model.ghg_emissions_credit_tco2_per_year[period]
    else:
        return Constraint.Skip

resolve_model.GHG_Target_Constraint = Constraint(resolve_model.PERIODS,
                                                 rule=ghg_target_rule)


# ##### Resource Operational Constraints ##### #


# ### Variable renewables ### #
def variable_power_rule(model, variable_resource, timepoint):
    """
    The amount of power that is produced by variable renewable resources is equal to the potential production (shape),
    multiplied by a maintenance derate if applicable.
    If a resource can be scheduled to be curtailed, then a curtailment variable is included.
    Note: subhourly curtailment is treated elsewhere - this constraint only includes scheduled curtailment.
    The model could have numeric problems with this constraint when model.shape is very small,
    so if the production potential is very small, round to zero via shape_trimmed
    :param model:
    :param variable_resource:
    :param timepoint:
    :return: Renewable_Power_Constraint rule
    """
    shape = model.shape[variable_resource, model.day[timepoint], model.hour_of_day[timepoint]]
    if shape < 0.0001:
        shape = 0

    if variable_resource in model.CURTAILABLE_VARIABLE_RESOURCES:
        curtail_or_not = model.Scheduled_Curtailment_MW[variable_resource, timepoint]
    else:
        curtail_or_not = 0

    return model.Provide_Power_MW[variable_resource, timepoint] + curtail_or_not == \
        model.Available_Capacity_In_Timepoint_MW[variable_resource, timepoint] \
        * shape

resolve_model.Renewable_Power_Constraint = Constraint(resolve_model.VARIABLE_RESOURCES,
                                                      resolve_model.TIMEPOINTS,
                                                      rule=variable_power_rule)


# ### Thermal ### #

def dispatchable_commitment_rule(model, resource, timepoint):
    """Determines how much of each dispatchable resource can be committed or started in each timepoint.

    If the Param `commit_all_capacity` is defined for a resource, it will be forced on.
    Otherwise, the capacity that is committed or available to be started is bounded by the total available capacity.

    Args:
        model ([type]): [description]
        resource ([type]): [description]
        timepoint ([type]): [description]

    Returns:
        [type]: [description]
    """

    if model.commit_all_capacity[resource, timepoint]:
        return (
            model.Commit_Capacity_MW[resource, timepoint]
            ==
            model.Available_Capacity_In_Timepoint_MW[resource, timepoint]
        )
    else:
        return (
            model.Commit_Capacity_MW[resource, timepoint] +
            model.Starting_Units[resource, timepoint] * model.unit_size_mw[model.technology[resource]]
            <=
            model.Available_Capacity_In_Timepoint_MW[resource, timepoint]
        )

resolve_model.Maximum_Thermal_Commitment_Constraint = Constraint(
    resolve_model.DISPATCHABLE_RESOURCES,
    resolve_model.TIMEPOINTS,
    rule=dispatchable_commitment_rule
)


def dispatchable_max_gen_and_up_reserves_rule(model, resource, timepoint):
    """
    Maximum output and, for technologies that can provide them, upward reserves and frequency response
    from a dispatchable resource:
    the sum of generation and reserves cannot exceed the fully operational (or committed) capacity
    for each resource in each timepoint.
    :param model:
    :param resource:
    :param timepoint:
    :return: Dispatchable_Max_Gen_Up_Reserve_Constraint
    """
    if resource in model.REGULATION_RESERVE_RESOURCES:
        upward_reg = model.Provide_Upward_Reg_MW[resource, timepoint]
    else:
        upward_reg = 0

    if resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
        upward_lf_reserves = model.Provide_LF_Upward_Reserve_MW[resource, timepoint]
    else:
        upward_lf_reserves = 0

    if resource in model.SPINNING_RESERVE_RESOURCES:
        spin = model.Provide_Spin_MW[resource, timepoint]
    else:
        spin = 0

    if resource in model.TOTAL_FREQ_RESP_RESOURCES:
        frequency_response = model.Provide_Frequency_Response_MW[resource, timepoint]
    else:
        frequency_response = 0

    if resource in model.DISPATCHABLE_RAMP_LIMITED_RESOURCES:
        max_power = \
            (model.Commit_Units[resource, timepoint] - model.Fully_Operational_Units[resource, timepoint]) \
            * model.unit_size_mw[model.technology[resource]] \
            * model.min_stable_level_fraction[model.technology[resource]] \
            + model.Fully_Operational_Units[resource, timepoint] \
            * model.unit_size_mw[model.technology[resource]]
    else:
        max_power = model.Commit_Capacity_MW[resource, timepoint]

    return model.Provide_Power_MW[resource, timepoint] \
        + upward_reg \
        + upward_lf_reserves \
        + spin \
        + frequency_response \
        <= max_power

resolve_model.Dispatchable_Max_Gen_Up_Reserve_Constraint = Constraint(resolve_model.DISPATCHABLE_RESOURCES,
                                                                      resolve_model.TIMEPOINTS,
                                                                      rule=dispatchable_max_gen_and_up_reserves_rule)


def dispatchable_upward_reserve_ramp_rule(model, resource, timepoint):
    """
    Maximum upward reserves from a dispatchable resource within the timeframe assumed
    for reg, load following, and spin reserves (reserve_timeframe_fraction_of_hour):
    The sum of reserves cannot exceed the operational/committed capacity for each resource in each timepoint.
    Frequency response reserve is not included here because it is on a faster timescale (~1 min).
    :param model:
    :param resource:
    :param timepoint:
    :return: Dispatchable_Upward_Reserve_Ramp_Constraint
    """
    if resource in model.REGULATION_RESERVE_RESOURCES:
        upward_reg = model.Provide_Upward_Reg_MW[resource, timepoint]
    else:
        upward_reg = 0

    if resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
        upward_lf_reserves = model.Provide_LF_Upward_Reserve_MW[resource, timepoint]
    else:
        upward_lf_reserves = 0

    if resource in model.SPINNING_RESERVE_RESOURCES:
        spin = model.Provide_Spin_MW[resource, timepoint]
    else:
        spin = 0

    if resource in model.DISPATCHABLE_RAMP_LIMITED_RESOURCES:
        reserve_capable_units = model.Fully_Operational_Units[resource, timepoint]
    else:
        reserve_capable_units = model.Commit_Units[resource, timepoint]

    # don't compile constraint if unit can ramp the entire operational range (1-PMin) within the reserve timeframe
    # or if the unit can't provide any reserves
    if (resource not in model.REGULATION_RESERVE_RESOURCES
        and resource not in model.LOAD_FOLLOWING_RESERVE_RESOURCES
            and resource not in model.SPINNING_RESERVE_RESOURCES):
        return Constraint.Skip
    elif model.reserve_timeframe_fraction_of_hour * model.ramp_rate_fraction[model.technology[resource]] >= \
            (1 - model.min_stable_level_fraction[model.technology[resource]]):
        return Constraint.Skip
    else:
        return upward_reg + upward_lf_reserves + spin <= \
            reserve_capable_units \
            * model.unit_size_mw[model.technology[resource]] \
            * model.ramp_rate_fraction[model.technology[resource]] \
            * model.reserve_timeframe_fraction_of_hour

resolve_model.Dispatchable_Upward_Reserve_Ramp_Constraint = Constraint(resolve_model.DISPATCHABLE_RESOURCES,
                                                                       resolve_model.TIMEPOINTS,
                                                                       rule=dispatchable_upward_reserve_ramp_rule)


def dispatchable_downward_reserve_ramp_rule(model, resource, timepoint):
    """
    Maximum downward reserves from a dispatchable resource within the timeframe assumed
    for reg and load following reserves (reserve_timeframe_fraction_of_hour):
    The sum of reserves cannot exceed the operational/committed capacity for each resource in each timepoint.
    :param model:
    :param resource:
    :param timepoint:
    :return: Dispatchable_Downward_Reserve_Ramp_Constraint
    """
    if resource in model.REGULATION_RESERVE_RESOURCES:
        downward_reg = model.Provide_Downward_Reg_MW[resource, timepoint]
    else:
        downward_reg = 0

    if resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
        downward_lf_reserves = model.Provide_LF_Downward_Reserve_MW[resource, timepoint]
    else:
        downward_lf_reserves = 0

    if resource in model.DISPATCHABLE_RAMP_LIMITED_RESOURCES:
        reserve_capable_units = model.Fully_Operational_Units[resource, timepoint]
    else:
        reserve_capable_units = model.Commit_Units[resource, timepoint]

    # don't compile constraint if unit can ramp the entire operational range (1-PMin) within the reserve timeframe
    # or if the unit can't provide any reserves
    if resource not in model.REGULATION_RESERVE_RESOURCES and resource not in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
        return Constraint.Skip
    elif model.reserve_timeframe_fraction_of_hour * model.ramp_rate_fraction[model.technology[resource]] >= \
            (1 - model.min_stable_level_fraction[model.technology[resource]]):
        return Constraint.Skip
    else:
        return downward_reg + downward_lf_reserves <= \
            reserve_capable_units \
            * model.unit_size_mw[model.technology[resource]] \
            * model.ramp_rate_fraction[model.technology[resource]] \
            * model.reserve_timeframe_fraction_of_hour

resolve_model.Dispatchable_Downward_Reserve_Ramp_Constraint = Constraint(resolve_model.DISPATCHABLE_RESOURCES,
                                                                         resolve_model.TIMEPOINTS,
                                                                         rule=dispatchable_downward_reserve_ramp_rule)


def dispatchable_freq_resp_limit(model, resource, timepoint):
    """
    Each MW of online thermal units can provide a fraction of its committed capacity of frequency response.
    (the fraction is the param thermal_freq_response_fraction_of_commitment)
    Units that are in the process of starting or stopping are assumed to not provide frequency response.
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    if resource in model.DISPATCHABLE_RAMP_LIMITED_RESOURCES:
        frequency_responsive_units = model.Fully_Operational_Units[resource, timepoint]
    else:
        frequency_responsive_units = model.Commit_Units[resource, timepoint]

    return model.Provide_Frequency_Response_MW[resource, timepoint] \
        <= model.thermal_freq_response_fraction_of_commitment[resource]\
        * model.unit_size_mw[model.technology[resource]] \
        * frequency_responsive_units

# Constraint applied over intersection of dispatchable resources and resources that can provide frequency response
resolve_model.Dispatchable_Freq_Resp_Limit_Constraint = Constraint(
    resolve_model.DISPATCHABLE_RESOURCES & resolve_model.TOTAL_FREQ_RESP_RESOURCES,
    resolve_model.TIMEPOINTS,
    rule=dispatchable_freq_resp_limit)


def dispatchable_min_gen_and_down_reserves_rule(model, resource, timepoint):
    """
    Minimum output and downward reserves from a dispatchable resource.
    :param model:
    :param resource:
    :param timepoint:
    :return: Min_Gen_Downward_Reserve_Constraint
    """
    if resource in model.REGULATION_RESERVE_RESOURCES:
        downward_reg = model.Provide_Downward_Reg_MW[resource, timepoint]
    else:
        downward_reg = 0

    if resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
        downward_lf_reserves = model.Provide_LF_Downward_Reserve_MW[resource, timepoint]
    else:
        downward_lf_reserves = 0

    # Relax the min gen constraint by a tiny amount if the unit is ramp limited and is starting or stopping
    # in order to avoid numerical conflicts between the ramp up, ramp down, and maximum power constraints
    if resource in model.DISPATCHABLE_RAMP_LIMITED_RESOURCES:
        ramp_relax_start_stop = model.ramp_relax \
            * (model.Commit_Units[resource, timepoint] - model.Fully_Operational_Units[resource, timepoint])
    else:
        ramp_relax_start_stop = 0

    return model.Provide_Power_MW[resource, timepoint] - downward_reg - downward_lf_reserves \
        >= model.Commit_Capacity_MW[resource, timepoint] \
        * model.min_stable_level_fraction[model.technology[resource]] \
        - ramp_relax_start_stop

resolve_model.Thermal_Min_Gen_Down_Reserve_Constraint = Constraint(resolve_model.DISPATCHABLE_RESOURCES,
                                                                   resolve_model.TIMEPOINTS,
                                                                   rule=dispatchable_min_gen_and_down_reserves_rule)


def dispatchable_units_start_rule(model, resource, timepoint):
    """
    Can't prestart more capacity than is off (not committed, not already starting).
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.PreStart_Units[resource, timepoint] * model.unit_size_mw[model.technology[resource]] \
           + model.Starting_Units[resource, timepoint] * model.unit_size_mw[model.technology[resource]] \
           + model.Commit_Capacity_MW[resource, timepoint] \
        <= model.Available_Capacity_In_Timepoint_MW[resource, timepoint]


resolve_model.Dispatchable_Units_Start_Constraint = Constraint(resolve_model.DISPATCHABLE_RESOURCES,
                                                               resolve_model.TIMEPOINTS,
                                                               rule=dispatchable_units_start_rule)


def dispatchable_units_shut_down_rule(model, dispatchable_resource, timepoint):
    """
    Can't preshut down more units than are on (committed) and not already scheduled to shut down.
    :param model:
    :param dispatchable_resource:
    :param timepoint:
    :return:
    """
    return model.PreShut_Down_Units[dispatchable_resource, timepoint] \
        <= model.Commit_Units[dispatchable_resource, timepoint] \
        - model.Shutting_Down_Units[dispatchable_resource, timepoint]

resolve_model.Dispatchable_Units_Shut_Down_Constraint = Constraint(resolve_model.DISPATCHABLE_RESOURCES,
                                                                   resolve_model.TIMEPOINTS,
                                                                   rule=dispatchable_units_shut_down_rule)


def dispatchable_resource_commitment_tracking_rule(model, resource, timepoint):
    """
    Track how many units are committed/on: the number of committed units in each timepoint is the number that were
    committed in the previous timepoint plus all units that are scheduled to start in the current timepoint minus
    all units that are scheduled to shut down in the current timepoint.
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.Commit_Units[resource, timepoint] \
        == model.Commit_Units[resource, model.previous_timepoint[timepoint]]\
        + model.Start_Units[resource, timepoint] \
        - model.Shut_Down_Units[resource, timepoint]

resolve_model.Commitment_Tracking_Constraint = Constraint(resolve_model.DISPATCHABLE_RESOURCES,
                                                          resolve_model.TIMEPOINTS,
                                                          rule=dispatchable_resource_commitment_tracking_rule)


def dispatchable_resource_ramp_up_rule(model, resource, timepoint):
    """
    Sets the upper bound ramp for a resource.
    When starting a ramp-limited resource the unit starts to PMin in the first timestep,
    so the full operational range is not available.
    ramp_relax is a small number that ensures that the ramp constraints don't conflict
    with the pmax or pmin constraints when turning on or off generators.
    Don't compile ramp rate constraints if the unit can ramp its entire operable range (1-PMin) in the timestep.
    Note: current formulation assumes hourly timesteps
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    if model.ramp_rate_fraction[model.technology[resource]] >= \
            (1 - model.min_stable_level_fraction[model.technology[resource]]):
        return Constraint.Skip
    else:
        return model.Provide_Power_MW[resource, timepoint] \
            - model.Provide_Power_MW[resource, model.previous_timepoint[timepoint]] \
            <= (model.Commit_Capacity_MW[resource, timepoint] - model.Start_Capacity_MW[resource, timepoint]) \
            * model.ramp_rate_fraction[model.technology[resource]] \
            + model.Start_Capacity_MW[resource, timepoint] \
            * model.min_stable_level_fraction[model.technology[resource]] \
            + model.Start_Units[resource, timepoint] * model.ramp_relax


resolve_model.Dispatchable_Resource_Ramp_Up_Constraint = Constraint(resolve_model.DISPATCHABLE_RAMP_LIMITED_RESOURCES,
                                                                    resolve_model.TIMEPOINTS,
                                                                    rule=dispatchable_resource_ramp_up_rule)


def dispatchable_resource_ramp_down_rule(model, resource, timepoint):
    """
    Sets the lower bound ramp for a resource.
    When stopping a ramp-limited resource, the unit held at PMin in the timestep before the Shut_Down_Units is non-zero.
    To be able to shut the unit off, it needs to ramp down in the current timestep by Shut_Down_Units * size * PMin.
    ramp_relax is a small number that ensures that the ramp constraints don't conflict
    with the pmax or pmin constraints when turning on or off generators.
    Don't compile ramp rate constraints if the unit can ramp its entire operable range (1-PMin) in the timestep.
    Note: current formulation assumes hourly timesteps
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    if model.ramp_rate_fraction[model.technology[resource]] >= \
            (1 - model.min_stable_level_fraction[model.technology[resource]]):
        return Constraint.Skip
    else:
        return -(model.Provide_Power_MW[resource, timepoint]
                 - model.Provide_Power_MW[resource, model.previous_timepoint[timepoint]]) \
            <= (model.Commit_Capacity_MW[resource, timepoint] - model.Start_Capacity_MW[resource, timepoint]) \
            * model.ramp_rate_fraction[model.technology[resource]] \
            + model.Shut_Down_Units[resource, timepoint] \
            * model.unit_size_mw[model.technology[resource]] \
            * model.min_stable_level_fraction[model.technology[resource]] \
            + model.Shut_Down_Units[resource, timepoint] * model.ramp_relax

resolve_model.Dispatchable_Resource_Ramp_Down_Constraint = Constraint(resolve_model.DISPATCHABLE_RAMP_LIMITED_RESOURCES,
                                                                      resolve_model.TIMEPOINTS,
                                                                      rule=dispatchable_resource_ramp_down_rule)


def generate_at_max(model, resource, timepoint):
    """
    Generate at max resources always produce power at a level equal to their available capacity.
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """

    return model.Provide_Power_MW[resource, timepoint] \
        == model.Available_Capacity_In_Timepoint_MW[resource, timepoint]


resolve_model.Generate_At_Max_Constraint = \
    Constraint(resolve_model.GENERATE_AT_MAX_RESOURCES,
               resolve_model.TIMEPOINTS,
               rule=generate_at_max)


# ### Hydro ### #

def hydro_energy_budget_rule(model, hydro_resource, period, day):
    """
    Hydro generators must flow enough water through their turbines to exactly meet a pre-defined energy budget unless
    spill is allowed. If spill is allowed, hydro may be spilled instead of curtailing renewables,
    which can mask the magnitude of renewable curtailment.
    Adjusts the daily energy budget for mileage when providing reserves/regulation.
    :param model:
    :param hydro_resource:
    :param period:
    :param day:
    :return:
    """

    timepoints_on_day = list()
    for tmp in model.TIMEPOINTS:
        if model.period[tmp] == period and model.day[tmp] == day:
            timepoints_on_day.append(tmp)

    hydro_daily_energy_mwh = (model.Operational_Capacity_MW[hydro_resource, period] *
                              model.hydro_daily_energy_fraction[hydro_resource, day] *
                              model.timepoints_per_day)

    # Daily_Hydro_Budget_Increase_MWh can be positive or negative,
    # with negative representing a decrease in hydro budget for the day
    if model.multi_day_hydro_energy_sharing:
        hydro_daily_energy_mwh += model.Daily_Hydro_Budget_Increase_MWh[hydro_resource, period, day]

    daily_hydro_energy_mwh = 0.0
    for tmp in timepoints_on_day:
        if hydro_resource in model.REGULATION_RESERVE_RESOURCES:
            upward_reg_mw = model.Provide_Upward_Reg_MW[hydro_resource, tmp]
            downward_reg_mw = model.Provide_Downward_Reg_MW[hydro_resource, tmp]
        else:
            upward_reg_mw = 0
            downward_reg_mw = 0

        if hydro_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
            upward_lf_reserves_mw = model.Provide_LF_Upward_Reserve_MW[hydro_resource, tmp]
            downward_lf_reserves_mw = model.Provide_LF_Downward_Reserve_MW[hydro_resource, tmp]
        else:
            upward_lf_reserves_mw = 0
            downward_lf_reserves_mw = 0

        daily_hydro_energy_mwh += model.Provide_Power_MW[hydro_resource, tmp] \
            + (upward_reg_mw - downward_reg_mw) * model.reg_dispatch_fraction \
            + (upward_lf_reserves_mw - downward_lf_reserves_mw) * model.lf_reserve_dispatch_fraction \

    if model.allow_hydro_spill:
        return daily_hydro_energy_mwh <= hydro_daily_energy_mwh
    else:
        return daily_hydro_energy_mwh == hydro_daily_energy_mwh


resolve_model.Hydro_Energy_Budget_Constraint = Constraint(resolve_model.HYDRO_RESOURCES, resolve_model.PERIODS,
                                                          resolve_model.DAYS, rule=hydro_energy_budget_rule)


def hydro_max_gen_and_up_reserves_rule(model, hydro_resource, timepoint):
    """
    Hydro output + up reserves cannot exceed pre-specified daily max
    :param model:
    :param hydro_resource:
    :param timepoint:
    :return:
    """
    if hydro_resource in model.REGULATION_RESERVE_RESOURCES:
        upward_reg = model.Provide_Upward_Reg_MW[hydro_resource, timepoint]
    else:
        upward_reg = 0

    if hydro_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
        upward_lf_reserves = model.Provide_LF_Upward_Reserve_MW[hydro_resource, timepoint]
    else:
        upward_lf_reserves = 0

    if hydro_resource in model.SPINNING_RESERVE_RESOURCES:
        spin = model.Provide_Spin_MW[hydro_resource, timepoint]
    else:
        spin = 0

    if hydro_resource in model.TOTAL_FREQ_RESP_RESOURCES:
        frequency_response = model.Provide_Frequency_Response_MW[hydro_resource, timepoint]
    else:
        frequency_response = 0

    return model.Provide_Power_MW[hydro_resource, timepoint] \
        + upward_reg + upward_lf_reserves + spin + frequency_response \
        <= model.Available_Capacity_In_Timepoint_MW[hydro_resource, timepoint] \
           * model.hydro_max_gen_fraction[hydro_resource, model.day[timepoint]]

resolve_model.Hydro_Max_Gen_Up_Reserve_Constraint = Constraint(resolve_model.HYDRO_RESOURCES, resolve_model.TIMEPOINTS,
                                                               rule=hydro_max_gen_and_up_reserves_rule)


def hydro_min_gen_and_down_reserves_rule(model, hydro_resource, timepoint):
    """
    Hydro output minus downward reserves cannot be below the pre-specified daily min gen
    :param model:
    :param hydro_resource:
    :param timepoint:
    :return:
    """
    if hydro_resource in model.REGULATION_RESERVE_RESOURCES:
        downward_reg = model.Provide_Downward_Reg_MW[hydro_resource, timepoint]
    else:
        downward_reg = 0

    if hydro_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
        downward_lf_reserves = model.Provide_LF_Downward_Reserve_MW[hydro_resource, timepoint]
    else:
        downward_lf_reserves = 0

    return model.Provide_Power_MW[hydro_resource, timepoint] - downward_reg - downward_lf_reserves \
        >= model.Available_Capacity_In_Timepoint_MW[hydro_resource, timepoint] \
           * model.hydro_min_gen_fraction[hydro_resource, model.day[timepoint]]

resolve_model.Hydro_Min_Gen_Down_Reserve_Constraint = Constraint(resolve_model.HYDRO_RESOURCES,
                                                                 resolve_model.TIMEPOINTS,
                                                                 rule=hydro_min_gen_and_down_reserves_rule)


def hydro_ramp_rule_lb(model, hydro_resource, timepoint, ramp_duration):
    """
    Multi-hour hydro ramp constraints enforced for each resource in every timepoint.
    :param model:
    :param hydro_resource:
    :param timepoint:
    :param ramp_duration:
    :return:
    """
    if model.hour_of_day[timepoint] - ramp_duration < 0:
        timepoint_shift = model.timepoints_per_day
    else:
        timepoint_shift = 0

    return - (model.Operational_Capacity_MW[hydro_resource, model.period[timepoint]] *
              model.hydro_ramp_down_limit_fraction[hydro_resource, ramp_duration]) \
              <= \
             (model.Provide_Power_MW[hydro_resource, timepoint] -
              model.Provide_Power_MW[hydro_resource, timepoint - ramp_duration + timepoint_shift])

resolve_model.Hydro_Ramp_Constraint_LB = Constraint(resolve_model.RAMP_CONSTRAINED_HYDRO_RESOURCES,
                                                 resolve_model.TIMEPOINTS,
                                                 resolve_model.HYDRO_RAMP_DURATIONS,
                                                 rule=hydro_ramp_rule_lb)

def hydro_ramp_rule_ub(model, hydro_resource, timepoint, ramp_duration):
    """
    Multi-hour hydro ramp constraints enforced for each resource in every timepoint.
    :param model:
    :param hydro_resource:
    :param timepoint:
    :param ramp_duration:
    :return:
    """
    if model.hour_of_day[timepoint] - ramp_duration < 0:
        timepoint_shift = model.timepoints_per_day
    else:
        timepoint_shift = 0

    return (model.Provide_Power_MW[hydro_resource, timepoint] -
            model.Provide_Power_MW[hydro_resource, timepoint - ramp_duration + timepoint_shift]) \
            <= \
           (model.Operational_Capacity_MW[hydro_resource, model.period[timepoint]] *
            model.hydro_ramp_up_limit_fraction[hydro_resource, ramp_duration])

resolve_model.Hydro_Ramp_Constraint_UB = Constraint(resolve_model.RAMP_CONSTRAINED_HYDRO_RESOURCES,
                                                 resolve_model.TIMEPOINTS,
                                                 resolve_model.HYDRO_RAMP_DURATIONS,
                                                 rule=hydro_ramp_rule_ub)

# ### Storage ### #

def storage_discharge_rule(model, storage_resource, timepoint):
    """
    Storage cannot discharge at a higher rate than implied by its total installed power capacity.
    Charge and discharge rate limits are currently the same.
    :param model:
    :param storage_resource:
    :param timepoint:
    :return:
    """
    return model.Provide_Power_MW[storage_resource, timepoint] \
        <= model.Available_Capacity_In_Timepoint_MW[storage_resource, timepoint]

resolve_model.Storage_Discharge_Constraint = Constraint(resolve_model.STORAGE_RESOURCES, resolve_model.TIMEPOINTS,
                                                        rule=storage_discharge_rule)


def storage_charge_rule(model, storage_resource, timepoint):
    """
    Storage cannot charge at a higher rate than implied by its total installed power capacity.
    Charge and discharge rate limits are currently the same.
    :param model:
    :param storage_resource:
    :param timepoint:
    :return:
    """
    return model.Charge_Storage_MW[storage_resource, timepoint] \
        <= model.Available_Capacity_In_Timepoint_MW[storage_resource, timepoint]

resolve_model.Storage_Charge_Constraint = Constraint(resolve_model.STORAGE_RESOURCES, resolve_model.TIMEPOINTS,
                                                     rule=storage_charge_rule)


def storage_energy_rule(model, storage_resource, timepoint):
    """
    No more total energy can be stored at any point that the total storage energy capacity.
    :param model:
    :param storage_resource:
    :param timepoint:
    :return:
    """
    return model.Energy_in_Storage_MWh[storage_resource, timepoint] \
        <= model.Total_Storage_Energy_Capacity_MWh[storage_resource, model.period[timepoint]] \
           * model.maintenance_derate[storage_resource, timepoint]


resolve_model.Storage_Energy_Constraint = Constraint(resolve_model.STORAGE_RESOURCES, resolve_model.TIMEPOINTS,
                                                     rule=storage_energy_rule)


def storage_energy_tracking_rule(model, storage_resource, timepoint):
    """
    The total energy in storage at the start of the next timepoint must equal
    the energy in storage at the start of the current timepoint
    plus charging that happened in the current timepoint, adjusted for the charging efficiency,
    minus discharging in the current timepoint, adjusted for the discharging efficiency.
    If providing reserve, assume a fraction of the time the reserves are dispatched, so add the respective additional
    energy stored from downward reserves (multiplied by the charging efficiency, as less is actually stored than
    needed from the grid) and additional energy discharged from upward reserves (divided by the discharging efficiency,
    as less is released to the grid than was stored).
    Assume providing frequency response or spinning reserve -- needed in rare contingency events
    -- will not affect the state of charge.
    Note that another constraint (storage_upward_reserve_energy_rule) ensures that there is enough energy in the
    storage device to dispatch spinning reserve for an entire timestep.
    :param model:
    :param storage_resource:
    :param timepoint:
    :return:
    """

    charging_mwh = 0.0
    discharging_mwh = 0.0

    charging_mwh += model.Charge_Storage_MW[storage_resource, timepoint]
    discharging_mwh += model.Provide_Power_MW[storage_resource, timepoint]

    # Regulation reserve dispatch
    if storage_resource in model.REGULATION_RESERVE_RESOURCES:
        charging_mwh += model.Provide_Downward_Reg_MW[storage_resource, timepoint] \
            * model.reg_dispatch_fraction
        discharging_mwh += model.Provide_Upward_Reg_MW[storage_resource, timepoint] \
            * model.reg_dispatch_fraction

    # Load-following reserve dispatch
    if storage_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
        charging_mwh += model.Provide_LF_Downward_Reserve_MW[storage_resource, timepoint] \
            * model.lf_reserve_dispatch_fraction
        discharging_mwh += model.Provide_LF_Upward_Reserve_MW[storage_resource, timepoint] \
            * model.lf_reserve_dispatch_fraction

    return model.Energy_in_Storage_MWh[storage_resource, model.next_timepoint[timepoint]] \
        == model.Energy_in_Storage_MWh[storage_resource, timepoint] \
        + charging_mwh * model.charging_efficiency[model.technology[storage_resource]] \
        - discharging_mwh / model.discharging_efficiency[model.technology[storage_resource]]

resolve_model.Storage_Energy_Tracking_Constraint = Constraint(resolve_model.STORAGE_RESOURCES, resolve_model.TIMEPOINTS,
                                                              rule=storage_energy_tracking_rule)


def storage_upward_reserve_power_rule(model, storage_resource, timepoint):
    """
    A storage resource can provide no more upward reserve and/or frequency response (headroom) than
    its installed discharging capacity (here the same as the charging capacity = Operational_Capacity_MW)
    minus the power it's currently providing (if discharging)
    plus the power it's currently drawing from the grid (if charging).
    No binaries are implemented here, but the assumption is that charging and discharging won't happen at the same time.
    :param model:
    :param storage_resource:
    :param timepoint:
    :return:
    """
    if (storage_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES or
            storage_resource in model.REGULATION_RESERVE_RESOURCES or
            storage_resource in model.SPINNING_RESERVE_RESOURCES or
            storage_resource in model.TOTAL_FREQ_RESP_RESOURCES):

        if storage_resource in model.REGULATION_RESERVE_RESOURCES:
            upward_reg = model.Provide_Upward_Reg_MW[storage_resource, timepoint]
        else:
            upward_reg = 0

        if storage_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
            upward_lf_reserves = model.Provide_LF_Upward_Reserve_MW[storage_resource, timepoint]
        else:
            upward_lf_reserves = 0

        if storage_resource in model.SPINNING_RESERVE_RESOURCES:
            spin = model.Provide_Spin_MW[storage_resource, timepoint]
        else:
            spin = 0

        if storage_resource in model.TOTAL_FREQ_RESP_RESOURCES:
            frequency_response = model.Provide_Frequency_Response_MW[storage_resource, timepoint]
        else:
            frequency_response = 0

        return upward_reg + upward_lf_reserves + spin + frequency_response \
            <= model.Operational_Capacity_MW[storage_resource, model.period[timepoint]] \
            - model.Provide_Power_MW[storage_resource, timepoint] \
            + model.Charge_Storage_MW[storage_resource, timepoint]
    else:
        return Constraint.Skip

resolve_model.Storage_Upward_Reserve_Power_Constraint = Constraint(resolve_model.STORAGE_RESOURCES,
                                                                   resolve_model.TIMEPOINTS,
                                                                   rule=storage_upward_reserve_power_rule)


def storage_downward_reserve_power_rule(model, storage_resource, timepoint):
    """
    A storage resource can provide no more downward reserve than
    its installed charging capacity (here the same as the discharging capacity = Operational_Capacity_MW)
    minus the power it's currently drawing from the grid (if charging)
    plus the power it's currently providing (if discharging).
    No binaries are implemented here, but the assumption is that charging and discharging won't happen at the same time.
    :param model:
    :param storage_resource:
    :param timepoint:
    :return:
    """
    if (storage_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES or
            storage_resource in model.REGULATION_RESERVE_RESOURCES):

        if storage_resource in model.REGULATION_RESERVE_RESOURCES:
            downward_reg = model.Provide_Downward_Reg_MW[storage_resource, timepoint]
        else:
            downward_reg = 0

        if storage_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
            downward_lf_reserves = model.Provide_LF_Downward_Reserve_MW[storage_resource, timepoint]
        else:
            downward_lf_reserves = 0

        return downward_reg + downward_lf_reserves <= \
            model.Operational_Capacity_MW[storage_resource, model.period[timepoint]] - \
            model.Charge_Storage_MW[storage_resource, timepoint] + \
            model.Provide_Power_MW[storage_resource, timepoint]
    else:
        return Constraint.Skip

resolve_model.Storage_Downward_Reserve_Power_Constraint = Constraint(resolve_model.STORAGE_RESOURCES,
                                                                     resolve_model.TIMEPOINTS,
                                                                     rule=storage_downward_reserve_power_rule)


def storage_upward_reserve_energy_rule(model, storage_resource, timepoint):
    """
    If called upon to provide upward reserve, storage must be have enough energy available to sustain output for
    the duration of the timepoint. Because of the discharge (in)efficiency, it will actually release less energy to the
    grid than is actually available in storage, so multiply by the discharge efficiency.
    Load-following, regulation, and spin are assumed to need to be available for the full duration of the timepoint
    if called upon.
    Ignore frequency response provision on the assumption that it does not significantly affect state of charge.
    :param model:
    :param storage_resource:
    :param timepoint:
    :return:
    """
    if (storage_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES or
            storage_resource in model.REGULATION_RESERVE_RESOURCES or
            storage_resource in model.SPINNING_RESERVE_RESOURCES):

        if storage_resource in model.REGULATION_RESERVE_RESOURCES:
            upward_reg = model.Provide_Upward_Reg_MW[storage_resource, timepoint]
        else:
            upward_reg = 0

        if storage_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
            upward_lf_reserves = model.Provide_LF_Upward_Reserve_MW[storage_resource, timepoint]
        else:
            upward_lf_reserves = 0

        if storage_resource in model.SPINNING_RESERVE_RESOURCES:
            spin = model.Provide_Spin_MW[storage_resource, timepoint]
        else:
            spin = 0

        return model.Provide_Power_MW[storage_resource, timepoint] \
            + upward_reg + upward_lf_reserves + spin \
            - model.Charge_Storage_MW[storage_resource, timepoint]\
            <= model.Energy_in_Storage_MWh[storage_resource, timepoint] \
            * model.discharging_efficiency[model.technology[storage_resource]]
    else:
        return Constraint.Skip

resolve_model.Storage_Upward_Reserve_Energy_Constraint = Constraint(resolve_model.STORAGE_RESOURCES,
                                                                    resolve_model.TIMEPOINTS,
                                                                    rule=storage_upward_reserve_energy_rule)


def storage_downward_reserve_energy_rule(model, storage_resource, timepoint):
    """
    If called upon to provide downward reserve, storage must be have enough energy storage capacity to store the
    additional energy from the new set point. Because of the charging (in)efficiency, it will have to get more energy
    from the grid than it will be able to put in storage, so divide by the charging efficiency.
    Load-following and regulation are assumed to have to be available for the full duration of the timepoint if called
    upon.
    :param model:
    :param storage_resource:
    :param timepoint:
    :return:
    """
    if (storage_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES or
            storage_resource in model.REGULATION_RESERVE_RESOURCES):

        if storage_resource in model.REGULATION_RESERVE_RESOURCES:
            downward_reg = model.Provide_Downward_Reg_MW[storage_resource, timepoint]
        else:
            downward_reg = 0

        if storage_resource in model.LOAD_FOLLOWING_RESERVE_RESOURCES:
            downward_lf_reserves = model.Provide_LF_Downward_Reserve_MW[storage_resource, timepoint]
        else:
            downward_lf_reserves = 0

        return model.Charge_Storage_MW[storage_resource, timepoint] \
            + downward_reg + downward_lf_reserves \
            - model.Provide_Power_MW[storage_resource, timepoint] \
            <= (model.Total_Storage_Energy_Capacity_MWh[storage_resource, model.period[timepoint]] -
                model.Energy_in_Storage_MWh[storage_resource, timepoint]) \
            / model.charging_efficiency[model.technology[storage_resource]]
    else:
        return Constraint.Skip

resolve_model.Storage_Downward_Reserve_Energy_Constraint = Constraint(resolve_model.STORAGE_RESOURCES,
                                                                      resolve_model.TIMEPOINTS,
                                                                      rule=storage_downward_reserve_energy_rule)


# ##### Power Balance and System Operational Constraints ##### #

def zonal_power_balance_rule(model, zone, timepoint):
    """
    The sum of all in-zone generation, net transmission flow, and net storage production
    must equal the zone's load in each timepoint.
    Two slack variables for unserved energy and overgeneration are included.
    Storage and flexible load (shift) can both add or subtract from a zone's power balance,
    so they appear on both sides of the power balance equation.
    Scheduled renewable curtailment is not explicitly included here because Provide_Power_MW
    will be less than the resource's potential power production during times of scheduled curtailment
    :param model:
    :param zone:
    :param timepoint:
    :return:
    """

    generation = float()
    storage_charging = float()
    hydrogen_electrolysis_load = float()
    ev_charging = float()
    ee_load_reduction = float()
    flexible_load = float()

    for resource in model.RESOURCES:
        if model.zone[resource] == zone:

            if resource not in model.LOAD_ONLY_RESOURCES | model.EE_PROGRAMS | model.FLEXIBLE_LOAD_RESOURCES:
                # generation (also includes storage discharging and shed demand response)
                generation += model.Provide_Power_MW[resource, timepoint]

            # storage charging
            if resource in model.STORAGE_RESOURCES:
                storage_charging += model.Charge_Storage_MW[resource, timepoint]

            # hydrogen electrolysis load
            if resource in model.HYDROGEN_ELECTROLYSIS_RESOURCES:
                hydrogen_electrolysis_load += model.Hydrogen_Electrolysis_Load_MW[resource, timepoint]

            # EV load
            if resource in model.EV_RESOURCES:
                ev_charging += model.Charge_EV_Batteries_MW[resource, timepoint]

            # energy efficiency
            if resource in model.EE_PROGRAMS:
                ee_load_reduction += model.EE_Reduced_Load_FTM_MW[resource, timepoint]

            # flexible loads
            if resource in model.FLEXIBLE_LOAD_RESOURCES:
                flexible_load += model.Shift_Load_Up_MW[resource, timepoint]
                flexible_load -= model.Shift_Load_Down_MW[resource, timepoint]

    # Imports/exports
    # Transmit_Power_Unspecified is used here because dedicated imports
    # are modeled as supplying power to the "to" zone directly,
    # so power from dedicated import resources will be included with resources above
    imports_exports = 0
    for line in model.TRANSMISSION_LINES:
        if model.transmission_to[line] == zone or model.transmission_from[line] == zone:
            if model.transmission_to[line] == zone:
                imports_exports += model.Transmit_Power_Unspecified_MW[line, timepoint]
            elif model.transmission_from[line] == zone:
                imports_exports -= model.Transmit_Power_Unspecified_MW[line, timepoint]

    # Imports and exports through semi storage zones
    # The positive direction for SSZ_Transmit_Power_MW is from the zone to storage semi zones,
    # so the direction is negative
    semi_storage_zones_imports_exports = float()
    if model.allow_semi_storage_zones:
        for ssz in model.SEMI_STORAGE_ZONES:
            if model.ssz_from_zone[ssz] == zone:
                semi_storage_zones_imports_exports -= model.SSZ_Transmit_Power_MW[ssz, timepoint]

    if model.allow_unserved_energy:
        unserved_energy = model.Unserved_Energy_MW[zone, timepoint]
    else:
        unserved_energy = 0.0

    # Unserved energy & overgeneration for infeasibility diagnosis
    return generation \
           + imports_exports \
           + semi_storage_zones_imports_exports \
           - model.Overgeneration_MW[zone, timepoint] \
           == model.input_load_mw[zone, timepoint] \
              + storage_charging \
              + ev_charging \
              + flexible_load \
              + hydrogen_electrolysis_load \
              - ee_load_reduction \
              - unserved_energy

resolve_model.Zonal_Power_Balance_Constraint = Constraint(resolve_model.ZONES, resolve_model.TIMEPOINTS,
                                                          rule=zonal_power_balance_rule)


def transmission_min_flow_rule(model, line, timepoint):
    """
    Transmission flows must obey flow limits on each line.
    :param model:
    :param line:
    :param timepoint:
    :return:
    """
    # Default tx bound
    min_flow_bound = model.min_flow_planned_mw[line]
    # If allow_tx_build, incremental capacity is added onto existing
    if model.allow_tx_build and line in model.TRANSMISSION_LINES_NEW:
        min_flow_bound -= model.New_Tx_Total_Installed_Capacity_MW[line, model.period[timepoint]]

    return min_flow_bound <= model.Transmit_Power_MW[line, timepoint]

resolve_model.Transmission_Min_Flow_Constraint = Constraint(resolve_model.TRANSMISSION_LINES,
                                                            resolve_model.TIMEPOINTS,
                                                            rule=transmission_min_flow_rule)


def transmission_max_flow_rule(model, line, timepoint):
    """
    Transmission flows must obey flow limits on each line.
    :param model:
    :param line:
    :param timepoint:
    :return:
    """
    # Default tx bound
    max_flow_bound = model.max_flow_planned_mw[line]
    # If allow_tx_build, incremental capacity is added onto existing
    if model.allow_tx_build and line in model.TRANSMISSION_LINES_NEW:
        max_flow_bound += model.New_Tx_Total_Installed_Capacity_MW[line, model.period[timepoint]]

    return model.Transmit_Power_MW[line, timepoint] <= max_flow_bound

resolve_model.Transmission_Max_Flow_Constraint = Constraint(resolve_model.TRANSMISSION_LINES,
                                                            resolve_model.TIMEPOINTS,
                                                            rule=transmission_max_flow_rule)

if resolve_model.transmission_ramp_limit:
    def transmission_ramp_down_rule(model, line, tmp,
                                    ramp_duration):
        """
        Multi-hour intertie ramp down constraints enforced in every timepoint.

        :param model:
        :param line:
        :param tmp:
        :param ramp_duration:
        :return:
        """
        if model.hour_of_day[tmp] - ramp_duration < 0:
            timepoint_shift = model.timepoints_per_day
        else:
            timepoint_shift = 0

        # Default tx bound
        max_flow_bound = (model.max_flow_planned_mw[line] - model.min_flow_planned_mw[line])
        # If allow_tx_build, incremental capacity is added onto existing
        if model.allow_tx_build and line in model.TRANSMISSION_LINES_NEW:
            # add the incremental capacity in both the positive and negative directions
            max_flow_bound += 2 * model.New_Tx_Total_Installed_Capacity_MW[line, model.period[tmp]]

        return (- model.flow_ramp_down_limit_fraction[line, ramp_duration] * max_flow_bound
                <=
                model.Transmit_Power_MW[line, tmp] -
                model.Transmit_Power_MW[line, tmp - ramp_duration + timepoint_shift])

    resolve_model.Transmission_Ramp_Down_Constraint = Constraint(
        resolve_model.RAMP_CONSTRAINED_TRANSMISSION_LINES,
        resolve_model.TIMEPOINTS,
        resolve_model.INTERTIE_FLOW_RAMP_DURATIONS,
        rule=transmission_ramp_down_rule)


    def transmission_ramp_up_rule(model, line, tmp, ramp_duration):
        """
        Multi-hour intertie ramp up constraints enforced in every timepoint.

        :param model:
        :param line:
        :param tmp:
        :param ramp_duration:
        :return:
        """
        if model.hour_of_day[tmp] - ramp_duration < 0:
            timepoint_shift = model.timepoints_per_day
        else:
            timepoint_shift = 0

        # Default tx bound
        max_flow_bound = (model.max_flow_planned_mw[line] - model.min_flow_planned_mw[line])
        # If allow_tx_build, incremental capacity is added onto existing
        if model.allow_tx_build and line in model.TRANSMISSION_LINES_NEW:
            max_flow_bound += 2 * model.New_Tx_Total_Installed_Capacity_MW[line, model.period[tmp]]

        return (model.Transmit_Power_MW[line, tmp] -
                model.Transmit_Power_MW[line, tmp - ramp_duration + timepoint_shift]
                <=
                model.flow_ramp_up_limit_fraction[line, ramp_duration] * max_flow_bound)


    resolve_model.Transmission_Ramp_Up_Constraint = Constraint(
        resolve_model.RAMP_CONSTRAINED_TRANSMISSION_LINES,
        resolve_model.TIMEPOINTS,
        resolve_model.INTERTIE_FLOW_RAMP_DURATIONS,
        rule=transmission_ramp_up_rule)


def simultaneous_transmission_flows_rule(model, group, timepoint):
    """
    The sum of flows on a group of lines (in a certain direction) cannot exceed a pre-specified limit.
    :param model:
    :param group:
    :param timepoint:
    :return:
    """
    sim_flow = float()
    for (g, line) in model.SIMULTANEOUS_FLOW_GROUP_LINES:
        if g == group:
            sim_flow += model.Transmit_Power_MW[line, timepoint] * model.direction[g, line]
    return sim_flow <= model.simultaneous_flow_limit_mw[group, model.period[timepoint]]

resolve_model.Simultaneous_Flows_Limit_Constraint = Constraint(resolve_model.SIMULTANEOUS_FLOW_GROUPS,
                                                               resolve_model.TIMEPOINTS,
                                                               rule=simultaneous_transmission_flows_rule)


# ### Operational Reserves ### #
def spinning_reserve_req(model, timepoint):
    spinning_reserve_requirement = float()
    for zone in model.ZONES:
        # how much does energy efficiency reduce demand?
        # Will be used to adjust the spinning reserve requirement
        ee_load_reduction = 0
        for resource in model.EE_PROGRAMS:
            if model.zone[resource] == zone:
                ee_load_reduction += model.EE_Reduced_Load_FTM_MW[resource, timepoint]

        spinning_reserve_requirement += model.spin_reserve_fraction_of_load[zone] * \
            (model.input_load_mw[zone, timepoint] - ee_load_reduction)

    return spinning_reserve_requirement

resolve_model.Spinning_Reserve_Req_MW = Expression(
    resolve_model.TIMEPOINTS,
    rule=spinning_reserve_req)

def spinning_reserve_rule(model, timepoint):
    """
    Meet the spinning reserve requirement in each timepoint.
    :param model:
    :param timepoint:
    :return:
    """
    spinning_reserve_provision = float()
    for resource in model.SPINNING_RESERVE_RESOURCES:
        spinning_reserve_provision += model.Provide_Spin_MW[resource, timepoint]

    return (spinning_reserve_provision + model.Spin_Violation_MW[timepoint] ==
            model.Spinning_Reserve_Req_MW[timepoint])

resolve_model.Meet_Spin_Requirement_Constraint = Constraint(resolve_model.TIMEPOINTS,
                                                            rule=spinning_reserve_rule)


def upward_regulation_rule(model, timepoint):
    """
    Meet the regulation requirement in each timepoint.
    :param model:
    :param timepoint:
    :return: rule ensuring upward regulation requirement is met
    """
    upward_regulation_provision = float()
    for resource in model.REGULATION_RESERVE_RESOURCES:
        upward_regulation_provision += model.Provide_Upward_Reg_MW[resource, timepoint]

    return upward_regulation_provision + model.Upward_Reg_Violation_MW[timepoint] \
        == model.upward_reg_req[timepoint]

resolve_model.Meet_Upward_Reg_Requirement_Constraint = Constraint(resolve_model.TIMEPOINTS,
                                                                  rule=upward_regulation_rule)


def downward_regulation_rule(model, timepoint):
    """
    Meet the downward regulation requirement in each timepoint.
    Currently variable renewables are assumed to not provide regulation.
    :param model:
    :param timepoint:
    :return:
    """
    downward_regulation_provision = float()
    for resource in model.REGULATION_RESERVE_RESOURCES:
        downward_regulation_provision += model.Provide_Downward_Reg_MW[resource, timepoint]

    return downward_regulation_provision + model.Downward_Reg_Violation_MW[timepoint] \
        == model.downward_reg_req[timepoint]

resolve_model.Meet_Downward_Reg_Requirement_Constraint = Constraint(resolve_model.TIMEPOINTS,
                                                                    rule=downward_regulation_rule)

def upward_combined_lf_reserve_req(model, timepoint):
    """Add endogenous LF requirement to baseline input LF requirement if applicable.

    The expression assumes all PRM variable resources contribute to the endogenous LF requirement
    and scales the incremental system load following need linearly with Operational_Capacity_MW
    """
    req = model.upward_lf_reserve_req[timepoint]

    for resource in model.VARIABLE_RESOURCES:
        if model.zone[resource] in model.LOAD_FOLLOWING_ZONES:
            req += (
                model.Operational_Capacity_MW[resource, model.period[timepoint]] *
                model.resource_upward_lf_req[resource, model.day[timepoint],
                                                model.hour_of_day[timepoint]])
    return req

resolve_model.Upward_Load_Following_Reserve_Req = Expression(
    resolve_model.TIMEPOINTS,
    rule=upward_combined_lf_reserve_req)

def downward_combined_lf_reserve_req(model, timepoint):
    """Add endogenous LF requirement to baseline input LF requirement if applicable.

    The expression assumes all PRM variable resources contribute to the endogenous LF requirement
    and scales the incremental system load following need linearly with Operational_Capacity_MW
    """
    req = model.downward_lf_reserve_req[timepoint]

    for resource in model.VARIABLE_RESOURCES:
        if model.zone[resource] in model.LOAD_FOLLOWING_ZONES:
            req += (
                model.Operational_Capacity_MW[resource, model.period[timepoint]] *
                model.resource_downward_lf_req[resource, model.day[timepoint],
                                                model.hour_of_day[timepoint]])
    return req

resolve_model.Downward_Load_Following_Reserve_Req = Expression(
    resolve_model.TIMEPOINTS,
    rule=downward_combined_lf_reserve_req)


def downward_load_following_reserve_rule(model, timepoint):
    """Meet downward load following reserve requirement by incurring subhourly curtailment.

    Downward LF not provided by firm resources or taken as a violation must be provided by curtailable
    variable resources.
    """
    firm_downward_lf_provision_mw = sum(
        model.Provide_LF_Downward_Reserve_MW[r, timepoint]
        for r in model.LOAD_FOLLOWING_RESERVE_RESOURCES)
    # make a separate Var for Sub_Curtailment / lf_dispatch
    return (model.Variable_Resource_Provide_Downward_LF_MW[timepoint] +
            model.Downward_LF_Reserve_Violation_MW[timepoint] +
            firm_downward_lf_provision_mw
            ==
            model.Downward_Load_Following_Reserve_Req[timepoint])

resolve_model.Meet_Downward_LF_Requirement_Constraint = Constraint(
    resolve_model.TIMEPOINTS,
    rule=downward_load_following_reserve_rule)


def meet_upward_load_following_reserve_rule(model, timepoint):
    """Ensure that upward load following reserves are met."""
    firm_upward_lf_provision_mw = sum(
        model.Provide_LF_Upward_Reserve_MW[r, timepoint]
        for r in model.LOAD_FOLLOWING_RESERVE_RESOURCES)

    return (firm_upward_lf_provision_mw +
            model.Variable_Resource_Provide_Upward_LF_MW[timepoint] +
            model.Upward_LF_Reserve_Violation_MW[timepoint]
            ==
            model.Upward_Load_Following_Reserve_Req[timepoint])

resolve_model.Meet_Upward_LF_Requirement_Constraint = Constraint(
    resolve_model.TIMEPOINTS,
    rule=meet_upward_load_following_reserve_rule)


def upward_load_following_reserve_rule(model, timepoint):
    """Limit the available upward LF from variable resources as a fraction of total scheduled curtailment.

    Variable resources can provide as much upward LF as they've scheduled for curtailment,
    even though only a fraction of the bid is dispatched (e.g., 20%)
    """
    if model.variable_resources_upward_lf:
        curtailment_mw = sum(
            model.Scheduled_Curtailment_MW[r, timepoint]
            for r in model.LOAD_FOLLOWING_ZONE_CURTAILABLE_RESOURCES)
    else:
        curtailment_mw = 0

    return (model.Variable_Resource_Provide_Upward_LF_MW[timepoint]
            <=
            model.var_rnw_available_for_lf_reserves * curtailment_mw)

resolve_model.Variable_Resource_Available_Upward_LF_Constraint = Constraint(
    resolve_model.TIMEPOINTS,
    rule=upward_load_following_reserve_rule)


def variable_rnw_down_reserve_availability_rule(model, timepoint):
    """Limit the available downward LF from variable resources as a fraction of total variable resource power production."""
    total_variable_renewables = float()
    for resource in model.LOAD_FOLLOWING_ZONE_CURTAILABLE_RESOURCES:
        total_variable_renewables += model.Provide_Power_MW[resource, timepoint]

    return (model.Variable_Resource_Provide_Downward_LF_MW[timepoint]
            <=
            model.var_rnw_available_for_lf_reserves * total_variable_renewables)

resolve_model.Var_Renw_Down_LF_Reserve_Availability_Constraint = Constraint(
    resolve_model.TIMEPOINTS,
    rule=variable_rnw_down_reserve_availability_rule)


def max_upward_lf_from_variable_rule(model, timepoint):
    """Limit the fraction of upward LF reserves that can be provided by variable resources."""
    return (model.Variable_Resource_Provide_Upward_LF_MW[timepoint]
            <=
            model.max_var_rnw_lf_reserves *
            model.Upward_Load_Following_Reserve_Req[timepoint])

resolve_model.Max_Upward_LF_From_Variable_Resources_Constraint = Constraint(
    resolve_model.TIMEPOINTS,
    rule=max_upward_lf_from_variable_rule)


def variable_rnw_downward_lf_reserve_limit_rule(model, timepoint):
    """Limit the fraction of the reserve requirement can be met with variable generation."""
    return (model.Variable_Resource_Provide_Downward_LF_MW[timepoint]
            <=
            model.max_var_rnw_lf_reserves *
            model.Downward_Load_Following_Reserve_Req[timepoint])

resolve_model.Var_Renw_Down_LF_Reserve_Limit_Constraint = Constraint(
    resolve_model.TIMEPOINTS,
    rule=variable_rnw_downward_lf_reserve_limit_rule)


def total_frequency_response_rule(model, timepoint):
    """
    Available headroom from resources contributing to the total frequency response requirement
    must be greater than the requirement.
    In other operational constraints, frequency response is modeled as additive to upward reserves,
    which means that provision of the two services is not allowed to be overlapping.
    Skip constraint if requirement is 0.
    :param model:
    :param timepoint:
    :return:
    """
    if model.freq_resp_total_req_mw[timepoint] == 0:
        return Constraint.Skip
    else:
        frequency_response_provision = float()
        for resource in model.TOTAL_FREQ_RESP_RESOURCES:
            frequency_response_provision += model.Provide_Frequency_Response_MW[resource, timepoint]

        return frequency_response_provision >= model.freq_resp_total_req_mw[timepoint]

resolve_model.Total_Frequency_Response_Headroom_Constraint = Constraint(resolve_model.TIMEPOINTS,
                                                                        rule=total_frequency_response_rule)


def partial_frequency_response_rule(model, timepoint):
    """
    Available headroom from resources contributing to the partial frequency response requirement
    must be greater than the requirement.
    Partial frequency response headroom can be shared with total frequency response headroom,
    but not with other upward reserves.
    :param model:
    :param timepoint:
    :return:
    """

    if model.freq_resp_partial_req_mw[timepoint] == 0:
        return Constraint.Skip
    else:
        frequency_response_provision = float()
        for resource in model.PARTIAL_FREQ_RESP_RESOURCES:
            frequency_response_provision += model.Provide_Frequency_Response_MW[resource, timepoint]

        return frequency_response_provision >= model.freq_resp_partial_req_mw[timepoint]

resolve_model.Partial_Frequency_Response_Headroom_Constraint = Constraint(resolve_model.TIMEPOINTS,
                                                                          rule=partial_frequency_response_rule)


def minimum_local_committed_generation_rule(model, timepoint):
    """
    A certain amount of eligible generation must be committed in all hours
    from resources in the set of MINIMUM_GENERATION_RESOURCES
    for any timepoint that has min_gen_committed_mw > 0.
    :param model:
    :param timepoint:
    :return:
    """
    if model.min_gen_committed_mw[timepoint] == 0:
        return Constraint.Skip
    else:
        local_generation = float()
        for resource in model.MINIMUM_GENERATION_RESOURCES:
            local_generation += model.Commit_Capacity_MW[resource, timepoint]

        return local_generation >= model.min_gen_committed_mw[timepoint]

resolve_model.Min_Local_Gen_Constraint = Constraint(resolve_model.TIMEPOINTS,
                                                    rule=minimum_local_committed_generation_rule)


# ### Transmission ### #
# Transmission deliverability/energy only for new renewables
def new_transmission_capacity_rule(model, tx_zone, period):
    """
    New transmission must be built if the deliverable capacity of resources in the tx zone
    exceeds the fully_deliverable_new_tx_threshold_mw.
    New_Transmission_Capacity_MW is associated with a cost to build new transmission capacity in the objective.
    :param model:
    :param tx_zone:
    :param period:
    :return:
    """
    total_fully_deliverable_capacity_in_tx_zone = float()
    for r in model.TX_DELIVERABILITY_RESOURCES:
        if model.tx_zone_of_resource[r] == tx_zone:
            total_fully_deliverable_capacity_in_tx_zone += model.Fully_Deliverable_Installed_Capacity_MW[r, period]
    return model.New_Transmission_Capacity_MW[tx_zone, period] \
        >= total_fully_deliverable_capacity_in_tx_zone - model.fully_deliverable_new_tx_threshold_mw[tx_zone]

resolve_model.New_Transmission_Capacity_Constraint = Constraint(resolve_model.TX_ZONES,
                                                                resolve_model.PERIODS,
                                                                rule=new_transmission_capacity_rule)


def energy_only_tx_zone_limit_rule(model, tx_zone, period):
    """
    The total energy only capacity for new resources in a tx zone is limited to energy_only_tx_limit_mw
    :param model:
    :param tx_zone:
    :param period:
    :return:
    """
    total_energy_only_capacity_in_tx_zone = float()
    for r in model.TX_DELIVERABILITY_RESOURCES:
        if model.tx_zone_of_resource[r] == tx_zone:
            total_energy_only_capacity_in_tx_zone += model.Energy_Only_Installed_Capacity_MW[r, period]
    return total_energy_only_capacity_in_tx_zone <= model.energy_only_tx_limit_mw[tx_zone]

resolve_model.Energy_Only_TX_Zone_Limit_Constraint = Constraint(resolve_model.TX_ZONES,
                                                                resolve_model.PERIODS,
                                                                rule=energy_only_tx_zone_limit_rule)


def deliverability_def_rule(model, resource, period):
    """
    Split newly installed resource capacity between energy only and fully deliverable
    Note: as this constraint is defined using Cumulative_New_Installed_Capacity_MW, any capacity added to the system
    via planned_installed_capacity_mw will not be included.  To avoid this possibility,
    planned_installed_capacity_validate ensures that the planned capacity of TX_DELIVERABILITY_RESOURCES is zero.
    Note: TX_DELIVERABILITY_RESOURCES cannot be retired currently,
    so Operational_New_Capacity = Cumulative_New_Installed_Capacity_MW

    :param model:
    :param resource:
    :param period:
    :return:
    """
    return model.Fully_Deliverable_Installed_Capacity_MW[resource, period] \
        + model.Energy_Only_Installed_Capacity_MW[resource, period] \
        == model.Operational_New_Capacity_MW[resource, period]

resolve_model.Deliverability_Definition_Constraint = Constraint(resolve_model.TX_DELIVERABILITY_RESOURCES,
                                                                resolve_model.PERIODS,
                                                                rule=deliverability_def_rule)


def fully_deliverable_period_build_rule(model, resource, current_period):
    """
    Fully_Deliverable_Installed_Capacity_MW cannot decrease over time.
    An identical constraint exists for energy only capacity
    :param model:
    :param resource:
    :param current_period:
    :return:
    """
    if current_period == model.first_period:
        return Constraint.Skip
    else:
        return model.Fully_Deliverable_Installed_Capacity_MW[resource, current_period] \
            >= model.Fully_Deliverable_Installed_Capacity_MW[resource, find_prev_period(model, current_period)]

resolve_model.Fully_Deliverable_Period_Build_Constraint = Constraint(resolve_model.TX_DELIVERABILITY_RESOURCES,
                                                                     resolve_model.PERIODS,
                                                                     rule=fully_deliverable_period_build_rule)


def energy_only_period_build_rule(model, resource, current_period):
    """
    Energy_Only_Installed_Capacity_MW cannot decrease over time.
    An identical constraint exists for fully deliverable capacity
    :param model:
    :param resource:
    :param current_period:
    :return:
    """
    if current_period == model.first_period:
        return Constraint.Skip
    else:
        return model.Energy_Only_Installed_Capacity_MW[resource, current_period] \
            >= model.Energy_Only_Installed_Capacity_MW[resource, find_prev_period(model, current_period)]

resolve_model.Energy_Only_Period_Build_Constraint = Constraint(resolve_model.TX_DELIVERABILITY_RESOURCES,
                                                               resolve_model.PERIODS,
                                                               rule=energy_only_period_build_rule)


# ############ Transmission Direction #############
# The following two constraints define the positive and negative direction versions of Transmit_Power_MW,
# which can then be multiplied by directional hurdle, GHG import rate, or other value.
# Important note: any value multiplied by these variables cannot provide an incentive
# for the directional variable to exceed the absolute value of the non-directional variable in the same direction.
# This means that, for example, a negative cost hurdle rate on the positive direction would give an incentive for
# Transmit_Power_Positive_Direction_MW to be much larger than Transmit_Power_MW
# which is not acceptable because the variables are supposed to be equal to each other when in the same direction.
def positive_direction_transmit_power_rule(model, line, timepoint):
    """
    :param model:
    :param line:
    :param timepoint:
    :return:
    """
    return model.Transmit_Power_Unspecified_Positive_Direction_MW[line, timepoint] \
        >= model.Transmit_Power_Unspecified_MW[line, timepoint]

resolve_model.Transmit_Power_Positive_Direction_Constraint = Constraint(resolve_model.TRANSMISSION_LINES,
                                                                        resolve_model.TIMEPOINTS,
                                                                        rule=positive_direction_transmit_power_rule)


def negative_direction_transmit_power_rule(model, line, timepoint):
    """
    :param model:
    :param line:
    :param timepoint:
    :return:
    """
    return model.Transmit_Power_Unspecified_Negative_Direction_MW[line, timepoint] \
        >= -model.Transmit_Power_Unspecified_MW[line, timepoint]

resolve_model.Transmit_Power_Negative_Direction_Constraint = Constraint(resolve_model.TRANSMISSION_LINES,
                                                                        resolve_model.TIMEPOINTS,
                                                                        rule=negative_direction_transmit_power_rule)


# ##### Flexible loads ##### #

# Electric Vehicles (EVs)

def ev_battery_energy_balance_rule(model, resource, timepoint):
    """
    The total energy in EV batteries in the current timepoint must equal the energy in EV batteries in the previous
    timepoint plus the charging that happened in the last timepoint, adjusted for the charging efficiency,
    minus discharging in the last timepoint, adjusted for the discharging efficiency.
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.Energy_in_EV_Batteries_MWh[resource, timepoint] \
        == model.Energy_in_EV_Batteries_MWh[resource, model.previous_timepoint[timepoint]] \
        + model.Charge_EV_Batteries_MW[resource, model.previous_timepoint[timepoint]] \
        * model.ev_charging_efficiency[resource] \
        - model.driving_energy_demand_mw[resource, model.previous_timepoint[timepoint]]

resolve_model.EV_Energy_Tracking_Constraint = Constraint(resolve_model.EV_RESOURCES, resolve_model.TIMEPOINTS,
                                                         rule=ev_battery_energy_balance_rule)


def ev_charge_rule(model, resource, timepoint):
    """
    EV charging cannot exceed a pre-specified rate based on the number of EVs plugged in.
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.Charge_EV_Batteries_MW[resource, timepoint] \
        <= model.ev_battery_plugged_in_capacity_mw[resource, timepoint]

resolve_model.EV_Charge_Constraint = Constraint(resolve_model.EV_RESOURCES, resolve_model.TIMEPOINTS, rule=ev_charge_rule)


def ev_max_energy_rule(model, resource, timepoint):
    """
    Total EV battery energy capacity.
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.Energy_in_EV_Batteries_MWh[resource, timepoint] \
        <= model.total_ev_battery_energy_capacity_mwh[resource, model.period[timepoint]]

resolve_model.EV_Max_Energy_Constraint = Constraint(resolve_model.EV_RESOURCES, resolve_model.TIMEPOINTS,
                                                    rule=ev_max_energy_rule)


def ev_min_energy_rule(model, resource, timepoint):
    """
    Minimum energy that must be available in EV batteries at all times.
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.Energy_in_EV_Batteries_MWh[resource, timepoint] \
        >= model.minimum_energy_in_ev_batteries_mwh[resource, model.period[timepoint]]

resolve_model.EV_Min_Energy_Constraint = Constraint(resolve_model.EV_RESOURCES, resolve_model.TIMEPOINTS,
                                                    rule=ev_min_energy_rule)


# Hydrogen Electrolysis
def hydrogen_electrolysis_load_max_rule(model, resource, timepoint):
    """
    Hydrogen electrolysis load cannot exceed the pre-specified MW capacity for electrolysis
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """

    return model.Hydrogen_Electrolysis_Load_MW[resource, timepoint] \
        <= model.Operational_Capacity_MW[resource, model.period[timepoint]]

resolve_model.Hydrogen_Electrolysis_Load_Max_Constraint = Constraint(resolve_model.HYDROGEN_ELECTROLYSIS_RESOURCES,
                                                                     resolve_model.TIMEPOINTS,
                                                                     rule=hydrogen_electrolysis_load_max_rule)


def hydrogen_electrolysis_load_min_rule(model, resource, timepoint):
    """
    Hydrogen electrolysis load cannot be lower than a pre-specified MW demand for electrolysis on each period and day
    :param model:
    :param resource:
    :param timepoint:
    :return:
    """
    return model.Hydrogen_Electrolysis_Load_MW[resource, timepoint] \
        >= model.hydrogen_electrolysis_load_min_mw[resource, model.period[timepoint], model.day[timepoint]]

resolve_model.Hydrogen_Electrolysis_Load_Min_Constraint = Constraint(resolve_model.HYDROGEN_ELECTROLYSIS_RESOURCES,
                                                                     resolve_model.TIMEPOINTS,
                                                                     rule=hydrogen_electrolysis_load_min_rule)


def hydrogen_electrolysis_load_daily_rule(model, resource, period, day):
    """
    Hydrogen electrolysis load over the course of each day must equal a pre-specified MW demand
    :param model:
    :param resource:
    :param period:
    :param day:
    :return:
    """
    hydrogen_electrolysis_load = 0.0
    for tmp in model.TIMEPOINTS:
        if model.period[tmp] == period and model.day[tmp] == day:
            hydrogen_electrolysis_load += model.Hydrogen_Electrolysis_Load_MW[resource, tmp]

    return hydrogen_electrolysis_load == model.hydrogen_electrolysis_load_daily_mwh[resource, period, day]

resolve_model.Hydrogen_Electrolysis_Load_Daily_Constraint = Constraint(resolve_model.HYDROGEN_ELECTROLYSIS_RESOURCES,
                                                                       resolve_model.PERIODS,
                                                                       resolve_model.DAYS,
                                                                       rule=hydrogen_electrolysis_load_daily_rule)


# Conventional (shed) demand response
def conventional_dr_max_annual_availability_rule(model, dr_resource, period):
    """
    Total quantity of energy that can be interrupted (permanently shed) in each period.
    :param model:
    :param dr_resource:
    :param period:
    :return:
    """
    conventional_dr_dispatch = 0.0

    # Sum the MWh of conventional DR dispatch in the period
    for timepoint in model.TIMEPOINTS:
        if model.period[timepoint] == period:
            conventional_dr_dispatch += \
                model.Provide_Power_MW[dr_resource, timepoint] * model.day_weight[model.day[timepoint]]

    # Limit the MWh of conventional DR dispatch to the MW capacity
    # multiplied by the hours per year that the DR resource can be called (the RHS is MWh of availability)
    return conventional_dr_dispatch \
           <= model.Operational_Capacity_MW[dr_resource, period] \
           * model.conventional_dr_availability_hours_per_year[dr_resource, period]


resolve_model.Conventional_DR_Annual_Availability_Constraint = \
    Constraint(resolve_model.CONVENTIONAL_DR_RESOURCES,
               resolve_model.PERIODS,
               rule=conventional_dr_max_annual_availability_rule)


def conventional_dr_daily_availability_rule(model, dr_resource, day, period):
    """Constrain shed DR calls to the equivalent energy of one call per day."""
    return (
        sum(
            model.Provide_Power_MW[dr_resource, timepoint]
            for timepoint in model.TIMEPOINTS
            if model.day[timepoint] == day and model.period[timepoint] == period
        )
        <=
        model.Operational_Capacity_MW[dr_resource, period] *
        model.conventional_dr_daily_capacity_factor[dr_resource, period] *
        model.timepoints_per_day
    )

resolve_model.Conventional_DR_Daily_Availability_Constraint = Constraint(
    resolve_model.CONVENTIONAL_DR_RESOURCES,
    resolve_model.DAYS,
    resolve_model.PERIODS,
    rule=conventional_dr_daily_availability_rule)

# ####### Advanced Demand Response, also known as "Shift" per the LBNL DR Potential Study ####### #
if resolve_model.include_flexible_load:
    def flexible_load_shift_max_rule(model, resource, timepoint):
        """
        The maximum amount (MW) that load can be shifted up (system load increases) at each timepoint.
        :param model:
        :param resource:
        :param timepoint:
        :return:
        """
        return model.Shift_Load_Up_MW[resource, timepoint] \
            <= model.Total_Daily_Flexible_Load_Potential_MWh[resource, model.period[timepoint]] \
            * model.shift_load_up_potential_factor[resource, timepoint]

    resolve_model.Max_Flexible_Load_Shift_Constraint = Constraint(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                                  resolve_model.TIMEPOINTS,
                                                                  rule=flexible_load_shift_max_rule)


    def flexible_load_shift_min_rule(model, resource, timepoint):
        """
        The maximum amount (MW) that load can be shifted down (system load decreases) at each timepoint.
        :param model:
        :param resource:
        :param timepoint:
        :return:
        """
        return model.Shift_Load_Down_MW[resource, timepoint] \
            <= model.Total_Daily_Flexible_Load_Potential_MWh[resource, model.period[timepoint]] \
            * model.shift_load_down_potential_factor[resource, timepoint]

    resolve_model.Min_Flexible_Load_Shift_Constraint = Constraint(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                                  resolve_model.TIMEPOINTS,
                                                                  rule=flexible_load_shift_min_rule)


    def flexible_load_shift_energy_neutrality_rule(model, resource, period, day):
        """
        Shift demand response must be energy neutral each day.
        :param model:
        :param resource:
        :param period:
        :param day:
        :return:
        """
        daily_shift_load = float()
        for timepoint in model.TIMEPOINTS:
            if model.period[timepoint] == period and model.day[timepoint] == day:
                daily_shift_load += model.Shift_Load_Up_MW[resource, timepoint]
                daily_shift_load -= model.Shift_Load_Down_MW[resource, timepoint]

        return daily_shift_load == 0

    resolve_model.Flexible_Load_Shift_Energy_Neutrality_Constraint = \
        Constraint(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                   resolve_model.PERIODS,
                   resolve_model.DAYS,
                   rule=flexible_load_shift_energy_neutrality_rule)


    def flexible_load_max_daily_energy_rule(model, resource, period, day):
        """
        Limit on the amount of load that can be shifted on each day. In conjunction
        with flexible_load_shift_energy_neutrality_rule, this constraint limits both Shift_Load_Up and Shift_Load_Down.
        :param model:
        :param resource:
        :param period:
        :param day:
        :return:
        """
        daily_shift_load_down = float()
        for timepoint in model.TIMEPOINTS:
            if model.period[timepoint] == period and model.day[timepoint] == day:
                daily_shift_load_down += model.Shift_Load_Down_MW[resource, timepoint]

        return daily_shift_load_down <= model.Total_Daily_Flexible_Load_Potential_MWh[resource, period]

    resolve_model.Flexible_Load_Max_Daily_Energy_Constraint = Constraint(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                                         resolve_model.PERIODS,
                                                                         resolve_model.DAYS,
                                                                         rule=flexible_load_max_daily_energy_rule)


    def max_flexible_load_shift_potential_rule(model, resource, period):
        """
        This sets a limit for daily MWh of flexible loads for each time period. This is the top of the supply curve.
        :param model:
        :param resource:
        :param period:
        :return:
        """
        return model.Total_Daily_Flexible_Load_Potential_MWh[resource, period] <= \
               model.max_flexible_load_shift_potential_mwh[resource, period]

    resolve_model.Max_Flexible_Load_Shift_Potential_Constraint = \
        Constraint(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                   resolve_model.PERIODS,
                   rule=max_flexible_load_shift_potential_rule)


    def min_flexible_load_installed_energy_capacity_rule(model, resource, period):
        """
        Ensure that a minimum amount (>=0) of flexible load shift is added in each period.
        Currently all flexible load shift is newly built, so cumulative new capacity = total capacity
        :param model:
        :param resource:
        :param period:
        :return:
        """
        return model.Total_Daily_Flexible_Load_Potential_MWh[resource, period] \
            >= model.min_cumulative_new_flexible_load_shift_mwh[resource, period]

    resolve_model.Min_Flexible_Load_Energy_Capacity_Constraint = \
        Constraint(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                   resolve_model.PERIODS,
                   rule=min_flexible_load_installed_energy_capacity_rule)


    def flexible_load_dr_cost_rule(model, resource, flexible_load_cost_curve_index, period):
        """
        LBNL's Demand Response report generates quantities of daily potentially shiftable MWh for given discrete price bins.
        The Resolve front end takes these price bins and generates a piecewise linear representation of them.
        The piecewise linear equations create a cost curve for demand response
        :param model:
        :param resource:
        :param flexible_load_cost_curve_index:
        :param period:
        :return:
        """
        return model.Flexible_Load_DR_Cost[resource, period] \
            >= model.flexible_load_cost_curve_slope[resource, flexible_load_cost_curve_index, period] \
            * model.Total_Daily_Flexible_Load_Potential_MWh[resource, period] \
            + model.flexible_load_cost_curve_intercept[resource, flexible_load_cost_curve_index, period]

    resolve_model.Flexible_Load_Dr_Cost_Constraint = Constraint(resolve_model.FLEXIBLE_LOAD_RESOURCES,
                                                                resolve_model.FLEXIBLE_LOAD_COST_CURVE_INDEX,
                                                                resolve_model.PERIODS,
                                                                rule=flexible_load_dr_cost_rule)


# ##### Constraints for multi-day hydro sharing ##### #
def net_zero_hydro_sharing_rule(model, hydro_resource, period, hydro_sharing_interval):
    """
    Make sure the total hydro energy within the sharing group stays the same before and after hydro sharing
    :param model:
    :param hydro_resource:
    :param period:
    :param hydro_sharing_interval:
    :return:
    """
    net_energy_moved = 0.0
    for day in model.DAYS:
        if model.hydro_sharing_interval_id[day] == hydro_sharing_interval:
            net_energy_moved += (model.Daily_Hydro_Budget_Increase_MWh[hydro_resource, period, day] *
                                 model.day_weight[day])

    return net_energy_moved == 0.0


def min_daily_changes_rule(model, hydro_resource, period, day):
    """
    Constrain daily hydro budget changes to be within a user defined range
    :param model:
    :param hydro_resource:
    :param period:
    :param day:
    :return:
    """
    return - (model.Operational_Capacity_MW[hydro_resource, period] *
              model.daily_max_hydro_budget_decrease_hours[hydro_resource, day]) \
              <= \
              model.Daily_Hydro_Budget_Increase_MWh[hydro_resource, period, day]


def max_daily_changes_rule(model, hydro_resource, period, day):
    """
    Constrain daily hydro budget changes to be within a user defined range
    :param model:
    :param hydro_resource:
    :param period:
    :param day:
    :return:
    """
    return model.Daily_Hydro_Budget_Increase_MWh[hydro_resource, period, day] \
           <= \
          (model.Operational_Capacity_MW[hydro_resource, period] *
           model.daily_max_hydro_budget_increase_hours[hydro_resource, day])


def define_absolute_hydro_moved_rule(model, hydro_resource, period, day):
    """Get the only positive values of energy increase.

    Given the net zero constraint, net_zero_hydro_sharing_rule, we know that exactly
    half of the energy will be increases and half will be decreases. In plain English,
    this constraint now means that you have x GWh of energy to shift to other parts
    of the year.

    :param model:
    :param hydro_resource:
    :param period:
    :param day:
    :return:
    """
    return (model.Positive_Hydro_Budget_Moved_MWh[hydro_resource, period, day]
            >=
            model.Daily_Hydro_Budget_Increase_MWh[hydro_resource, period, day])


def max_absolute_hydro_moved_rule(model, hydro_resource, period, hydro_sharing_interval):
    """
    Constraint the total amount of hydro being moved
    :param model:
    :param hydro_resource:
    :param period:
    :param hydro_sharing_interval:
    :return:
    """
    absolute_energy_moved = 0.0
    for day in model.DAYS:
        if model.hydro_sharing_interval_id[day] == hydro_sharing_interval:
            absolute_energy_moved += (model.Positive_Hydro_Budget_Moved_MWh[hydro_resource, period, day] *
                                      model.day_weight[day])

    return absolute_energy_moved <= (model.Operational_Capacity_MW[hydro_resource, period] *
        model.max_hydro_to_move_around_hours[hydro_resource, hydro_sharing_interval])


# initiate constraints
if resolve_model.multi_day_hydro_energy_sharing:

    resolve_model.Net_Zero_Hydro_Sharing_Constraint = Constraint(
        resolve_model.HYDRO_RESOURCES,
        resolve_model.PERIODS,
        resolve_model.HYDRO_SHARING_INTERVAL,
        rule=net_zero_hydro_sharing_rule)

    resolve_model.Min_Daily_Changes_Constraint = Constraint(
        resolve_model.HYDRO_RESOURCES,
        resolve_model.PERIODS,
        resolve_model.DAYS,
        rule=min_daily_changes_rule)

    resolve_model.Max_Daily_Changes_Constraint = Constraint(
        resolve_model.HYDRO_RESOURCES,
        resolve_model.PERIODS,
        resolve_model.DAYS,
        rule=max_daily_changes_rule)

    resolve_model.Define_Absolute_Hydro_Moved_Constraint = Constraint(
        resolve_model.HYDRO_RESOURCES,
        resolve_model.PERIODS,
        resolve_model.DAYS,
        rule=define_absolute_hydro_moved_rule)

    resolve_model.Max_Absolute_Hydro_Moved_Constraints = Constraint(
        resolve_model.HYDRO_RESOURCES,
        resolve_model.PERIODS,
        resolve_model.HYDRO_SHARING_INTERVAL,
        rule=max_absolute_hydro_moved_rule)


def maximum_ee_investment_in_period_rule(model, resource, period):
    """
    Limit EE investment in each period to max_investment_in_period_aMW
    :param model:
    :param resource:
    :param period:
    :return:
    """

    return model.Build_Capacity_MW[resource, period] <= model.max_investment_in_period_aMW[resource, period]

if resolve_model.allow_ee_investment:

    resolve_model.Maximum_EE_Investment_In_Period_Constraint = Constraint(resolve_model.EE_PROGRAMS,
                                                                          resolve_model.PERIODS,
                                                                          rule=maximum_ee_investment_in_period_rule)


# ------------------------------------ Semi storage zones related constraints ----------------------------------------
def ssz_energy_net_0_rule(model, ssz_zone, period):
    """
    Make sure the energy transmit to and from ssz_zone within a period is net 0
    day weights are applied because the energy accounting.
    GHG emissions from semi storage zones are assumed to be zero,
    so semi storage zones don't appear anywhere in GHG constraints.
    :param model:
    :param ssz_zone:
    :param period:
    :return:
    """

    total_transmit_power_mw = 0.0
    for timepoint in model.TIMEPOINTS:
        if model.period[timepoint] == period:
            total_transmit_power_mw += model.SSZ_Transmit_Power_MW[ssz_zone, timepoint] \
                                       * model.day_weight[model.day[timepoint]]

    return total_transmit_power_mw == 0.0


# The following two constraints define the positive and negative direction versions of SSZ_Transmit_Power_MW,
# which can then be multiplied by directional hurdle, GHG import rate, hurdle rates, or other value.
# Important note: any value multiplied by these variables cannot provide an incentive
# for the directional variable to exceed the absolute value of the non-directional variable in the same direction.
# This means that, for example, a negative cost hurdle rate on the positive direction would give an incentive for
# Transmit_Power_Positive_Direction_MW to be much larger than Transmit_Power_MW
# which is not acceptable because the variables are supposed to be equal to each other when in the same direction.

def ssz_transmit_power_positive_definition_rule(model, ssz_zone, timepoint):
    """

    :param model:
    :param ssz_zone:
    :param timepoint:
    :return:
    """

    return model.SSZ_Positive_Transmit_Power_MW[ssz_zone, timepoint] \
        >= model.SSZ_Transmit_Power_MW[ssz_zone, timepoint]


def ssz_transmit_power_negative_definition_rule(model, ssz_zone, timepoint):
    """

    :param model:
    :param ssz_zone:
    :param timepoint:
    :return:
    """
    return model.SSZ_Negative_Transmit_Power_MW[ssz_zone, timepoint] \
        >= - model.SSZ_Transmit_Power_MW[ssz_zone, timepoint]


def ssz_tx_limit_max_rule(model, ssz_zone, timepoint):
    """
    Constraint the transmitting power is below the transmission limits
    :param model:
    :param ssz_zone:
    :param timepoint:
    :return:
    """
    return model.SSZ_Transmit_Power_MW[ssz_zone, timepoint] <= model.ssz_max_flow_mw[ssz_zone, model.period[timepoint]]


def ssz_tx_limit_min_rule(model, ssz_zone, timepoint):
    """
    Constraint the transmitting power is below the transmission limits
    :param model:
    :param ssz_zone:
    :param timepoint:
    :return:
    """
    return model.ssz_min_flow_mw[ssz_zone, model.period[timepoint]] \
        <= model.SSZ_Transmit_Power_MW[ssz_zone, timepoint]


if resolve_model.allow_semi_storage_zones:
    resolve_model.SSZ_Energy_Net_0_Constraint = Constraint(resolve_model.SEMI_STORAGE_ZONES, resolve_model.PERIODS,
                                                           rule=ssz_energy_net_0_rule)
    resolve_model.SSZ_Transmit_Power_Positive_Definition = Constraint(resolve_model.SEMI_STORAGE_ZONES,
                                                                      resolve_model.TIMEPOINTS,
                                                                      rule=ssz_transmit_power_positive_definition_rule)
    resolve_model.SSZ_Transmit_Power_Negative_Definition = Constraint(resolve_model.SEMI_STORAGE_ZONES,
                                                                      resolve_model.TIMEPOINTS,
                                                                      rule=ssz_transmit_power_negative_definition_rule)
    resolve_model.SSZ_Tx_Limit_Max_Constraint = Constraint(resolve_model.SEMI_STORAGE_ZONES,
                                                           resolve_model.TIMEPOINTS,
                                                           rule=ssz_tx_limit_max_rule)
    resolve_model.SSZ_Tx_Limit_Min_Constraint = Constraint(resolve_model.SEMI_STORAGE_ZONES,
                                                           resolve_model.TIMEPOINTS,
                                                           rule=ssz_tx_limit_min_rule)
