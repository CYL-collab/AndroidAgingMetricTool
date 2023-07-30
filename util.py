import re
import time
import threading
import trace
import yaml

app_list_10 = ["com.heytap.browser",#oplus浏览器
                "com.tencent.qqmusic",#QQ音乐
                "com.oplus.camera",
                "com.tencent.news",#腾讯新闻
                "com.UCMobile",#UC浏览器
                "com.autonavi.minimap",#高德地图
                "com.ximalaya.ting.android",#喜马拉雅
                "com.gotokeep.keep",#keep
                "com.hunantv.imgo.activity",#芒果TV
                "com.meitu.meiyancamera",#美颜相机
                ]
app_list_10_2 = [
                 "me.ele",#饿了么
                 "com.wuba",#五八同城
                 "ctrip.android.view",#携程旅行
                 "com.smile.gifmaker",#快手
                 "com.tencent.weishi",#腾讯微视
                 "com.ss.android.article.news",#今日头条
                 "com.ss.android.article.video",#西瓜视频
                 "com.tencent.mtt",#QQ浏览器
                 "com.achievo.vipshop",#唯品会
                 "com.qiyi.video",#爱奇艺
                ]
app_list_10_3 = [
                "com.happyelements.AndroidAnimal",#开心消消乐
                 "com.kugou.android",#酷狗音乐
                 "com.gotokeep.keep",#keep
                 "com.hunantv.imgo.activity",#芒果TV
                 "com.meitu.meiyancamera",#美颜相机
                 "com.shizhuang.duapp",#得物
                 "com.dragon.read",#番茄小说
                 "com.xs.fm",#番茄畅听
                 "cn.missevan",#猫耳FM
                 "com.xingin.xhs",#小红书
                ]
app_list_30 = ["com.heytap.browser",#oplus浏览器
                "com.tencent.qqmusic",#QQ音乐
                "com.oplus.camera",
                "com.tencent.news",#腾讯新闻
                "com.UCMobile",#UC浏览器
                "com.autonavi.minimap",#高德地图
                "com.ximalaya.ting.android",#喜马拉雅
                "com.gotokeep.keep",#keep
                "com.hunantv.imgo.activity",#芒果TV
                "com.meitu.meiyancamera",#美颜相机
                "me.ele",#饿了么
                "com.wuba",#五八同城
                "ctrip.android.view",#携程旅行
                 "com.smile.gifmaker",#快手
                 "com.tencent.weishi",#腾讯微视
                 "com.ss.android.article.news",#今日头条
                 "com.ss.android.article.video",#西瓜视频
                 "com.tencent.mtt",#QQ浏览器
                 "com.achievo.vipshop",#唯品会
                 "com.qiyi.video",#爱奇艺
                 "com.happyelements.AndroidAnimal",#开心消消乐
                 "com.kugou.android",#酷狗音乐
                 "com.gotokeep.keep",#keep
                 "com.hunantv.imgo.activity",#芒果TV
                 "com.meitu.meiyancamera",#美颜相机
                 "com.shizhuang.duapp",#得物
                 "com.dragon.read",#番茄小说
                 "com.xs.fm",#番茄畅听
                 "cn.missevan",#猫耳FM
                 "com.xingin.xhs",#小红书
                ]
xiaobai_apps = [
                'com.tencent.mm',
                'com.tencent.mobileqq',
                'com.sina.weibo',
                'com.eg.android.AlipayGphone',
                'com.taobao.taobao',
                'com.jingdong.app.mall',
                'com.sankuai.meituan',
                'com.upin.app',
                'com.baidu.BaiduMap',
                'com.Qunar',
                'com.baidu.searchbox',
                'com.MobileTicket',
                'com.youku.phone',
                'com.netease.cloudmusic',
                'com.zhihu.android',
                'com.alibaba.android.rimet',
                'com.ss.android.ugc.aweme',
                'tv.danmaku.bili',
                'com.tencent.tmgp.sgame',
                'com.tencent.tmgp.pubgmhd'
                ]

