import uiautomator2 as u2
import time
import re
import matplotlib.pyplot as plt
import threading
import pandas as pd
import trace
import util
import math

d = u2.connect()
d.watcher.when('安装').click()
d.watcher.when('继续安装').click()
d.watcher.when('完成').click()
d.watcher.when('同意并继续').click()
d.watcher.when("我知道了").click()
d.watcher.when("跳过").click()
d.watcher.when("取消").click()
d.watcher.when("允许").click()
d.watcher.start()

d.shell('setprop debug.choreographer.skipwarning 12') # set jank threshold to 12fps(12/120=0.1s)
t_mute = threading.Thread(target=util.mute_phone,args=(d,),daemon=True)
t_mute.start()
trace_path = 'e:/data/3-8-1app/'
test_app_list = util.xiaobai_apps
stress_app_list = ["com.heytap.browser"]
duration = 21  # hours
t_xiaobai = 1  # minutes
t_stress = 20*60  # minutes

if __name__ == "__main__":
    n = math.ceil(duration*60 / (t_stress + t_xiaobai)) 
    for i in range(n):
        util.uninstall_xiaobai(d)
        util.install_xiaobai(d)
        # trace.jank_reset(d, test_app_list)
        t_start = time.time()
        t_end = t_start + 60 * t_xiaobai
        lt = util.xiaobai_auto(d)
        # df_lt.insert(df_lt.shape[1], '', lt, allow_duplicates = True)
        # print(df_lt)
        while time.time() < t_end:
            time.sleep(1)       
        
        trace.start_ot_trace_manually()
        t_tracing = util.T_tracing(d,10,(t_stress*60))
        t_tracing.start()
        
        t_start = time.time()
        t_end = t_start + 60 * t_stress
        while time.time() < t_end:
            for package_name in stress_app_list:
                lt, t, app_name = util.test_app(d, 0.5, package_name)
                pd.DataFrame([{'t':t, 'app_name':app_name, 'lt':lt}]).to_csv(f'{trace_path}lt.csv', mode='a',index=False, header=False)
                if time.time() > t_end: break
                
        trace.stop_ot_trace_manually(trace_path,f'otrace{i}/')       
        try:
            # df_jank = trace.jank_collection(d, test_app_list)
            df_tracing = t_tracing.get_result()
            df_tracing.to_csv(f'{trace_path}tracing{i}.csv',sep=',',index=False,header=True)
            # df_jank.to_csv(f'{trace_path}jank{i}.csv',sep=',',index=False,header=True)
        except Exception as e:
            print(str(e))
                
    # df_lt.transpose().to_csv(f'{trace_path}lt.csv',sep=',',index=False,header=True)            
    
