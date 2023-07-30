# -*- coding: utf-8 -*-
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
    test_app_list = config['base']['test_app_list']
    stress_app_list = config['base']['stress_app_list']
    duration = config['run_t&s']['duration']  # hours
    t_xiaobai = config['run_t&s']['t_xiaobai']  # minutes
    t_stress = config['run_t&s']['t_stress']  # minutes
    monkey_interval = config['base']['monkey_interval']
    stress_time_per_app = config['base']['stress_time_per_app']
    trace_interval = config['base']['trace_interval']

    # Start test
    d = u2.connect(addr=config['base']['serial'])
    util.begin_watcher(d)
    d.shell('setprop debug.choreographer.skipwarning {}'.format(config['base']['jank_threshold'])) # set jank threshold 
    t_mute = threading.Thread(target=util.mute_phone,args=(d,),daemon=True)
    t_mute.start() # Keep the phone mute
    
    n = math.ceil(duration*60 / (t_stress + t_xiaobai))
    for i in range(n):
        util.uninstall_xiaobai(d)
        util.install_xiaobai(d)
        trace.jank_reset(d, test_app_list)
        t_tracing = util.T_tracing(d,trace_interval,(60*t_xiaobai))
        trace.start_ot_trace_manually(d)
        t_tracing.start()
        t_start = time.time()
        t_end = t_start + 60 * t_xiaobai
        lt = util.xiaobai_auto(d)

        while time.time() < t_end:
            time.sleep(1)       
        trace.stop_ot_trace_manually(d, trace_path, f'otrace{i}/')
        
        try:
            df_jank = trace.jank_collection(d, test_app_list)
            pd.DataFrame(lt).transpose().to_csv(f'{trace_path}/lt.csv', mode='a', index=False, header=False)
            df_tracing = t_tracing.get_result()
            df_tracing.to_csv(f'{trace_path}/tracing{i}.csv',sep=',',index=False,header=True)
            df_jank.to_csv(f'{trace_path}/jank{i}.csv',sep=',',index=False,header=True)
        except Exception as e:
            print(str(e))
        
        t_start = time.time()
        t_end = t_start + 60 * t_stress
        while time.time() < t_end:
            for package_name in stress_app_list:
                util.test_app(d, stress_time_per_app, package_name, monkey_interval)
                if time.time() > t_end: break       
    
