import logging
import os
import json
import calendar
import copy

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from es_gui.tools.btm.btm_dms import BtmDMS
from es_gui.tools.btm.btm_optimizer import BtmOptimizer
import es_gui.tools.btm.readutdata as readutdata

from es_gui.tools.valuation.valuation_dms import ValuationDMS
from es_gui.simulators.valuation import ValuationOptimizerSimulator

import es_gui.tools.plotting_utils as plotting_utils


def valuation_demo_with_simulation():
    with open('valuation_optimizer.log', 'w'):
        pass

    logging.basicConfig(filename='bounds_demo.log', format='[%(levelname)s] %(asctime)s: %(message)s',
                        level=logging.INFO)

    dms = ValuationDMS(save_name='valuation_dms.p', home_path='data', save_data=True)

    year = 2017
    node_name = 'SPPSOUTH_H'
    market_type = 'spp_pfp'

    params = {
        'Energy_capacity': 8,
        'Power_rating': 2,
    }

    revenue_monthly = []
    revenue_monthly_da_forecast = []
    revenue_daily = []
    revenue_daily_da_forecast = []

    for ix, month in enumerate(calendar.month_abbr[1:], start=1): 
        _, num_days = calendar.monthrange(year, ix)

        lmp_da, mcpru_da, mcprd_da = dms.get_spp_data(year, ix, node_name)

        properties = {
            'market_type': 'spp_pfp',
            'solver': 'gurobi',
        }
        data = {
            'price_electricity': lmp_da,
            'price_reg_up': mcpru_da,
            'price_reg_down': mcprd_da,
        }

        # Monthly horizon, perfect foresight
        sim = ValuationOptimizerSimulator()
        sim.run(
            properties=properties,
            data=data,
            simulation_type='monthly_perfect',
            parameters=params,
        )

        revenue_monthly.append(sim.gross_revenue)

        # Monthly horizon, day-ahead presistent forecast
        sim = ValuationOptimizerSimulator()
        sim.run(
            properties=properties,
            data=data,
            simulation_type='monthly_forecast',
            forecast_method='persistent',
            parameters=params,
        )

        revenue_monthly_da_forecast.append(sim.gross_revenue)

        # Daily horizon, perfect foresight
        sim = ValuationOptimizerSimulator()
        sim.run(
            properties=properties,
            data=data,
            simulation_type='daily_perfect',
            parameters=params,
            n_days=num_days,
        )

        revenue_daily.append(sim.gross_revenue)

        # Daily horizon, day-ahead persistent forecast
        sim = ValuationOptimizerSimulator()
        sim.run(
            properties=properties,
            data=data,
            simulation_type='daily_forecast',
            forecast_method='persistent',
            parameters=params,
            n_days=num_days,
        )

        revenue_daily_da_forecast.append(sim.gross_revenue)

    fig, ax = plotting_utils.generate_multisetbar_chart(
        [
        revenue_daily, 
        revenue_daily_da_forecast, 
        revenue_monthly, 
        revenue_monthly_da_forecast
        ],
        cats=[
            'daily (perfect)', 
            'daily (persistent)', 
            'monthly (perfect)', 
            'monthly (persistent)'
            ],
        labels=calendar.month_abbr[1:],
    )

    ax.set_title('Gross Revenue')
    ax.set_ylabel('Gross Revenue [\$]')  # Note the $ is escaped, assuming LaTeX is used to render text.
    
    # Stacked bar chart
    zipped_results = zip(revenue_daily, revenue_daily_da_forecast, revenue_monthly, revenue_monthly_da_forecast)

    fig, ax = plotting_utils.generate_revenue_stackedbar_chart(zipped_results, labels=calendar.month_abbr[1:])

    ax.set_title('Gross Revenue')
    ax.set_ylabel('Gross Revenue [\$]')  # Note the $ is escaped, assuming LaTeX is used to render text.          

    # Bar spread chart
    zipped_results = zip(revenue_daily, revenue_daily_da_forecast, revenue_monthly, revenue_monthly_da_forecast)

    min_rev_per_month = []
    bar_heights = []

    for result_set in zipped_results:
        min_rev_per_month.append(min(result_set))
        bar_heights.append(max(result_set) - min(result_set))

    fig, ax = plotting_utils.generate_bar_chart(bar_heights, bottoms=min_rev_per_month, labels=calendar.month_abbr[1:])

    ax.set_title('Gross Revenue')
    ax.set_ylabel('Gross Revenue [\$]')  # Note the $ is escaped, assuming LaTeX is used to render text.

    sim.results.to_csv('simulator_results.csv')


