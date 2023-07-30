import os
import sqlite3 as db
import ast
import pymannkendall as mk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import f_oneway
    
thread_sql = f'''
    SELECT process_name, thread_name, sum(uniform_time_ms) AS total_value
    FROM ctp_metrics
    WHERE thread_name NOT LIKE 'Binder:%'
    AND process_name IN ('system_server','system:ui','surfaceflinger','dex2oat','com.android.systemui')
    OR process_name LIKE 'com.oplus.%'
    AND ts > (SELECT min(record_timestamp) FROM frk_info) * 1000
    AND ts < (SELECT max(finish_timestamp) FROM frk_info) * 1000
    GROUP BY process_name, thread_name
    UNION ALL
    SELECT process_name, 'Binder Threads' as thread_name, sum(uniform_time_ms) AS total_value
    FROM ctp_metrics
    WHERE thread_name LIKE 'Binder:%'
    AND process_name IN ('system_server','system:ui','surfaceflinger','dex2oat','com.android.systemui')
    OR process_name LIKE 'com.oplus.%'
    AND ts > (SELECT min(record_timestamp) FROM frk_info) * 1000
    AND ts < (SELECT max(finish_timestamp) FROM frk_info) * 1000 
'''

gc_sql = f'''
    SELECT state_name, sum(duration_ms) AS total_value
    FROM gc_trace
    WHERE ts > (SELECT min(record_timestamp) FROM frk_info) * 1000
    AND ts < (SELECT max(finish_timestamp) FROM frk_info) * 1000
    GROUP BY state_name
    UNION ALL
    SELECT 'total gc' AS state_name, sum(duration_ms) AS total_value
    FROM gc_trace
    WHERE ts > (SELECT min(record_timestamp) FROM frk_info) * 1000
    AND ts < (SELECT max(finish_timestamp) FROM frk_info) * 1000 
'''

gc_process_sql = f'''
    SELECT process_name, sum(duration_ms) AS total_value
    FROM gc_trace
    WHERE ts > (SELECT min(record_timestamp) FROM frk_info) * 1000
    AND ts < (SELECT max(finish_timestamp) FROM frk_info) * 1000
    GROUP BY process_name 
'''

binder_sql = f'''
    SELECT code_id, interface_name, sum(duration_ms) AS total_value
    FROM binder_trace
    WHERE ts > (SELECT min(record_timestamp) FROM frk_info) * 1000
    AND ts < (SELECT max(finish_timestamp) FROM frk_info) * 1000
    AND endpoint_type = 'BN'
    AND process_mode = 'BLOCK'
    AND process_name = 'system_server'
    GROUP BY code_id, interface_name
    HAVING total_value > 5
    AND total_value != 'NaN'
'''

lock_sql = f'''
    SELECT caller_thread_name, sum(duration_ms) AS total_value
    FROM lock_contention_trace
    WHERE caller_thread_name NOT LIKE 'Binder:%'
    AND ts > (SELECT min(record_timestamp) FROM frk_info) * 1000
    AND ts < (SELECT max(finish_timestamp) FROM frk_info) * 1000
    AND caller_process_name = 'system_server'
    GROUP BY caller_thread_name
    UNION ALL
    SELECT 'Binder Threads' as caller_thread_name, sum(duration_ms) AS total_value
    FROM lock_contention_trace
    WHERE caller_thread_name LIKE 'Binder:%'
    AND caller_process_name = 'system_server'
    AND ts > (SELECT min(record_timestamp) FROM frk_info) * 1000
    AND ts < (SELECT max(finish_timestamp) FROM frk_info) * 1000
'''

def extract_db(db_list, sql, merge_on):
    result = None
    for i, db_file in enumerate(db_list):
        conn = db.connect(db_file)
        df = pd.read_sql_query(sql, conn)
        df.rename(columns={'total_value':f'{i}'}, inplace = True)
        if i == 0:
            result = df
        else:
            result = pd.merge(result, df, how='outer', on = merge_on)
            # result = merge_df(result, df, how='outer', on = merge_on)
    result.dropna(axis=0, inplace=True)
    return result

