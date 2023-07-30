import os
import data_util
import pandas as pd

def impl_dp(exp_dir, exp_list, data_processor):
    tracing_path_list = [os.path.join(exp_dir, exp) for exp in exp_list]    
    analysis_results = [data_processor(tracing_path).run() for tracing_path in tracing_path_list] 
    indicators_intrested = pd.concat([result[0] for result in analysis_results], axis=1, keys=exp_list)
    indicators_intrested['count_incre'] = indicators_intrested.apply(lambda row: (row == 'increasing').sum(), axis=1)
    indicators_intrested['count_decre'] = indicators_intrested.apply(lambda row: (row == 'decreasing').sum(), axis=1)
    indicators_data = pd.concat([result[1] for result in analysis_results], axis=1, keys=exp_list) 

    import pickle as pkl
    pkl.dump(indicators_data, open(os.path.join(exp_dir, 'indicators_data.pkl'), 'wb'))
    # indicators_intrested.to_csv(os.path.join(exp_dir, 'indicators_intrested.csv'))

impl_dp('e://data', ['2-21-10app1', '2-27-10app1', '3-1-10app1-modified','4-5-10app2','4-6-10app2', '3-8-10app2', '3-13-10app3','3-19-10app3','3-20-10app3'], data_util.DataProcessor)
# impl_dp('e://data', ['3-29-10app3-continue', '4-11-10app2-continue', '4-19-10app1-continue','4-20-10app1-continue'], data_util.SampleDataProcessor)     
# impl_dp('e://data/pre', ['11-28-10app1' ,'12-1-10app1', '12-2-10app1', '12-3-1app', '3-8-1app'], data_util.PreDataProcessor)