def valuation_demo():
    with open('valuation_optimizer.log', 'w'):
        pass

    logging.basicConfig(filename='bounds_demo.log', format='[%(levelname)s] %(asctime)s: %(message)s',
                        level=logging.INFO)

    dms = ValuationDMS(save_name='valuation_dms.p', home_path='data', save_data=True)

    year = 2017
    node_name = 'SPPSOUTH_H'
    market_type = 'spp_pfp'

    params = {
        'Energy_capacity': 8,
        'Power_rating': 2,
    }

    revenue_monthly = []
    revenue_monthly_da_forecast = []
    revenue_daily = []
    revenue_daily_da_forecast = []

    for ix, month in enumerate(calendar.month_abbr[1:], start=1): 
        n_hrs = 24
        _, num_days = calendar.monthrange(year, ix)

        lmp_da, mcpru_da, mcprd_da = dms.get_spp_data(year, ix, node_name)

        # Create day-ahead forecast by delaying prices by one day
        lmp_da_forecast = copy.deepcopy(lmp_da)
        lmp_da_forecast = np.append(lmp_da_forecast[-n_hrs:], lmp_da_forecast[:-n_hrs])

        mcpru_da_forecast = copy.deepcopy(mcpru_da)
        mcpru_da_forecast = np.append(mcpru_da_forecast[-n_hrs:], mcpru_da_forecast[:-n_hrs])

        mcprd_da_forecast = copy.deepcopy(mcprd_da)
        mcprd_da_forecast = np.append(mcprd_da_forecast[-n_hrs:], mcprd_da_forecast[:-n_hrs])

        # Monthly horizon, perfect foresight
        op = ValuationOptimizer(market_type=market_type)

        op.price_electricity = lmp_da
        op.price_reg_up = mcpru_da
        op.price_reg_down = mcprd_da

        if params:
            op.set_model_parameters(**params)

        op.run()
        # op.reprocess_results(price_electricity=lmp_da)
        revenue_monthly.append(op.gross_revenue)

        # Monthly horizon, day-ahead forecast
        op = ValuationOptimizer(market_type=market_type)

        op.price_electricity = lmp_da_forecast
        op.price_reg_up = mcpru_da_forecast
        op.price_reg_down = mcprd_da_forecast

        if params:
            op.set_model_parameters(**params)

        op.run()
        op.reprocess_results(
            price_electricity=lmp_da,
            price_reg_up=mcpru_da,
            price_reg_down=mcprd_da,
            )
        revenue_monthly_da_forecast.append(op.gross_revenue)
        
        solved_ops_pf = []
        solved_ops_da_forecast = []

        for iy in range(1, num_days+1):
            # Daily horizon, perfect foresight
            op = ValuationOptimizer(market_type=market_type)

            daily_price_electricity = lmp_da[:n_hrs]
            daily_price_reg_up = mcpru_da[:n_hrs]
            daily_price_reg_down = mcprd_da[:n_hrs]

            lmp_da = lmp_da[n_hrs:]
            mcpru_da = mcpru_da[n_hrs:]
            mcprd_da = mcprd_da[n_hrs:]

            op.price_electricity = daily_price_electricity
            op.price_reg_up = daily_price_reg_up
            op.price_reg_down = daily_price_reg_down

            if params:
                op.set_model_parameters(**params)

            op.run()
            solved_ops_pf.append(op)

            # Daily horizon, day-ahead forecast
            op = ValuationOptimizer(market_type=market_type)

            op.price_electricity = lmp_da_forecast[:n_hrs]
            op.price_reg_up = mcpru_da_forecast[:n_hrs]
            op.price_reg_down = mcprd_da_forecast[:n_hrs]

            lmp_da_forecast = lmp_da_forecast[n_hrs:]
            mcpru_da_forecast = mcpru_da_forecast[n_hrs:]
            mcprd_da_forecast = mcprd_da_forecast[n_hrs:]

            if params:
                op.set_model_parameters(**params)

            op.run()
            op.reprocess_results(
                price_electricity=daily_price_electricity,
                price_reg_up=daily_price_reg_up,
                price_reg_down=daily_price_reg_down,
                )
            solved_ops_da_forecast.append(op)
        
        total_revenue = sum(op.gross_revenue for op in solved_ops_pf)
        revenue_daily.append(total_revenue)

        total_revenue = sum(op.gross_revenue for op in solved_ops_da_forecast)
        revenue_daily_da_forecast.append(total_revenue)

    # fig, ax = plotting_utils.generate_multisetbar_chart(
    #     [revenue_daily, revenue_daily_da_forecast, revenue_monthly, revenue_monthly_da_forecast],
    #     cats=['daily horizon', 'daily horizon w/ DA forecast', 'monthly horizon', 'monthly horizon w/ DA forecast'],
    #     labels=calendar.month_abbr[1:],
    # )

    fig, ax = plotting_utils.generate_multisetbar_chart(
        [revenue_daily, revenue_monthly,],
        cats=['daily horizon', 'monthly horizon',],
        labels=calendar.month_abbr[1:],
    )

    ax.set_title('Gross Revenue')
    ax.set_ylabel('Gross Revenue [\$]')  # Note the $ is escaped, assuming LaTeX is used to render text.
    
    #
    zipped_results = zip(revenue_daily, revenue_daily_da_forecast, revenue_monthly, revenue_monthly_da_forecast)

    fig, ax = plotting_utils.generate_revenue_stackedbar_chart(zipped_results, labels=calendar.month_abbr[1:])

    ax.set_title('Gross Revenue')
    ax.set_ylabel('Gross Revenue [\$]')  # Note the $ is escaped, assuming LaTeX is used to render text.          

    #
    zipped_results = zip(revenue_daily, revenue_daily_da_forecast, revenue_monthly, revenue_monthly_da_forecast)

    min_rev_per_month = []
    bar_heights = []

    for result_set in zipped_results:
        min_rev_per_month.append(min(result_set))
        bar_heights.append(max(result_set) - min(result_set))

    fig, ax = plotting_utils.generate_bar_chart(bar_heights, bottoms=min_rev_per_month, labels=calendar.month_abbr[1:])

    ax.set_title('Gross Revenue')
    ax.set_ylabel('Gross Revenue [\$]')  # Note the $ is escaped, assuming LaTeX is used to render text.        
    # plt.show()


