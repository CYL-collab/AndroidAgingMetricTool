import matplotlib.pyplot as plt
import pandas as pd
import pickle
import pymannkendall as mk
from data_util import plot_with_trend

# Mapping: number of occurrences of indicators
def trend_occur(exp_list_1, exp_list_2, exp_list_3, indicators_intrested):
    labels = indicators_intrested[indicators_intrested['count_incre'] >= 4].index.tolist()
    data = []
    for exp_list in [exp_list_1, exp_list_2, exp_list_3]:
        data.append([indicators_intrested[exp_list].loc[label].value_counts()['increasing'] if not indicators_intrested[exp_list].loc[label].value_counts().empty else 0 for label in labels])
    width = 0.5
    fig, ax = plt.subplots()
    ax.barh(labels, data[0], width, label='EXP3.1')
    ax.barh(labels, data[1], width, left = data[0], label='EXP3.2')
    ax.barh(labels, data[2], width, left = [x + y for x, y in zip(data[0], data[1])], label='EXP3.3')
    ax.legend()
    ax.set_xlabel('Number of Trend Occurrences')

# Plotting: indicator values and fitting linear trends    
def draw_plot(indicators_data, indicator, exp_list):
    for i, exp in enumerate(exp_list):
        data = indicators_data[exp][indicator]
        from math import sqrt, ceil
        plt.subplot(ceil(sqrt(len(exp_list))), ceil(sqrt(len(exp_list))), i+1)
        plot_with_trend(data, s=4)
        plt.xlabel('Rounds')
        plt.ylabel(indicator)

# Filtering of specified indicators based on trend analysis results
# sys_indicators = []
# user_indicators = []

# correlation analysis
def corr_to_sys(indicators_data, sys_indicators, user_indicator):
    corr = pd.DataFrame(index=sys_indicators, columns=indicators_data.columns)
    for exp_name, exp_data in indicators_data.items():
        for indicator in sys_indicators:
            if type(exp_data[user_indicator]) is float or type(exp_data[indicator]) is float:
                continue
            n = min(len(exp_data[user_indicator]), len(exp_data[indicator]))
            from scipy.stats import spearmanr
            corr.loc[indicator, exp_name] = spearmanr(exp_data[user_indicator][:n], exp_data[indicator][:n]).correlation
    corr['spearman corr'] = corr.mean(axis=1)
    corr.sort_values(by='spearman corr', ascending=False, inplace=True)
    return corr['spearman corr']

def corr_analysis(indicators_data, sys_indicators, user_indicators):
    res = pd.concat([corr_to_sys(indicators_data, sys_indicators, indicator) for indicator in user_indicators], axis=1)
    res.columns = user_indicators
    res['avg'] = res.mean(axis=1)
    res.sort_values(by='avg', ascending=False, inplace=True)
    return res

indicators_selected = []
indicators_confidence = {}

# threshold analysis
def threshold_each_exp(exp_list, indicators_data, indicators_selected, target_indicator, target_value):
    '''Analyze the correlation between the indicator values near the target indicator value and the target indicator value in each experiment, in order to get the other indicator values corresponding to the target indicator value'''
    closest = lambda lst, target: min(enumerate(lst), key=lambda i: abs(i[1] - target))
    threshold = {}
    for exp in exp_list:
        lst = indicators_data[exp][target_indicator]
        target_round = closest(lst, target_value)[0]
        # plt.figure(figsize = (30, 25))
        result = {}
        for indicator in indicators_selected:
            # target_round = [i for i, value in enumerate(lst) if abs(value-target_value)<0.5][0]
            A = pd.Series(indicators_data[exp][target_indicator])
            B = pd.Series(indicators_data[exp][indicator])
            df = pd.DataFrame({'A': A, 'B': B})
            for i in range(-2, 3):
                df[str(i)] = B.shift(i)
            df.dropna(inplace=True)
            # plt.subplot(4, 5, indicators_selected.index(indicator)+1)
            # plt.bar(range(-2, 3), df.corr().iloc[0][2:].values, width=0.5)
            # plt.title(indicator)
            # plt.xlabel('offset')
            # plt.ylabel('Correlation') 
            offset = int(df.corr().iloc[0][2:].idxmax())
            if target_round+offset >= len(B)-1:
                dest_round = len(B)-1
            elif target_round+offset < 0:
                dest_round = 0
            else:
                dest_round = target_round+offset
            result[indicator] = B[dest_round]
        threshold[exp] = result
    threshold_by_exp = pd.DataFrame()
    for indicator in indicators_selected:
        threshold_by_exp[indicator] = [d[indicator] for d in threshold.values() if indicator in d]
    return threshold_by_exp   

