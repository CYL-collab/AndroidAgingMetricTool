import re
import os
import time
import subprocess
import pandas as pd
import threading
import platform

host_system = platform.system()

# subprocess.run(["cat","d:/Android/config_test.pbtx","|","adb","shell","perfetto","-c","-","--txt","-o",Ptrace_remote_path])
def start_perfetto_trace(config_path, remote_path, local_path):
    '''
    will block in adb shell perfetto, you have to open another thread outside the running script.
    '''
    subprocess.run("adb shell rm -rf /data/misc/perfetto-traces")
    if host_system == 'Windows':
        subprocess.run("type {} | adb shell perfetto -c - --txt -o {}".format(config_path,remote_path),shell=True)
    else:
        subprocess.run("cat {} | adb shell perfetto -c - --txt -o {}".format(config_path,remote_path),shell=True)
    subprocess.run('adb pull {} {}'.format(remote_path,local_path))


def multi_perfetto_trace(num, config_path, remote_path, local_path):
    '''
    It will block in adb shell perfetto, path need to leave the format number position.
    Each perfetto-trace should be controlled at about 3GB, otherwise TraceProcessor cannot read it properly.
    '''
    subprocess.run("adb shell rm -rf /data/misc/perfetto-traces")
    for i in range(num):
        remote = remote_path.format(i+1)
        local = local_path.format(i+1)
        if host_system == 'Windows':
            subprocess.run("type {} | adb shell perfetto -c - --txt -o {}".format(config_path,remote),shell=True)
        else:
            subprocess.run("cat {} | adb shell perfetto -c - --txt -o {}".format(config_path,remote),shell=True)
        pwd_pull = 'adb pull {} {}'.format(remote,local)
        pwd_rm = 'adb shell rm {}'.format(remote_path.format(i))
        t_pull = threading.Thread(target=subprocess.run,args=(pwd_pull,))
        t_rm = threading.Thread(target=subprocess.run,args=(pwd_rm,))
        t_pull.start()
        if i > 0:
            t_rm.start()
        

def check_ot_state(d):
    output = d.shell('dumpsys activity service StatsManagerService perf --state').output
    # subprocess.run('adb shell dumpsys activity service StatsManagerService perf --state')
    # output = subprocess.check_output('adb shell dumpsys activity service StatsManagerService perf --state',shell=True)
    # out = output.decode()
    if output.find('false') >= 0:
        return False
    else:
        return True

 
def start_ot_trace_manually(d):
    '''
    Start OneTrace, non-blocking
    '''
    if check_ot_state(d):
        print('OneTrace is already running.')
        d.shell('dumpsys activity service StatsManagerService perf --force_stop')
        d.shell('am force-stop com.oplus.onetrace')
        time.sleep(0.5)
    
    d.shell('dumpsys activity service OTraceDaemonService systrace --start')
    d.shell('rm -rf /storage/emulated/0/Android/data/com.oplus.onetrace/files/Documents')
    d.shell('dumpsys activity service StatsManagerService perf -D')
    d.shell('dumpsys activity service StatsManagerService file -D')
    d.shell('dumpsys activity service OTraceDaemonService -D')
    d.shell('dumpsys activity service StatsManagerService perf --start')
    
    
def stop_ot_trace_manually(d, path, folder_name):
    '''
    Stop OneTrace, non-blocking
    '''
    # os.system('start .\\bat\\Onetrace_Stop_Tracing.bat')
    d.shell("dumpsys activity service StatsManagerService perf --force_stop")
    time.sleep(5)
    d.shell("dumpsys activity service OTraceDaemonService -la")
    d.shell("dumpsys activity service OTraceDaemonService -o")
    d.shell("dumpsys activity service StatsManagerService file -o")
    time.sleep(5)
    if not os.path.exists(path):
        os.makedirs(path)
        print(f'文件夹 {path} 不存在，已创建成功！')
    subprocess.run(f"adb -s {d.serial} pull /storage/emulated/0/Android/data/com.oplus.onetrace/files/Documents/OTRTA/manually_traces/ {path}", shell=True)
    os.rename(f'{path}manually_traces',f'{path}{folder_name}')

    