def extract_db_divide(db_list, sql, merge_on, slice_num = 50):
    import re
    result = None
    conn = db.connect(db_list[0])
    min_time = pd.read_sql_query(f"SELECT min(record_timestamp) FROM frk_info", conn).iloc[0, 0] * 1000
    max_time = pd.read_sql_query(f"SELECT max(finish_timestamp) FROM frk_info", conn).iloc[0, 0] * 1000
    for i in range(slice_num):
        sql = re.sub('ts > .+\n', f'ts > {min_time + (max_time - min_time) *  i / slice_num}\n', sql)
        sql = re.sub('ts < .+\n', f'ts < {min_time + (max_time - min_time) *  (i+1) / slice_num}\n', sql)
        df = pd.read_sql_query(sql, conn)
        df.rename(columns={'total_value':f'{i}'}, inplace = True)
        if i == 0:
            result = df
        else:
            result = pd.merge(result, df, how='outer', on = merge_on)
            # result = merge_df(result, df, how='outer', on = merge_on)
    result.dropna(axis=0, inplace=True)
    return result

def get_times(db_list, table_name):
    indicators_intrested = pd.Series(dtype='str')
    indicators_data = pd.Series(dtype='object')
    result = []
    for i, db_file in enumerate(db_list):
        conn = db.connect(db_file)
        df = pd.read_sql_query(f"select count(*) from {table_name}\
                                WHERE ts > (SELECT min(record_timestamp) FROM frk_info) * 1000\
                                AND ts < (SELECT max(finish_timestamp) FROM frk_info) * 1000", conn)
        result.append(df.iat[0,0])
    if not any(result):
        return None, None
    mk_res = mk.original_test(result)
    if mk_res.trend == 'increasing':
        print(f"Indicator {table_name} Analysis:")
        print(mk_res)
        print('-----------------')
        indicators_intrested[table_name] = mk_res.trend
    indicators_data[table_name] = result
    return indicators_intrested, indicators_data

def get_times_divide(db_list, table_name, slice_num = 50):
    indicators_intrested = pd.Series(dtype='str')
    indicators_data = pd.Series(dtype='object')
    result = []
    conn = db.connect(db_list[0])
    min_time = pd.read_sql_query(f"SELECT min(record_timestamp) FROM frk_info", conn).iloc[0, 0] * 1000
    max_time = pd.read_sql_query(f"SELECT max(finish_timestamp) FROM frk_info", conn).iloc[0, 0] * 1000
    for i in range(slice_num):
        df = pd.read_sql_query(f"select count(*) from {table_name}\
                                WHERE ts > {min_time + (max_time - min_time) *  i / slice_num}\
                                AND ts < {min_time + (max_time - min_time) *  (i+1) / slice_num}", conn)
        result.append(df.iat[0,0])
    if not any(result):
        return None, None
    mk_res = mk.original_test(result)
    if mk_res.trend == 'increasing':
        print(f"Indicator {table_name} Analysis:")
        print(mk_res)
        print('-----------------')
        indicators_intrested[table_name] = mk_res.trend
    indicators_data[table_name] = result
    return indicators_intrested, indicators_data

def get_time(db_list, table_name):
    indicators_intrested = pd.Series(dtype='str')
    indicators_data = pd.Series(dtype='object')
    result = []
    for i, db_file in enumerate(db_list):
        conn = db.connect(db_file)
        df = pd.read_sql_query(f"select sum(duration_ms) from {table_name}\
                                WHERE ts > (SELECT min(record_timestamp) FROM frk_info) * 1000\
                                AND ts < (SELECT max(finish_timestamp) FROM frk_info) * 1000", conn)
        result.append(df.iat[0,0])
    if not any(result):
        return None, None
    mk_res = mk.original_test(result)
    if mk_res.trend == 'increasing':
        print(f"Indicator {table_name} Analysis:")
        print(mk_res)
        print('-----------------')
        indicators_intrested[table_name] = mk_res.trend
    indicators_data[table_name] = result
    return indicators_intrested, indicators_data