# 丢弃过于分散的指标
def threshold_filt(indicators_data, indicators_selected, threshold_by_exp):
    from data_util import quartile_range
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    th_scaled = pd.DataFrame(scaler.fit_transform(threshold_by_exp), columns=threshold_by_exp.columns)
    iqr_scaled = pd.Series(th_scaled.apply(quartile_range), name='quar').sort_values(ascending=True)
    print(iqr_scaled)
    mean_th = threshold_by_exp.mean()
    indicators_selected = iqr_scaled[iqr_scaled < 0.6].index.tolist()
    threshold = {}
    for indicator in indicators_selected:
        min_num = float('inf')
        for _, data in indicators_data.loc[indicator].items():
            if type(data) is not float:
                if min(data) < min_num:
                    min_num = min(data)
        threshold[indicator] = (min_num, mean_th[indicator])
    return threshold
    
def get_aging_level(x, threshold, indicators_selected, indicators_confidence):
    level = lambda x, indicator: (x-threshold[indicator][0])/(threshold[indicator][1]-threshold[indicator][0]) 
    high = [0.8*level(x[indicator], indicator) for indicator in indicators_selected if indicators_confidence[indicator] == 'high']
    mid = [0.5*level(x[indicator], indicator) for indicator in indicators_selected if indicators_confidence[indicator] == 'mid']
    low = [0.2*level(x[indicator], indicator) for indicator in indicators_selected if indicators_confidence[indicator] == 'low']
    return (sum(high)+sum(mid)+sum(low))/(0.8*len(high)+0.5*len(mid)+0.2*len(low))

def draw_aging_level(indicators_data, indicators_selected, indicators_confidence, exp_list, threshold, window=5, alarm_threshold=0.75, alert_threshold=1.0, aged_threshold=1.5):
    aging_level_data = {}
    for exp_name, exp_data in indicators_data.items():
        data_points = []
        for i in range(exp_data.apply(lambda x:1000000 if type(x) is float else len(x)).min()):
            data_point = {}
            for indicator, value in exp_data.dropna().items(): 
                data_point[indicator] = value[i]
            data_points.append(data_point)
        # print(data_points)
        from math import sqrt, ceil
        plt.subplot(ceil(sqrt(len(exp_list))),ceil(sqrt(len(exp_list))),exp_list.index(exp_name)+1)
        data = [get_aging_level(data_point, threshold, indicators_selected, indicators_confidence) for data_point in data_points]
        aging_alert(data, window, alarm_threshold, alert_threshold, aged_threshold)
        aging_level_data[exp_name] = data
        plt.plot(data, label='Aging Level')
        plt.xlabel('Rounds')
        plt.ylabel('Aging Level')
        plt.ylim([0.4, 2])
        plt.axhline(y=0.75, color='gray', linestyle='--')
        plt.axhline(y=1, color='red', linestyle=':')
    return aging_level_data
        
def aging_alert(data, window=5, alarm_threshold=0.75, alert_threshold=1.0, aged_threshold=1.5):
    alarm_count = 0
    alert_count = 0
    alarm_enabled = False
    alert_enabled = False
    for i, value in enumerate(data):
        if i < window // 2:
            continue
        if not alarm_enabled:
            if all(j >= alarm_threshold for j in data[(i-window//2):(i+window//2+1)]):
                alarm_count += 1
                if alarm_count == 3:
                    plt.plot(i, value, 'ro')
                    plt.annotate('Aging Alarm', xy=(i, value), xytext=(i - 2, value))
                    alarm_enabled = True
            else:
                alarm_count = 0
        if not alert_enabled:
            if all(j >= alert_threshold for j in data[(i-window//2):(i+window//2+1)]):
                alert_count += 1
                if alert_count == 3:
                    plt.plot(i, value, 'ro')
                    plt.annotate('Aging Alert', xy=(i, value), xytext=(i - 2, value))
                    alert_enabled = True
                    mk_res = mk.original_test(data[:i])
                    import numpy as np
                    y = np.linspace(data[0], aged_threshold, 10)
                    x = (y - mk_res.intercept) / mk_res.slope
                    x = np.array([j for j in x if j >= 0])
                    y = x * mk_res.slope + mk_res.intercept
                    plt.annotate('({:.2f},{:.2f})'.format(x[-1], y[-1]), xy=(x[-1], y[-1]), xytext=(x[-1] - 2.2, y[-1] - 0.15))
                    plt.plot(x[-1], y[-1], 'o', linestyle='dashed')
                    plt.plot(x, y)
            else:
                alert_count = 0