def tracing_script(d, interval, duration):
    '''
    Manual collection scripts that block
    '''
    df = pd.DataFrame(columns=['ts','rss_ss','rss_sf','rss_ui','rss_ms',
                                'mem_free','mem_available','cache','swap_cached','mem_locked','mem_shared','slab','vmalloc_total','vmalloc_used',
                                'reads_completed','reads_merged','sectors_read','time_read','writes_completed','writes_merged','sectors_write','time_write','io_time','weighted_io_time','discards_completed','discards_merged','sectors_discard','time_discard',
                                'user_time','nice_time','iowait_time','steal_time',
                                'pgfree','pgpgin','pgpgout','slabs_scanned','pgfault','pgmajfault','avg_load','kernel_locks' ,'voltage','temp'   
                                ])
    pattern_d = re.compile(r'\d+')
    t_end = time.time() + duration
    while time.time() < t_end:
        t_begin = time.time()
        try:
            proc_text = d.shell("procrank").output
            # pid_ss = pattern_d.findall(re.search(r'\n.+system_server\n', proc_text).group())[0]
            rss_ss = float(pattern_d.findall(re.search(r'\n.+system_server\n', proc_text).group())[2])
            rss_sf = float(pattern_d.findall(re.search(r'\n.+/system/bin/surfaceflinger\n', proc_text).group())[2])
            rss_ui = float(pattern_d.findall(re.search(r'\n.+com.android.systemui\n', proc_text).group())[2])
            rss_ms = float(pattern_d.findall(re.search(r'\n.+/system/bin/mediaserver\n', proc_text).group())[2])

            mem_text = d.shell("cat /proc/meminfo").output
            mem_free = float(pattern_d.search(re.search(r'MemFree:.+\n', mem_text).group()).group())
            mem_available = float(pattern_d.search(re.search(r'MemAvailable:.+\n', mem_text).group()).group())
            cache = float(pattern_d.search(re.search(r'Cached:.+\n', mem_text).group()).group())
            swap_cached = float(pattern_d.search(re.search(r'SwapCached:.+\n', mem_text).group()).group())
            mem_locked = float(pattern_d.search(re.search(r'Mlocked:.+\n', mem_text).group()).group())
            mem_shared = float(pattern_d.search(re.search(r'Shmem:.+\n', mem_text).group()).group())
            slab = float(pattern_d.search(re.search(r'Slab:.+\n', mem_text).group()).group())
            vmalloc_total = float(pattern_d.search(re.search(r'VmallocTotal:.+\n', mem_text).group()).group())
            vmalloc_used = float(pattern_d.search(re.search(r'VmallocUsed:.+\n', mem_text).group()).group())
            
            io_text = pattern_d.findall(d.shell("cat /proc/diskstats | grep 'sde [0-9]'").output)
            reads_completed = float(io_text[2])
            reads_merged = float(io_text[3])
            sectors_read = float(io_text[4])
            time_read = float(io_text[5])
            writes_completed = float(io_text[6])
            writes_merged = float(io_text[7])
            sectors_write = float(io_text[8])
            time_write = float(io_text[9])
            io_time = float(io_text[11])
            weighted_io_time = float(io_text[12])
            discards_completed = float(io_text[13])
            discards_merged = float(io_text[14])
            sectors_discard = float(io_text[15])
            time_discard = float(io_text[16])
            
            cpu_text = pattern_d.findall(d.shell("cat /proc/stat | grep 'cpu '").output)
            user_time = cpu_text[0] # normal processes executing in user mode
            nice_time = cpu_text[1] # niced processes executing in user mode
            iowait_time = cpu_text[4] # waiting for I/O to complete
            steal_time = cpu_text[7] # involuntary wait
            
            vm_text = d.shell('cat /proc/vmstat').output
            pgfree = float(pattern_d.search(re.search(r'pgfree .+\n', vm_text).group()).group())
            pgpgin = float(pattern_d.search(re.search(r'pgpgin .+\n', vm_text).group()).group()) 
            pgpgout = float(pattern_d.search(re.search(r'pgpgout .+\n', vm_text).group()).group()) 
            slabs_scanned = float(pattern_d.search(re.search(r'slabs_scanned .+\n', vm_text).group()).group()) 
            pgfault = float(pattern_d.search(re.search(r'pgfault .+\n', vm_text).group()).group())
            pgmajfault = float(pattern_d.search(re.search(r'pgmajfault .+\n', vm_text).group()).group())
            
            # load by process/core
            avg_load = re.findall(r'\d+\.\d*',d.shell("cat /proc/loadavg").output)[0]
            
            kernel_locks = int(pattern_d.findall(d.shell("wc -l /proc/locks").output)[0])
            
            battery_text = d.shell("dumpsys battery").output
            voltage = float(pattern_d.search(re.search(r'\n  voltage:.+\n', battery_text).group()).group())
            temp = float(pattern_d.search(re.search(r'PhoneTemp:.+\n', battery_text).group()).group())
            
            ts = time.time()
            df.loc[len(df.index)] = [ts,rss_ss,rss_sf,rss_ui,rss_ms,
                                    mem_free,mem_available,cache,swap_cached,mem_locked,mem_shared,slab,vmalloc_total,vmalloc_used,
                                    reads_completed,reads_merged,sectors_read,time_read,writes_completed,writes_merged,sectors_write,time_write,io_time,weighted_io_time,discards_completed,discards_merged,sectors_discard,time_discard,
                                    user_time,nice_time,iowait_time,steal_time,
                                    pgfree,pgpgin,pgpgout,slabs_scanned,pgfault,pgmajfault,avg_load,kernel_locks,voltage,temp  
                                    ]
        except:
            print('Trace collection failed in {}'.format(time.time()))
        while time.time() < t_begin + interval:
            time.sleep(0.1)
    return df
    

def jank_reset(d, app_list):
    for app in (app_list + ['com.android.systemui','com.android.launcher']):
        d.shell('dumpsys gfxinfo {} reset'.format(app))


def jank_collection(d, app_list):
    df = pd.DataFrame(columns=['app', 'total_frame', 'janky_frame'])
    for app in (app_list + ['com.android.systemui','com.android.launcher']):
        text = d.shell(f"dumpsys gfxinfo {app} | egrep 'Janky frames|Total frames rendered'").output
        try:
            total_frame, janky_frame = list(map(int, re.findall(r'\d+', text)[0:2]))
            df.loc[len(df.index)] = [app, total_frame, janky_frame]
        except:
            pass
    return df
 

# Ptrace_remote_path = "/data/misc/perfetto-traces/trace60APP.perfetto-trace"
# Ptrace_local_path = "data/perfetto-traces/trace60APP.perfetto-trace"
# start_perfetto_trace('config.pbtx',Ptrace_remote_path,Ptrace_local_path)