def get_time_divide(db_list, table_name, slice_num = 50):
    indicators_intrested = pd.Series(dtype='str')
    indicators_data = pd.Series(dtype='object')
    result = []
    conn = db.connect(db_list[0])
    min_time = pd.read_sql_query(f"SELECT min(record_timestamp) FROM frk_info", conn).iloc[0, 0] * 1000
    max_time = pd.read_sql_query(f"SELECT max(finish_timestamp) FROM frk_info", conn).iloc[0, 0] * 1000
    for i in range(slice_num):
        df = pd.read_sql_query(f"select sum(duration_ms) from {table_name}\
                                WHERE ts > {min_time + (max_time - min_time) *  i / slice_num}\
                                AND ts < {min_time + (max_time - min_time) *  (i+1) / slice_num}", conn)
        result.append(df.iat[0,0])
    if not any(result):
        return None, None
    mk_res = mk.original_test(result)
    if mk_res.trend == 'increasing':
        print(f"Indicator {table_name} Analysis:")
        print(mk_res)
        print('-----------------')
        indicators_intrested[table_name] = mk_res.trend
    indicators_data[table_name] = result
    return indicators_intrested, indicators_data

def mk_result(db_list, sql, from_index, entity_names):
    df = extract_db(db_list, sql, entity_names)
    indicators_intrested = pd.Series(dtype='str')
    indicators_data = pd.Series(dtype='object')
    print('-----------------')
    for _, row in df.iterrows():
        mk_res = mk.original_test(row.tolist()[from_index:])
        if mk_res.trend == 'increasing':
            for entity_name in entity_names:
                print(row[entity_name])
            indicators_intrested[' '.join([str(row[entity_name]) for entity_name in entity_names])] = mk_res.trend
            print(mk_res)
        indicators_data[' '.join([str(row[entity_name]) for entity_name in entity_names])] = row.tolist()[from_index:]
    return indicators_intrested, indicators_data

def mk_result_divide(db_list, sql, from_index, entity_names):
    df = extract_db_divide(db_list, sql, entity_names)
    indicators_intrested = pd.Series(dtype='str')
    indicators_data = pd.Series(dtype='object')
    print('-----------------')
    for _, row in df.iterrows():
        mk_res = mk.original_test(row.tolist()[from_index:])
        if mk_res.trend == 'increasing':
            for entity_name in entity_names:
                print(row[entity_name])
            indicators_intrested[' '.join([str(row[entity_name]) for entity_name in entity_names])] = mk_res.trend
            print(mk_res)
        indicators_data[' '.join([str(row[entity_name]) for entity_name in entity_names])] = row.tolist()[from_index:]
    return indicators_intrested, indicators_data

def color_generator(theme='ayaka'):
    color_dict = {}
    color_dict['ayaka'] = [(65, 76, 135), (156, 179, 212), (34, 36, 73), (175, 90, 118)]
    color_dict['ayaka_twin'] = [(156, 179, 212), (175, 90, 118)]
    color_dict['ayaka_twin2'] = [(65, 76, 135), (175, 90, 118)]
    color_to_float = lambda colors: tuple(c / 255 for c in colors)
    list_to_iter = list(map(color_to_float, color_dict[theme]))
    import random
    import itertools
    start_index = random.randint(0, len(list_to_iter) - 1)
    cycled_list = itertools.cycle(list_to_iter[start_index:] + list_to_iter[:start_index])
    while True:
        yield next(cycled_list)

def plot_with_trend(data, label=None, s=None):
    if isinstance(data, str):
        data = ast.literal_eval(data)
    mk_res = mk.original_test(data)
    x_len = len(data)
    x = np.linspace(0, (x_len - 1), 100)
    y = mk_res.slope * x + mk_res.intercept
    gen = color_generator()
    plt.scatter(range(len(data)), data, label=label, color=next(gen), s=s)
    plt.plot(x, y, color=next(gen))
    