pattern_d = re.compile(r'\d+')
pattern_pkg = re.compile(r'package:.*')

def load_config(file_path):
    with open(file_path, 'rb') as f:
        config = yaml.safe_load(f)
    return config

def begin_watcher(d):
    d.watcher.when('安装').click()
    d.watcher.when('继续安装').click()
    d.watcher.when('完成').click()
    d.watcher.when('同意并继续').click()
    d.watcher.when("我知道了").click()
    d.watcher.when("跳过").click()
    d.watcher.when("取消").click()
    d.watcher.when("允许").click()
    d.watcher.start()

def install_xiaobai(d):
    if d.shell("test -d /data/local/tmp/ap && echo 'exist' || echo 'does not exist'").output == 'does not exist':
        d.push('apk/xiaobai', '/data/local/tmp/apk')
    for app in xiaobai_apps:
        d.shell("pm install /data/local/tmp/apk/{}.apk".format(app))

def uninstall_xiaobai(d):
    for app in xiaobai_apps:
        d.shell("pm uninstall {}".format(app))

def fill_mem(d, app_quantity):
    pkgs = d.shell("pm list package -3").output
    pkg_list = pattern_pkg.findall(pkgs)
    for pkg in pkg_list[0:app_quantity]:
        pkg = pkg[8:]
        try:
            d.app_start(pkg)
            print('{} started!'.format(pkg))
        except:
            pass
            print('{} start failed!'.format(pkg))
        time.sleep(0.5)
        
def mute_phone(d):
    while True:
        try:
            d.shell('cmd media_session volume --stream 3 --set 0')
            time.sleep(0.3)
        except:
            pass

def test_app(d, last_time, package_name, monkey_interval):
    t_end = time.time() + 60 * last_time
    main_activity = d.app_info(package_name)['mainActivity']
    lt_text = d.shell(f"am start -W -S -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n {package_name}/{main_activity} | grep TotalTime").output
    try:
        t = time.time()
        app_name = package_name
        lt = float(pattern_d.search(lt_text).group())
    except:
        print('{} lt collect failed at {}'.format(package_name,time.time()))
        lt = None
    while time.time() < t_end:
        d.shell("monkey -p {} --throttle {} -s 42\
        --pct-majornav 0  --pct-syskeys 0 --pct-anyevent 0\
        100".format(package_name, monkey_interval))
    return lt, t, app_name


def monkey_watcher(d, activity_name):
    while True:
        try:
            current_activity = d.shell('dumpsys window | grep mCurrentFocus').output
            current_activity = re.search(r' \S*}', current_activity).group()[1:-1]
        except:
            current_activity = None
        if current_activity != activity_name:
            d.shell('am start {}'.format(activity_name))
        time.sleep(5)
        global stop_thread
        if stop_thread: break

class T_tracing(threading.Thread):
    def __init__(self, d, interval, duration):
        threading.Thread.__init__(self)
        self.d = d
        self.interval = interval
        self.duration = duration

    def run(self):
        self.result = trace.tracing_script(self.d, self.interval, self.duration)

    def get_result(self):
        threading.Thread.join(self)
        return self.result
    
def xiaobai_auto(d): 
    lt = []
    t_start = time.time()
    for _ in range(2):
        for package_name in xiaobai_apps:
            lt_text = d.shell(f"am start -W -a android.intent.action.MAIN -c android.intent.category.LAUNCHER {package_name}/{d.app_info(package_name)['mainActivity']} | grep WaitTime").output
            try:
                print(f'{package_name}:{float(pattern_d.search(lt_text).group())}')
                lt.append(float(pattern_d.search(lt_text).group()))
            except:
                print('{} lt collect failed at {}'.format(package_name,time.time()))
            time.sleep(0.5)
            # d.press('home')
            # time.sleep(0.5)
    t_xiaobai = time.time() - t_start
    lt.append(t_xiaobai)
    return lt


