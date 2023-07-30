import uiautomator2 as u2
import time
import threading
import pandas as pd
import trace
import util
import math


if __name__ == "__main__":
    # Load config
    config = util.load_config('config.yaml')
    trace_path = config['base']['trace_path']
    test_app_list = config['base']['stress_app_list']
    monkey_interval = config['base']['monkey_interval']
    stress_time_per_app = config['base']['stress_time_per_app']
    trace_interval = config['base']['trace_interval']
    duration = config['run_stress']['duration']  # hours
    interval = config['run_stress']['sample_interval']  # rounds

    d = u2.connect(addr=config['base']['serial'])
    util.begin_watcher(d)
    d.shell('setprop debug.choreographer.skipwarning {}'.format(config['base']['jank_threshold'])) # set jank threshold 
    t_mute = threading.Thread(target=util.mute_phone,args=(d,),daemon=True)
    t_mute.start()
    i = 0
    t_start = time.time()
    t_end = t_start + 3600 * duration
    while time.time() < t_end:
        if i % interval == 0:
            tracing_enaled = True
        else:
            tracing_enaled = False 
        if tracing_enaled:
            trace.jank_reset(d, test_app_list)
            t_tracing = util.T_tracing(d,trace_interval,(60*stress_time_per_app*len(test_app_list)))
            trace.start_ot_trace_manually(d)
            t_tracing.start()
        
        lt_list = []
        # app_list = []
        for package_name in test_app_list:
            lt, t, app_name = util.test_app(d, stress_time_per_app, package_name, monkey_interval)
            lt_list.append(lt)
            # app_list.append(app_name)
            
        if tracing_enaled:
            trace.stop_ot_trace_manually(d,trace_path,f'otrace{i // interval}/')
            try:
                df_jank = trace.jank_collection(d, test_app_list)
                pd.DataFrame(lt_list).transpose().to_csv(f'{trace_path}/lt.csv', mode='a', index=False, header=False)
                df_tracing = t_tracing.get_result()
                df_tracing.to_csv(f'{trace_path}/tracing{i // interval}.csv',sep=',',index=False,header=True)
                df_jank.to_csv(f'{trace_path}/jank{i // interval}.csv',sep=',',index=False,header=True)
            except Exception as e:
                print(str(e))
        i += 1
                
    # df_lt.transpose().to_csv(f'{trace_path}lt.csv',sep=',',index=False,header=True)            
    