class DataProcessor:
    def __init__(self, tracing_path):
        self.tracing_path = tracing_path
        self.len = len([file for file in os.listdir(self.tracing_path) if os.path.isfile(os.path.join(self.tracing_path, file)) and file.startswith('tracing')])
        self.indicators_intrested = pd.Series(dtype='str')
        self.indicators_data = pd.Series(dtype='object')
        
    def tracing_process(self):
        data_range = range(self.len)
        tracing_data_list = [pd.read_csv(f'{self.tracing_path}/tracing{str(i)}.csv') for i in data_range]
        for indicator in ['mem_free','mem_available','rss_ms','rss_ss', 'rss_sf', 'rss_ui', 'cache', 'swap_cached', 'mem_locked','mem_shared', 'slab', 'vmalloc_total', 'vmalloc_used', 'kernel_locks']:
            anova_text = ''
            avg_value = {}
            for i, tracing_data in enumerate((tracing_data_list)):
                anova_text += f"tracing_data_list[{i}]['{indicator}'], "
                if indicator not in avg_value.keys():
                    avg_value[indicator] = [tracing_data[f'{indicator}'].mean()]
                else:
                    avg_value[indicator].append(tracing_data[f'{indicator}'].mean())
            f, p = eval(f"f_oneway({anova_text}axis=0)")
            # print(f'ANOVA: F={f}, p={p}') # p<0.05, reject null hypothesis, there is significant difference between groups
            mk_res = mk.original_test(avg_value[indicator])
            if mk_res.trend != 'no trend':
                print(f"Indicator {indicator} Analysis:")
                print(mk_res)
                print('-----------------')
                self.indicators_intrested[indicator] = mk_res.trend
            self.indicators_data[indicator] = avg_value[indicator]
            
        for indicator in ['reads_completed','reads_merged','sectors_read','time_read','writes_completed','writes_merged','sectors_write','time_write','io_time','weighted_io_time','discards_completed','discards_merged','sectors_discard','time_discard',
                                        'user_time','nice_time','iowait_time','steal_time','pgfree','pgpgin','pgpgout','slabs_scanned','pgfault','pgmajfault']:
            anova_text = ''
            avg_value = {}
            avg_gap = {}
            for i, tracing_data in enumerate((tracing_data_list)):
                anova_text += f"tracing_data_list[{i}]['{indicator}'], "
                if indicator not in avg_value.keys():
                    avg_value[indicator] = [tracing_data[f'{indicator}'].mean()]
                else:
                    avg_value[indicator].append(tracing_data[f'{indicator}'].mean())
            avg_gap[indicator] = [avg_value[indicator][i+1]-avg_value[indicator][i] for i in range(len(avg_value[indicator])-1)]
            if not all(gap == 0 for gap in avg_gap[indicator]):
                f, p = eval(f"f_oneway({anova_text}axis=0)")
            # print(f'ANOVA: F={f}, p={p}') # p<0.05, reject null hypothesis, there is significant difference between groups
            mk_res = mk.original_test(avg_gap[indicator])
            if mk_res.trend == 'increasing':
                print(f"Indicator {indicator} Analysis:")
                print(mk_res)
                print('-----------------')
                self.indicators_intrested[indicator] = mk_res.trend
            self.indicators_data[indicator] = avg_gap[indicator]
            
    def jank_process(self):
        if any(name.startswith('jank') for name in os.listdir(self.tracing_path)):
            data_range = range(self.len)
            jank = []
            for i in data_range:
                jank_path = self.tracing_path + '/jank' + str(i) + '.csv'
                df_jank = pd.read_csv(jank_path)
                total_jank =(df_jank['janky_frame'][df_jank['app'] == 'com.android.systemui'])
                total_frame = (df_jank['total_frame'][df_jank['app'] == 'com.android.systemui'])
                jank.append(100*float(total_jank.iloc[0]/total_frame.iloc[0]))
            if mk.original_test(jank).trend == 'increasing':
                print(f"Indicator jank Analysis:")
                print(mk.original_test(jank))
                print('-----------------')
                self.indicators_intrested['jank'] = mk.original_test(jank).trend
            self.indicators_data['jank'] = jank
    
    def lt_process(self):
        with open(f'{self.tracing_path}/lt.csv', 'r') as f:
            start = f.read(1)
        if start == '0':    
            df_lt = pd.read_csv(f'{self.tracing_path}/lt.csv')
        else:
            df_lt = pd.read_csv(f'{self.tracing_path}/lt.csv', header=None)
        col_num = df_lt.shape[1]
        print('LT Analysis:', end='')
        for i in range(col_num):
            if not df_lt.iloc[:, i].isna().any():
                if mk.original_test(df_lt.iloc[:, i]).trend == 'increasing':
                    print(f'{i}, ', end='')
                    self.indicators_intrested[f'LT_{i}'] = 'increasing' 
                self.indicators_data[f'LT_{i}'] = list(df_lt.iloc[:, i])
    
    def db_process(self):
        db_list = [f'{self.tracing_path}/db/db{i}.db' for i in range(self.len)] 
        if db_list:
            binder_res, binder_data = mk_result(db_list, binder_sql, 2, ['interface_name', 'code_id'])
            gc_res_process, gc_process_data = mk_result(db_list, gc_process_sql, 1, ['process_name'])
            gc_res, gc_data = mk_result(db_list, gc_sql, 1, ['state_name'])
            thread_res, thread_data = mk_result(db_list, thread_sql, 2, ['process_name', 'thread_name'])   
            athena_res, athena_data = get_times(db_list, 'athena_process_clear_metrics')
            jank_event_res, jank_event_data = get_time(db_list, 'app_jank_event_metrics')   
            self.indicators_intrested = pd.concat([self.indicators_intrested, binder_res, gc_res_process, gc_res, thread_res, athena_res, jank_event_res])
            self.indicators_data = pd.concat([self.indicators_data, binder_data, gc_process_data, gc_data, thread_data, athena_data, jank_event_data])
        
    def run(self):
        self.db_process()
        self.tracing_process()
        self.jank_process()
        self.lt_process()
        return self.indicators_intrested, self.indicators_data