def btm_demo(rate_structure_path, load_profile_path, pv_profile_path=None):
    with open('btm_optimizer.log', 'w'):
        pass

    logging.basicConfig(filename='bounds_demo.log', format='[%(levelname)s] %(asctime)s: %(message)s',
                        level=logging.INFO)
    
    dms = BtmDMS(save_name='btm_dms.p', home_path=os.path.join('data'))

    with open(rate_structure_path, 'r') as f:
        rate_structure = json.load(f)
    
    year = 2019

    params = {
        'Energy_capacity': 400,
        'Power_rating': 100,
    }

    weekday_energy_schedule = rate_structure['energy rate structure']['weekday schedule']
    weekend_energy_schedule = rate_structure['energy rate structure']['weekend schedule']
    weekday_demand_schedule = rate_structure['demand rate structure']['weekday schedule']
    weekend_demand_schedule = rate_structure['demand rate structure']['weekend schedule']

    nem_type = 2 if rate_structure['net metering']['type'] else 1
    nem_rate = None if rate_structure['net metering']['type'] else rate_structure['net metering']['energy sell price']

    rate_df = readutdata.input_df(year, weekday_energy_schedule, weekend_energy_schedule, weekday_demand_schedule, weekend_demand_schedule)

    bills_monthly = []
    savings_monthly = []
    bills_daily = []
    savings_daily = []

    charges = []

    for ix, month in enumerate(calendar.month_abbr[1:], start=1):
    # for ix, month in enumerate(['Jan',], start=1):
        load_profile = dms.get_load_profile_data(
            load_profile_path,
            ix
        )

        if pv_profile_path is not None:
            pv_profile = dms.get_pv_profile_data(
                pv_profile_path,
                ix
            )

        _, num_days = calendar.monthrange(year, ix)

        charges_month = {}

        # Month time horizon
        op = BtmOptimizer()

        # Build op inputs.
        rate_df_month = rate_df.loc[(rate_df['month'] == ix)]

        # Populate op.
        op.tou_energy_schedule = rate_df_month['tou_energy_schedule'].values
        op.tou_demand_schedule = rate_df_month['tou_demand_schedule'].values

        op.tou_energy_rate = [x[1] for x in rate_structure['energy rate structure']['energy rates'].items()]
        op.tou_demand_rate = [x[1] for x in rate_structure['demand rate structure']['time of use rates'].items()]
        op.flat_demand_rate = rate_structure['demand rate structure']['flat rates'][month]

        op.nem_type = nem_type
        op.nem_rate = nem_rate

        op.load_profile = load_profile
        op.load_profile_metadata = load_profile

        if pv_profile_path is not None:
            op.pv_profile = pv_profile
            op.pv_profile_metadata = pv_profile
        else:
            op.pv_profile = np.zeros(len(load_profile))

        op.rate_structure_metadata = rate_structure

        if params:
            op.set_model_parameters(**params)

        op.run()

        charges_month['total_with_es_month'] = op.total_bill_with_es
        charges_month['total_without_es_month'] = op.total_bill_without_es
        charges_month['demand_charge_with_es_month'] = op.demand_charge_with_es
        charges_month['demand_charge_without_es_month'] = op.demand_charge_without_es
        charges_month['energy_charge_with_es_month'] = op.energy_charge_with_es
        charges_month['energy_charge_without_es_month'] = op.energy_charge_without_es

        total_bill_with_es_month = op.total_bill_with_es
        
        bills_monthly.append(op.total_bill_with_es)
        savings_monthly.append(op.total_bill_without_es - op.total_bill_with_es)

        tou_demand_rate = [x[1] for x in rate_structure['demand rate structure']['time of use rates'].items()]
        n_tou_demand_periods = len(tou_demand_rate)
        n_hrs = 24

        solved_ops = []
        peak_per_period_per_day = []

        for iy in range(1, num_days+1):
            op = BtmOptimizer()

            # Build op inputs.
            rate_df_day = rate_df.loc[(rate_df['month'] == ix) & (rate_df['day'] == iy)]

            # Populate op.
            op.tou_energy_schedule = rate_df_day['tou_energy_schedule'].values
            op.tou_demand_schedule = rate_df_day['tou_demand_schedule'].values

            op.tou_energy_rate = [x[1] for x in rate_structure['energy rate structure']['energy rates'].items()]

            # For TOU demand rates per period and flat demand rates per month, set to 0 and calculate at the end of the month.
            op.tou_demand_rate = [0 for x in rate_structure['demand rate structure']['time of use rates'].items()]
            op.flat_demand_rate = 0

            op.nem_type = nem_type
            op.nem_rate = nem_rate

            daily_load_profile = load_profile[:24]
            load_profile = load_profile[24:]
            op.load_profile = daily_load_profile

            if pv_profile_path is not None:
                daily_pv_profile = pv_profile[:24]
                pv_profile = pv_profile[24:]

                op.pv_profile = daily_pv_profile
                op.pv_profile_metadata = pv_profile
            else:
                op.pv_profile = np.zeros(len(daily_load_profile))

            op.rate_structure_metadata = rate_structure
            op.load_profile_metadata = load_profile

            if params:
                op.set_model_parameters(**params)

            op.run()
            solved_op = op

            solved_ops.append(solved_op)

            daily_peak_per_period = []

            for i in range(n_tou_demand_periods):
                listi = [int(op.tou_demand_schedule[t] == i) for t in range(n_hrs)]

                daily_peak = max(op.model.pnet[n]*listi[n] for n in range(n_hrs))
                daily_peak_per_period.append(daily_peak)
            
            peak_per_period_per_day.append(daily_peak_per_period)
        
        peak_per_period_per_day = np.array(peak_per_period_per_day)

        # Compute the monthly bill combining each of the daily horizon sub-problems.
        ## Bill with energy storage
        month_flat_demand_rate = rate_structure['demand rate structure']['flat rates'][month]

        total_bill_with_es_daily = sum(op.total_bill_with_es for op in solved_ops)

        flat_demand_charge_with_es = month_flat_demand_rate*max(op.model.pfpk.value for op in solved_ops)
        total_bill_with_es_daily += flat_demand_charge_with_es
        
        peak_demand_per_period = [max(op.model.ptpk[period].value for op in solved_ops) for period in range(n_tou_demand_periods)]
        tou_demand_charge_with_es = sum(tou_demand_rate[period] * peak_demand_per_period[period] for period in range(n_tou_demand_periods))
        total_bill_with_es_daily += tou_demand_charge_with_es

        ## Bill without energy storage
        total_bill_without_es_daily = sum(op.total_bill_without_es for op in solved_ops)

        peak_demand = np.amax(peak_per_period_per_day)
        flat_demand_charge_without_es = month_flat_demand_rate*peak_demand

        total_bill_without_es_daily += flat_demand_charge_without_es
        tou_demand_charge_without_es = 0

        for period in range(n_tou_demand_periods):
            daily_peaks = peak_per_period_per_day[:, period]
            tou_demand_charge_without_es += tou_demand_rate[period]*daily_peaks.max()

        total_bill_without_es_daily += tou_demand_charge_without_es

        bills_daily.append(total_bill_with_es_daily)
        savings_daily.append(total_bill_without_es_daily - total_bill_with_es_daily)

        charges_month['total_with_es_daily'] = total_bill_with_es_daily
        charges_month['total_without_es_daily'] = total_bill_without_es_daily
        charges_month['demand_charge_with_es_daily'] = flat_demand_charge_with_es + tou_demand_charge_with_es
        charges_month['demand_charge_without_es_daily'] = flat_demand_charge_without_es + tou_demand_charge_without_es
        charges_month['energy_charge_with_es_month'] = sum(op.total_bill_with_es for op in solved_ops)
        charges_month['energy_charge_without_es_month'] = sum(op.total_bill_without_es for op in solved_ops)

        charges.append(charges_month)
    
    charges_df = pd.DataFrame.from_records(charges)
    charges_df.to_csv('charges.csv')
    
    fig, ax = plotting_utils.generate_multisetbar_chart(
        [bills_daily, bills_monthly],
        cats=['daily horizon', 'monthly horizon'],
        labels=calendar.month_abbr[1:],
    )

    ax.set_title('Total Bill with Energy Storage')
    ax.set_ylabel('Total Bill [\$]')  # Note the $ is escaped, assuming LaTeX is used to render text.

    fig, ax = plotting_utils.generate_multisetbar_chart(
        [savings_daily, savings_monthly],
        cats=['daily horizon', 'monthly horizon'],
        labels=calendar.month_abbr[1:],
    )

    ax.set_title('Total Savings with Energy Storage')
    ax.set_ylabel('Total Savings [\$]')  # Note the $ is escaped, assuming LaTeX is used to render text.


    plt.show()


if __name__ == '__main__':
    rate_structure_path = os.path.join('data', 'rate_structures', 'mySFhotelPGE.json')
    load_profile_path = os.path.join('data', 'load', 'commercial', 'USA_CA_San.Francisco.Intl.AP.724940_TMY3', 'RefBldgLargeHotelNew2004_7.1_5.0_3C_USA_CA_SAN_FRANCISCO.csv')
    pv_profile_path = os.path.join('data', 'pv', '50kwSF.json')

    # btm_demo(
    #     rate_structure_path, 
    #     load_profile_path, 
    #     pv_profile_path
    # )

    # valuation_demo()

    valuation_demo_with_simulation()

    plt.show()