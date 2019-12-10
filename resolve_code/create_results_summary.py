#!/usr/bin/env python

"""
This script aggregates and summarizes results, and collects all of the necessary files for the results viewer.

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
import pandas as pd
import numpy as np
import shutil


def create_summaries(results_directory):
    """
    The summary directory contains various aggregations and combinations of the data in the results files.
    Only data in the summary directory is imported into the results viewer.
    :param results_directory:
    :return:
    """
    print('Creating summary files...')
    summaries_directory = os.path.join(results_directory, "summary")
    dispatch_summaries_directory = os.path.join(summaries_directory, "dispatch")

    # Create summaries directory
    create_summaries_directory(summaries_directory, dispatch_summaries_directory)

    # Hourly operations by zone and resource
    calculate_hourly_operations_by_zone_resource(results_directory, dispatch_summaries_directory)

    # Annual energy by resource-zone-contract
    calculate_annual_energy_by_resource_zone_contract(results_directory, summaries_directory)

    # Annual load by zone
    calculate_annual_load_by_zone(results_directory, summaries_directory)

    # Annual curtailment by zone
    calculate_annual_curtailment_by_zone(results_directory, summaries_directory)

    # Annual operational costs by resource-zone-contract
    calculate_annual_operational_costs_by_resource_zone_contract(results_directory, summaries_directory)

    # Annual fuel burn by resource-zone-contract
    calculate_fuel_burn(results_directory, summaries_directory)

    # Annual transmission flows
    calculate_annual_flows_by_path(results_directory, summaries_directory)

    # Annual GHG imports
    calculate_annual_ghg_imports(results_directory, summaries_directory)

    # Annual unbundled RPS purchases
    calculate_annual_unbundled_rps_purchases(results_directory, summaries_directory)

    # Copy some files to other directories for the Excel results user interface
    copy_results_files_to_summary_directory(results_directory, summaries_directory, dispatch_summaries_directory)


def create_summaries_directory(summaries_directory, dispatch_summaries_directory):
    """
    Create the summary directory. Gets called by create_summaries()
    :param summaries_directory:
    :param dispatch_summaries_directory:
    :return:
    """
    if not os.path.exists(summaries_directory):
        os.mkdir(summaries_directory)

    if not os.path.exists(dispatch_summaries_directory):
        os.mkdir(dispatch_summaries_directory)


def calculate_hourly_operations_by_zone_resource(results_directory, dispatch_summaries_directory):
    """
    Calculate hourly operations by resource and zone.
    :param results_directory:
    :param dispatch_summaries_directory:
    :return:
    """
    print('...aggregating operations to resource and zone...')
    operations = pd.read_csv(os.path.join(results_directory, "operations.csv"))
    operations_by_zone_resource_tmp = \
        operations.\
        groupby(["zone", "resource", "period", "timepoint_id", "day", "hour_of_day", "day_weight"]).\
        agg({"power_mw": np.sum,
             "spin_mw": np.sum,
             "upward_reg_mw": np.sum,
             "downward_reg_mw": np.sum,
             "upward_lf_reserve_mw": np.sum,
             "downward_lf_reserve_mw": np.sum,
             "committed_units": np.sum,
             "committed_capacity_mw": np.sum,
             "storage_charging_mw": np.sum,
             "ev_charging_mw": np.sum,
             "flexible_load_final_mw": np.sum,
             "subhourly_dispatch_down_mw": np.sum,
             "subhourly_dispatch_up_mw": np.sum,
             "hydrogen_electrolysis_load_mw": np.sum,
             "scheduled_curtailment_mw": np.sum})

    operations_by_zone_resource_tmp.to_csv(
        os.path.join(dispatch_summaries_directory, "operations_by_zone_resource_tmp.csv"),
        columns=["power_mw",
                 "spin_mw",
                 "upward_reg_mw",
                 "downward_reg_mw",
                 "upward_lf_reserve_mw",
                 "downward_lf_reserve_mw",
                 "committed_units",
                 "committed_capacity_mw",
                 "storage_charging_mw",
                 "ev_charging_mw",
                 "flexible_load_final_mw",
                 "subhourly_dispatch_down_mw",
                 "subhourly_dispatch_up_mw",
                 "hydrogen_electrolysis_load_mw",
                 "scheduled_curtailment_mw"],
        index=True)


def calculate_annual_energy_by_resource_zone_contract(results_directory, summaries_directory):
    """
    Aggregate hourly energy to year-resource-zone-contract (net for storage).
    :param results_directory:
    :param summaries_directory:
    :return:
    """
    print('...aggregating hourly energy to year-resource-zone-contract...')

    operations = pd.read_csv(os.path.join(results_directory, "operations.csv"))

    # all values are not available for all resources, so fill empty values with 0s for net calculation
    operations["power_mw"] = operations["power_mw"].fillna(0)
    operations["ee_ftm_load_reduction_mw"] = operations["ee_ftm_load_reduction_mw"].fillna(0)
    operations["storage_charging_mw"] = operations["storage_charging_mw"].fillna(0)
    operations["ev_charging_mw"] = operations["ev_charging_mw"].fillna(0)
    operations["flexible_load_final_mw"] = operations["flexible_load_final_mw"].fillna(0)
    operations["hydrogen_electrolysis_load_mw"] = operations["hydrogen_electrolysis_load_mw"].fillna(0)
    operations["subhourly_dispatch_down_mw"] = operations["subhourly_dispatch_down_mw"].fillna(0)
    operations["subhourly_dispatch_up_mw"] = operations["subhourly_dispatch_up_mw"].fillna(0)
    operations["scheduled_curtailment_mw"] = operations["scheduled_curtailment_mw"].fillna(0)

    # Add column for energy production per year to the operations data frame
    # negative values indicate an increase in load from flexible loads or storage charging
    operations["net_energy_mwh_per_year"] = \
        (operations["power_mw"]
         + operations["ee_ftm_load_reduction_mw"]
         - operations["storage_charging_mw"]
         - operations["ev_charging_mw"]
         - operations["flexible_load_final_mw"]
         - operations["hydrogen_electrolysis_load_mw"]) \
        * operations["day_weight"]
    # Add column for net subhourly energy balance per year (from reserve provision)
    operations["net_subhourly_energy_mwh_per_year"] = \
        (operations["subhourly_dispatch_up_mw"] - operations["subhourly_dispatch_down_mw"]) \
        * operations["day_weight"]
    # Add column for scheduled curtailment per year
    operations["scheduled_curtailment_mwh_per_year"] = \
        operations["scheduled_curtailment_mw"] * operations["day_weight"]

    # Calculate starts and stops per year for dispatchable units
    operations["units_started_per_year"] = operations["start_units"] * operations["day_weight"]
    operations["units_shut_down_per_year"] = operations["shut_down_units"] * operations["day_weight"]

    annual_energy_by_resource_zone_contract = \
        operations.\
        groupby(["zone", "contract", "resource", "period"]).\
        agg({"net_energy_mwh_per_year": np.sum,
             "net_subhourly_energy_mwh_per_year": np.sum,
             "scheduled_curtailment_mwh_per_year": np.sum,
             "units_started_per_year": np.sum,
             "units_shut_down_per_year": np.sum})

    # Export annual energy to csv
    annual_energy_by_resource_zone_contract.to_csv(
        os.path.join(summaries_directory, "annual_energy.csv"),
        columns=["net_energy_mwh_per_year",
                 "net_subhourly_energy_mwh_per_year",
                 "scheduled_curtailment_mwh_per_year",
                 "units_started_per_year",
                 "units_shut_down_per_year"],
        index=True)


def calculate_annual_load_by_zone(results_directory, summaries_directory):
    """
    Calculate total annual load, unserved energy, and overgeneration by zone.
    :param results_directory:
    :param summaries_directory:
    :return:
    """
    print('...aggregating hourly loads and power balance to zone-year...')
    loads = pd.read_csv(os.path.join(results_directory, "loads_and_power_balance.csv"))
    loads["input_load_mwh_per_year"] = loads["day_weight"] * loads["input_load_mw"]
    loads["flexible_ev_load_mwh_per_year"] = loads["day_weight"] * loads["flexible_ev_load_mw"]
    loads["unserved_energy_mwh_per_year"] = loads["day_weight"] * loads["unserved_energy_mw"]
    loads["overgeneration_mwh_per_year"] = loads["day_weight"] * loads["overgeneration_mw"]
    loads["hydrogen_electrolysis_load_mwh_per_year"] = loads["day_weight"] * loads["hydrogen_electrolysis_load_mw"]
    loads["ee_load_reduction_mwh_per_year"] = loads["day_weight"] * loads["ee_ftm_load_reduction_mw"]
    annual_loads_by_zone = loads.groupby(["zone", "period"]).agg({"input_load_mwh_per_year": np.sum,
                                                                  "flexible_ev_load_mwh_per_year": np.sum,
                                                                  "unserved_energy_mwh_per_year": np.sum,
                                                                  "overgeneration_mwh_per_year": np.sum,
                                                                  "hydrogen_electrolysis_load_mwh_per_year": np.sum,
                                                                  "ee_load_reduction_mwh_per_year": np.sum})
    annual_loads_by_zone.to_csv(
        os.path.join(summaries_directory, "annual_load.csv"),
        columns=["input_load_mwh_per_year",
                 "flexible_ev_load_mwh_per_year",
                 "unserved_energy_mwh_per_year",
                 "overgeneration_mwh_per_year",
                 "hydrogen_electrolysis_load_mwh_per_year",
                 "ee_load_reduction_mwh_per_year"],
        index=True)


def calculate_annual_curtailment_by_zone(results_directory, summaries_directory):
    """
    Calculate total annual curtailment by zone.
    :param results_directory:
    :param summaries_directory:
    :return:
    """
    print('...aggregating hourly curtailment to zone-contract-year...')
    curtailment = pd.read_csv(os.path.join(results_directory, "curtailment.csv"))
    curtailment["scheduled_curtailment_mwh_per_year"] = \
        curtailment["day_weight"] * curtailment["scheduled_curtailment_mw"]
    curtailment["subhourly_curtailment_mwh_per_year"] = \
        curtailment["day_weight"] * (curtailment["subhourly_downward_lf_mwh"])
    curtailment["subhourly_upward_dispatch_mwh_per_year"] = \
        curtailment["day_weight"] * (curtailment["subhourly_upward_lf_mwh"])
    curtailment["curtailment_cost_$_per_year"] = \
        curtailment["day_weight"] * curtailment["curtailment_cost_$"]
    annual_curtailment_by_zone_contract = \
        curtailment.groupby(["zone", "contract", "period"]).agg({"scheduled_curtailment_mwh_per_year": np.sum,
                                                                 "subhourly_curtailment_mwh_per_year": np.sum,
                                                                 "subhourly_upward_dispatch_mwh_per_year": np.sum,
                                                                 "curtailment_cost_$_per_year": np.sum})

    annual_curtailment_by_zone_contract.to_csv(
        os.path.join(summaries_directory, "annual_curtailment.csv"),
        columns=["scheduled_curtailment_mwh_per_year",
                 "subhourly_curtailment_mwh_per_year",
                 "curtailment_cost_$_per_year"],
        index=True)


def calculate_annual_operational_costs_by_resource_zone_contract(results_directory, summaries_directory):
    """
    Calculate annual variable, fuel, startup, and curtailment costs by resource-zone-contract.
    :param results_directory:
    :param summaries_directory:
    :return:
    """
    print('...aggregating hourly operational costs to resource-zone-contract-year...')

    operational_costs = pd.read_csv(os.path.join(results_directory, "operations.csv"))
    hourly_energy_cost = pd.read_csv(os.path.join(results_directory, "loads_and_power_balance.csv")).\
        set_index(["zone","timepoint_id"])["hourly_energy_cost_$_per_mwh"]
    reserve_duals = pd.read_csv(os.path.join(results_directory, "reserve_timepoints.csv")).\
        set_index(["timepoint"])[["total_fr_dual_$","partial_fr_dual_$","spin_dual_$",
                                 "upward_lf_dual_$","upward_reg_dual_$",
                                 "max_downward_lf_dual_$","downward_reg_dual_$"]]
    reserve_duals.index.names = ['timepoint_id']

    hourly_energy_cost = operational_costs.join(hourly_energy_cost, on=["zone","timepoint_id"])
    reserve_duals = operational_costs.join(reserve_duals, on=["timepoint_id"])

    # all values are not available for all resources, so fill empty values with 0s for net calculation
    operational_costs["variable_costs_$_per_year"] = \
        operational_costs["day_weight"] * operational_costs["variable_costs_$"].fillna(0)
    operational_costs["fuel_costs_$_per_year"] = \
        operational_costs["day_weight"] * operational_costs["fuel_costs_$"].fillna(0)
    operational_costs["startup_costs_$_per_year"] = \
        operational_costs["day_weight"] * operational_costs["unit_start_costs_$"].fillna(0)
    operational_costs["shutdown_costs_$_per_year"] = \
        operational_costs["day_weight"] * operational_costs["unit_shutdown_costs_$"].fillna(0)
    operational_costs["curtailment_costs_$_per_year"] = \
        operational_costs["day_weight"] * operational_costs["curtailment_costs_$"].fillna(0)

    operational_costs["generation_mwh_per_year"] = \
        operational_costs["day_weight"] * operational_costs["power_mw"].fillna(0)
    operational_costs["energy_value_$_per_year"] = \
        operational_costs["generation_mwh_per_year"] * hourly_energy_cost["hourly_energy_cost_$_per_mwh"]

    operational_costs["total_fr_mw_per_year"] = \
        operational_costs["day_weight"] * operational_costs["freq_response_total_mw"].fillna(0)
    operational_costs["total_fr_value_$_per_year"] = \
        operational_costs["total_fr_mw_per_year"] * reserve_duals["total_fr_dual_$"]

    operational_costs["partial_fr_mw_per_year"] = \
        operational_costs["day_weight"] * operational_costs["freq_response_partial_mw"].fillna(0)
    operational_costs["partial_fr_value_$_per_year"] = \
        operational_costs["partial_fr_mw_per_year"] * reserve_duals["partial_fr_dual_$"]

    operational_costs["spin_mw_per_year"] = \
        operational_costs["day_weight"] * operational_costs["spin_mw"].fillna(0)
    operational_costs["spin_value_$_per_year"] = \
        operational_costs["spin_mw_per_year"] * reserve_duals["spin_dual_$"]

    operational_costs["upward_reg_mw_per_year"] = \
        operational_costs["day_weight"] * operational_costs["upward_reg_mw"].fillna(0)
    operational_costs["upward_reg_value_$_per_year"] = \
        operational_costs["upward_reg_mw_per_year"] * reserve_duals["upward_reg_dual_$"]

    operational_costs["downward_reg_mw_per_year"] = \
        operational_costs["day_weight"] * operational_costs["downward_reg_mw"].fillna(0)
    operational_costs["downward_reg_value_$_per_year"] = \
        operational_costs["downward_reg_mw_per_year"] * reserve_duals["downward_reg_dual_$"]

    operational_costs["upward_lf_mw_per_year"] = \
        operational_costs["day_weight"] * operational_costs["upward_lf_reserve_mw"].fillna(0)
    operational_costs["upward_lf_value_$_per_year"] = \
        operational_costs["upward_lf_mw_per_year"] * reserve_duals["upward_lf_dual_$"]

    operational_costs["downward_lf_mw_per_year"] = \
        operational_costs["day_weight"] * operational_costs["downward_lf_reserve_mw"].fillna(0)
    operational_costs["downward_lf_value_$_per_year"] = \
        operational_costs["downward_lf_mw_per_year"] * reserve_duals["max_downward_lf_dual_$"]

    annual_operational_costs_by_resource_zone_contract = \
        operational_costs.\
        groupby(["resource", "zone", "contract", "period"]).\
        agg({"variable_costs_$_per_year": np.sum,
             "fuel_costs_$_per_year": np.sum,
             "startup_costs_$_per_year": np.sum,
             "shutdown_costs_$_per_year": np.sum,
             "curtailment_costs_$_per_year": np.sum,
             "generation_mwh_per_year":np.sum,
             "energy_value_$_per_year": np.sum,
             "total_fr_mw_per_year": np.sum,
             "total_fr_value_$_per_year": np.sum,
             "partial_fr_mw_per_year": np.sum,
             "partial_fr_value_$_per_year": np.sum,
             "spin_mw_per_year": np.sum,
             "spin_value_$_per_year": np.sum,
             "upward_reg_mw_per_year": np.sum,
             "upward_reg_value_$_per_year": np.sum,
             "downward_reg_mw_per_year": np.sum,
             "downward_reg_value_$_per_year": np.sum,
             "upward_lf_mw_per_year": np.sum,
             "upward_lf_value_$_per_year": np.sum,
             "downward_lf_mw_per_year": np.sum,
             "downward_lf_value_$_per_year": np.sum})

    annual_operational_costs_by_resource_zone_contract.to_csv(
        os.path.join(summaries_directory, "operational_costs.csv"),
        columns=["variable_costs_$_per_year",
                 "fuel_costs_$_per_year",
                 "startup_costs_$_per_year",
                 "shutdown_costs_$_per_year",
                 "curtailment_costs_$_per_year",
                 "generation_mwh_per_year",
                 "energy_value_$_per_year",
                 "total_fr_mw_per_year",
                 "total_fr_value_$_per_year",
                 "partial_fr_mw_per_year",
                 "partial_fr_value_$_per_year",
                 "spin_mw_per_year",
                 "spin_value_$_per_year",
                 "upward_reg_mw_per_year",
                 "upward_reg_value_$_per_year",
                 "downward_reg_mw_per_year",
                 "downward_reg_value_$_per_year",
                 "upward_lf_mw_per_year",
                 "upward_lf_value_$_per_year",
                 "downward_lf_mw_per_year",
                 "downward_lf_value_$_per_year"],
        index=True)


def calculate_fuel_burn(results_directory, summaries_directory):
    """
    Calculate annual fuel burn and GHG emissions by resource-zone-contract.
    :param results_directory:
    :param summaries_directory:
    :return:
    """
    print('...aggregating fuel burn to year-resource-zone-contract...')
    fuel_burn = pd.read_csv(os.path.join(results_directory, "fuel_burn_by_resource.csv"))
    fuel_burn["fuel_burn_mmbtu_per_year"] = fuel_burn["day_weight"] * fuel_burn["fuel_burn_mmbtu"]
    fuel_burn["ghg_tco2_per_year"] = fuel_burn["day_weight"] * fuel_burn["emissions_tco2"]
    fuel_burn["pipeline_biogas_mmbtu_per_year"] = fuel_burn["day_weight"] * fuel_burn["pipeline_biogas_mmbtu"]
    fuel_burn["start_fuel_mmbtu_per_year"] = fuel_burn["day_weight"] * fuel_burn["start_fuel_mmbtu"]

    annual_fuel_burn_by_resource_zone_contract = fuel_burn.\
        groupby(["resource", "fuel", "zone", "contract", "period"]).\
        agg({"fuel_burn_mmbtu_per_year": np.sum,
             "ghg_tco2_per_year": np.sum,
             "pipeline_biogas_mmbtu_per_year": np.sum,
             "start_fuel_mmbtu_per_year": np.sum})

    annual_fuel_burn_by_resource_zone_contract.to_csv(
        os.path.join(summaries_directory, "fuel_burn.csv"),
        columns=["fuel_burn_mmbtu_per_year",
                 "ghg_tco2_per_year",
                 "pipeline_biogas_mmbtu_per_year",
                 "start_fuel_mmbtu_per_year"],
        index=True)


def calculate_annual_flows_by_path(results_directory, summaries_directory):
    """
    Calculate annual transmission flows in each direction on each path.
    Also calculate costs for purchases and sales along transmission lines.
    :param results_directory:
    :param summaries_directory:
    :return:
    """
    print('...aggregating transmission flows to year-transmission-line-direction...')

    hourly_flows = pd.read_csv(os.path.join(results_directory, "transmit_power.csv"))

    # calculate annual flows
    hourly_flows["unspecified_power_mwh_per_year"] = hourly_flows["day_weight"] * hourly_flows["unspecified_power_mw"]
    hourly_flows["unspecified_power_positive_mwh_per_year"] = \
        hourly_flows["day_weight"] * hourly_flows["unspecified_power_positive_direction_mw"]
    hourly_flows["unspecified_power_negative_mwh_per_year"] = \
        hourly_flows["day_weight"] * hourly_flows["unspecified_power_negative_direction_mw"]
    hourly_flows["power_mwh_per_year"] = \
        hourly_flows["day_weight"] * hourly_flows["power_including_dedicated_imports_mw"]
    hourly_flows["hurdle_cost_positive_direction_$_per_year"] = \
        hourly_flows["day_weight"] * hourly_flows["hurdle_cost_positive_direction_$"]
    hourly_flows["hurdle_cost_negative_direction_$_per_year"] = \
        hourly_flows["day_weight"] * hourly_flows["hurdle_cost_negative_direction_$"]

    # count how many hours per year each line is flowing in the positive and negative directions
    # also count the number of hours the line has zero flow
    hourly_flows["positive_flow_hours_per_year"] = \
        hourly_flows.apply(lambda row: (row["day_weight"] if row['power_including_dedicated_imports_mw'] > 0 else 0), axis='columns')
    hourly_flows["negative_flow_hours_per_year"] = \
        hourly_flows.apply(lambda row: (row["day_weight"] if row['power_including_dedicated_imports_mw'] < 0 else 0), axis='columns')
    hourly_flows["zero_flow_hours_per_year"] = \
        hourly_flows.apply(lambda row: (row["day_weight"] if row['power_including_dedicated_imports_mw'] == 0 else 0), axis='columns')

    # calculate energy costs in different ways based on the direction of flow along the line
    # and the price at the source ("from") or destination ("to") zone
    hourly_flows["energy_cost_posdir_fromzone_$_per_year"] = \
        hourly_flows["unspecified_power_positive_mwh_per_year"] * hourly_flows["energy_cost_from_$_per_mwh"]
    hourly_flows["energy_cost_posdir_tozone_$_per_year"] = \
        hourly_flows["unspecified_power_positive_mwh_per_year"] * hourly_flows["energy_cost_to_$_per_mwh"]
    hourly_flows["energy_cost_negdir_fromzone_$_per_year"] = \
        hourly_flows["unspecified_power_negative_mwh_per_year"] * hourly_flows["energy_cost_from_$_per_mwh"]
    hourly_flows["energy_cost_negdir_tozone_$_per_year"] = \
        hourly_flows["unspecified_power_negative_mwh_per_year"] * hourly_flows["energy_cost_to_$_per_mwh"]

    # aggregate to yearly
    annual_flows = hourly_flows.\
        groupby(["transmission_line", "transmission_from", "transmission_to", "period"]).\
        agg({"unspecified_power_mwh_per_year": np.sum,
             "unspecified_power_positive_mwh_per_year": np.sum,
             "unspecified_power_negative_mwh_per_year": np.sum,
             "positive_flow_hours_per_year": np.sum,
             "negative_flow_hours_per_year": np.sum,
             "zero_flow_hours_per_year": np.sum,
             "energy_cost_posdir_fromzone_$_per_year": np.sum,
             "energy_cost_posdir_tozone_$_per_year": np.sum,
             "energy_cost_negdir_fromzone_$_per_year": np.sum,
             "energy_cost_negdir_tozone_$_per_year": np.sum,
             "power_mwh_per_year": np.sum,
             "hurdle_cost_positive_direction_$_per_year": np.sum,
             "hurdle_cost_negative_direction_$_per_year": np.sum})

    # Calculate average flow when positive and average flow when negative
    # the apply here avoids dividing by zero when there are zero hours of flow
    annual_flows["annual_average_positive_mw"] = annual_flows.apply(
        lambda row: (row["unspecified_power_positive_mwh_per_year"] / row["positive_flow_hours_per_year"]
                     if row["positive_flow_hours_per_year"] > 0 else 0), axis='columns')
    annual_flows["annual_average_negative_mw"] = annual_flows.apply(
        lambda row: (row["unspecified_power_negative_mwh_per_year"] / row["negative_flow_hours_per_year"]
                     if row["negative_flow_hours_per_year"] > 0 else 0), axis='columns')

    annual_flows.to_csv(
        os.path.join(summaries_directory, "transmission_flows.csv"),
        columns=["unspecified_power_mwh_per_year",
                 "unspecified_power_positive_mwh_per_year",
                 "unspecified_power_negative_mwh_per_year",
                 "annual_average_positive_mw",
                 "annual_average_negative_mw",
                 "positive_flow_hours_per_year",
                 "negative_flow_hours_per_year",
                 "zero_flow_hours_per_year",
                 "energy_cost_posdir_fromzone_$_per_year",
                 "energy_cost_posdir_tozone_$_per_year",
                 "energy_cost_negdir_fromzone_$_per_year",
                 "energy_cost_negdir_tozone_$_per_year",
                 "power_mwh_per_year",
                 "hurdle_cost_positive_direction_$_per_year",
                 "hurdle_cost_negative_direction_$_per_year"
                 ],
        index=True)


def calculate_annual_ghg_imports(results_directory, summaries_directory):
    """
    Calculate annual ghg imports by transmission line.
    :param results_directory:
    :param summaries_directory:
    :return:
    """
    print('...aggregating hourly ghg imports to line-year...')

    ghg_imports = pd.read_csv(os.path.join(results_directory, "ghg_imports.csv"))
    ghg_imports["positive_direction_ghg_imports_tco2_per_year"] = \
        ghg_imports["day_weight"] * ghg_imports["positive_direction_ghg_import_tco2"]
    ghg_imports["negative_direction_ghg_imports_tco2_per_year"] = \
        ghg_imports["day_weight"] * ghg_imports["negative_direction_ghg_import_tco2"]

    annual_ghg_imports_by_line_period = \
        ghg_imports.\
        groupby(["line", "period"]).\
        agg({"positive_direction_ghg_imports_tco2_per_year": np.sum,
             "negative_direction_ghg_imports_tco2_per_year": np.sum})

    annual_ghg_imports_by_line_period.to_csv(
        os.path.join(summaries_directory, "ghg_imports.csv"),
        columns=["positive_direction_ghg_imports_tco2_per_year",
                 "negative_direction_ghg_imports_tco2_per_year"],
        index=True)


def calculate_annual_unbundled_rps_purchases(results_directory, summaries_directory):
    """
    Calculate the energy cost of unbundled generation (contracted to RPS zones but balanced elsewhere).
    :param results_directory:
    :param summaries_directory:
    :return:
    """
    print('...aggregating unbundled purchases by year...')

    loads_and_power_balance = pd.read_csv(os.path.join(results_directory, "loads_and_power_balance.csv"))

    # note: unbundled_rps_generation_mw = 0 for the RPS zones because this column
    # represents RECs that are generated outside the RPS zones.
    loads_and_power_balance["unbundled_rps_generation_mwh_per_year"] = \
        loads_and_power_balance["unbundled_rps_generation_mw"] * \
        loads_and_power_balance["day_weight"]

    # Price all generation contracted to the RPS zone but balanced elsewhere
    # at the local energy cost of the zone in which the resource is balanced
    loads_and_power_balance["unbundled_rps_energy_cost_$_per_year"] = \
        loads_and_power_balance["unbundled_rps_generation_mwh_per_year"] * \
        loads_and_power_balance["hourly_energy_cost_$_per_mwh"]

    annual_unbundled_rps_purchases = \
        loads_and_power_balance.\
        groupby(["zone", "period"]).\
        agg({"unbundled_rps_generation_mwh_per_year": np.sum,
             "unbundled_rps_energy_cost_$_per_year": np.sum})

    annual_unbundled_rps_purchases.to_csv(
        os.path.join(summaries_directory, "annual_unbundled_rps_purchases.csv"),
        columns=["unbundled_rps_generation_mwh_per_year",
                 "unbundled_rps_energy_cost_$_per_year"],
        index=True)


def copy_results_files_to_summary_directory(results_directory, summaries_directory, dispatch_summaries_directory):
    """
    Copy some disaggregated results files to the summary directory to facilitate data import
    to the Excel results user interface.
    :param results_directory:
    :param summaries_directory:
    :param dispatch_summaries_directory:
    :return:
    """

    for file_name in ["transmission_costs.csv",
                      "transmission_build.csv",
                      "storage_build.csv",
                      "resource_build.csv",
                      "planning_reserve_margin.csv",
                      "energy_sufficiency.csv",
                      "local_capacity_resources.csv",
                      "rps.csv",
                      "ghg.csv"]:

        file_path = os.path.join(results_directory, file_name)
        if os.path.isfile(file_path):
            shutil.copy(file_path, summaries_directory)

    # ### Dispatch summaries ### #
    for file_name in ["curtailment.csv",
                      "loads_and_power_balance.csv",
                      "transmit_power.csv"]:

        file_path = os.path.join(results_directory, file_name)
        if os.path.isfile(file_path):
            shutil.copy(file_path, dispatch_summaries_directory)