class SampleDataProcessor(DataProcessor):
        
    def tracing_process(self):
        data_range = range(0, self.len, 9)
        tracing_data_list = [pd.read_csv(f'{self.tracing_path}/tracing{str(i)}.csv') for i in data_range]
        for indicator in ['mem_free','mem_available','rss_ms','rss_ss', 'rss_sf', 'rss_ui', 'cache', 'swap_cached', 'mem_locked','mem_shared', 'slab', 'vmalloc_total', 'vmalloc_used', 'kernel_locks']:
            anova_text = ''
            avg_value = {}
            for i, tracing_data in enumerate((tracing_data_list)):
                anova_text += f"tracing_data_list[{i}]['{indicator}'], "
                if indicator not in avg_value.keys():
                    avg_value[indicator] = [tracing_data[f'{indicator}'].mean()]
                else:
                    avg_value[indicator].append(tracing_data[f'{indicator}'].mean())
            f, p = eval(f"f_oneway({anova_text}axis=0)")
            # print(f'ANOVA: F={f}, p={p}') # p<0.05, reject null hypothesis, there is significant difference between groups
            mk_res = mk.original_test(avg_value[indicator])
            if mk_res.trend != 'no trend':
                print(f"Indicator {indicator} Analysis:")
                print(mk_res)
                print('-----------------')
                self.indicators_intrested[indicator] = mk_res.trend
            self.indicators_data[indicator] = avg_value[indicator]
            
        for indicator in ['reads_completed','reads_merged','sectors_read','time_read','writes_completed','writes_merged','sectors_write','time_write','io_time','weighted_io_time','discards_completed','discards_merged','sectors_discard','time_discard',
                                        'user_time','nice_time','iowait_time','steal_time','pgfree','pgpgin','pgpgout','slabs_scanned','pgfault','pgmajfault']:
            anova_text = ''
            avg_value = {}
            avg_gap = {}
            for i, tracing_data in enumerate((tracing_data_list)):
                anova_text += f"tracing_data_list[{i}]['{indicator}'], "
                if indicator not in avg_value.keys():
                    avg_value[indicator] = [tracing_data[f'{indicator}'].mean()]
                else:
                    avg_value[indicator].append(tracing_data[f'{indicator}'].mean())
            avg_gap[indicator] = [avg_value[indicator][i+1]-avg_value[indicator][i] for i in range(len(avg_value[indicator])-1)]
            if not all(gap == 0 for gap in avg_gap[indicator]):
                f, p = eval(f"f_oneway({anova_text}axis=0)")
            # print(f'ANOVA: F={f}, p={p}') # p<0.05, reject null hypothesis, there is significant difference between groups
            mk_res = mk.original_test(avg_gap[indicator])
            if mk_res.trend == 'increasing':
                print(f"Indicator {indicator} Analysis:")
                print(mk_res)
                print('-----------------')
                self.indicators_intrested[indicator] = mk_res.trend
            self.indicators_data[indicator] = avg_gap[indicator]
            
    def jank_process(self):
        if any(name.startswith('jank') for name in os.listdir(self.tracing_path)):
            data_range = range(0, self.len, 9)
            jank = []
            for i in data_range:
                jank_path = self.tracing_path + '/jank' + str(i) + '.csv'
                df_jank = pd.read_csv(jank_path)
                total_jank =(df_jank['janky_frame'][df_jank['app'] == 'com.android.systemui'])
                total_frame = (df_jank['total_frame'][df_jank['app'] == 'com.android.systemui'])
                jank.append(100*float(total_jank.iloc[0]/total_frame.iloc[0]))
            if mk.original_test(jank).trend == 'increasing':
                print(f"Indicator jank Analysis:")
                print(mk.original_test(jank))
                print('-----------------')
                self.indicators_intrested['jank'] = mk.original_test(jank).trend
            self.indicators_data['jank'] = jank
    
    def lt_process(self):
        with open(f'{self.tracing_path}/lt.csv', 'r') as f:
            start = f.read(1)
        if start == '0':    
            df_lt = pd.read_csv(f'{self.tracing_path}/lt.csv')
        else:
            df_lt = pd.read_csv(f'{self.tracing_path}/lt.csv', header=None)
        col_num = df_lt.shape[1]
        print('LT Analysis:', end='')
        for i in range(col_num):
            if not df_lt.iloc[::9, i].isna().any():
                if mk.original_test(df_lt.iloc[::9, i]).trend == 'increasing':
                    print(f'{i}, ', end='')
                    self.indicators_intrested[f'LT_{i}'] = 'increasing' 
                self.indicators_data[f'LT_{i}'] = list(df_lt.iloc[::9, i])
    
    def db_process(self):
        db_list = [f'{self.tracing_path}/db/db{i}.db' for i in range(0, self.len, 9)] 
        if db_list:
            binder_res, binder_data = mk_result(db_list, binder_sql, 2, ['interface_name', 'code_id'])
            gc_res_process, gc_process_data = mk_result(db_list, gc_process_sql, 1, ['process_name'])
            gc_res, gc_data = mk_result(db_list, gc_sql, 1, ['state_name'])
            thread_res, thread_data = mk_result(db_list, thread_sql, 2, ['process_name', 'thread_name'])   
            athena_res, athena_data = get_times(db_list, 'athena_process_clear_metrics')
            jank_event_res, jank_event_data = get_time(db_list, 'app_jank_event_metrics')   
            self.indicators_intrested = pd.concat([self.indicators_intrested, binder_res, gc_res_process, gc_res, thread_res, athena_res, jank_event_res])
            self.indicators_data = pd.concat([self.indicators_data, binder_data, gc_process_data, gc_data, thread_data, athena_data, jank_event_data])
class PreDataProcessor(DataProcessor):
    
    def tracing_process(self):
        tracing_data = pd.read_csv(os.path.join(self.tracing_path, 'tracing.csv'))
        for indicator in ['mem_free','mem_available','rss_ms','rss_ss', 'rss_sf', 'rss_ui', 'cache', 'swap_cached', 'mem_locked','mem_shared', 'slab', 'vmalloc_total', 'vmalloc_used', 'kernel_locks']:
            mk_res = mk.original_test(tracing_data[indicator])
            if mk_res.trend != 'no trend':
                print(f"Indicator {indicator} Analysis:")
                print(mk_res)
                print('-----------------')
                self.indicators_intrested[indicator] = mk_res.trend
            self.indicators_data[indicator] = list(tracing_data[indicator])
            
        for indicator in ['reads_completed','reads_merged','sectors_read','time_read','writes_completed','writes_merged','sectors_write','time_write','io_time','weighted_io_time','discards_completed','discards_merged','sectors_discard','time_discard',
                                        'user_time','nice_time','iowait_time','steal_time','pgfree','pgpgin','pgpgout','slabs_scanned','pgfault','pgmajfault']:
            gap = {}
            gap[indicator] = [tracing_data[indicator][i+1]-tracing_data[indicator][i] for i in range(len(tracing_data[indicator])-1)]
            # print(f'ANOVA: F={f}, p={p}') # p<0.05, reject null hypothesis, there is significant difference between groups
            mk_res = mk.original_test(gap[indicator])
            if mk_res.trend == 'increasing':
                print(f"Indicator {indicator} Analysis:")
                print(mk_res)
                print('-----------------')
                self.indicators_intrested[indicator] = mk_res.trend
            self.indicators_data[indicator] = gap[indicator]
    
    def lt_process(self):
        df_lt = pd.read_csv(os.path.join(self.tracing_path, 'lt.csv'))
        apps = df_lt['app_package'].unique()
        for app in apps:
            try:
                data = df_lt[df_lt['app_package'] == app]['LT']
            except:
                data = df_lt[df_lt['app_package'] == app]['lt']
            self.indicators_data[f'LT_{app}'] = list(data)
            mk_res = mk.original_test(data)
            if mk_res.trend == 'increasing':
                print(f"Indicator {f'LT_{app}'} Analysis:")
                print(mk_res)
                print('-----------------')
                self.indicators_intrested[f'LT_{app}'] = mk_res.trend
                
    def db_process(self):
        db_filenames = list(filter(lambda x: x.endswith('.db'), os.listdir(self.tracing_path)))
        db_list = [os.path.join(self.tracing_path, db_filename) for db_filename in db_filenames] 
        if db_list:
            # binder_res, binder_data = mk_result_devide(db_list, binder_sql, 2, ['interface_name', 'code_id'])
            gc_res_process, gc_process_data = mk_result_divide(db_list, gc_process_sql, 1, ['process_name'])
            gc_res, gc_data = mk_result_divide(db_list, gc_sql, 1, ['state_name'])
            thread_res, thread_data = mk_result_divide(db_list, thread_sql, 2, ['process_name', 'thread_name'])   
            athena_res, athena_data = get_times_divide(db_list, 'athena_process_clear_metrics', slice_num=190)
            jank_event_res, jank_event_data = get_time_divide(db_list, 'app_jank_event_metrics')   
            self.indicators_intrested = pd.concat([self.indicators_intrested, gc_res_process, gc_res, thread_res, athena_res, jank_event_res])
            self.indicators_data = pd.concat([self.indicators_data, gc_process_data, gc_data, thread_data, athena_data, jank_event_data])

from statistics import median
def quartile_range(lst):
    n = len(lst)
    sorted_lst = sorted(lst)
    mid = n // 2
    if n % 2 == 0:
        lower_half = sorted_lst[:mid]
        upper_half = sorted_lst[mid:]
    else:
        lower_half = sorted_lst[:mid]
        upper_half = sorted_lst[mid+1:]
    q1 = median(lower_half)
    q3 = median(upper_half)
    return q3 - q1