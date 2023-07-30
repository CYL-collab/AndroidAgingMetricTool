# Software Aging Metrics Analysis Tools

<p align="left">
<img alt="Release" 
src="https://img.shields.io/badge/Release-v0.1-red?style=flat-square"/></a>
<img alt="Platform" src="https://img.shields.io/badge/Platform-Windows | Linux-lightgrey?style=flat-square"/>
<img alt="Language" src="https://img.shields.io/badge/Python-3.8-yellow?style=flat-square"/>
</p>

> Warning: You may need an OPLUS phone to enable OneTrace collection.

Built on Python 3.8, the tool simulates and tests software aging on cell phones using the [``uiautomator2``](https://pypi.org/project/uiautomator2/) library, collects metrics based on the ``OneTrace`` tool and the ``adb shell`` command, and supports rapid analysis and diagnosis of aging metrics based on [``scipy``](https://pypi.org/project/uiautomator2/) and [``pymannkendall``](https://pypi.org/project/uiautomator2/). It collects metrics data based on the ``OneTrace`` tool and the ``adb shell`` command, and supports fast analysis and diagnosis of aging metrics based on the [``scipy`'](https://pypi.org/project/scipy/) and [``pymannkendall`'](https://pypi.org/project/pymannkendall/) libraries. The tool has been tested to function correctly on both Windows and Linux (MacOS is also theoretically supported).

## Environment configuration

### Python environment

   - Install Python and its environment management tools. We recommend using [``miniconda``](https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/), but you can also use ``venv`` if you prefer, or create a standalone environment in docker.

   - Create a virtual environment based on Python 3.8. For example, in ``conda``, you can create a virtual environment based on Python 3.8 via the

     `````shell
     conda create --name aging_test python=3.8
     `````

     to create a Python 3.8 environment named aging_test.

   - Enter that environment and install the required third-party libraries. In conda, you need to first activate the new environment you just created:

     `````shell
     conda activate aging_test
     `````

     Go to the project directory:
     
     `````shell
     cd [path_to_AndroidAgingTest]
     `````
     
     and install the required pypi packages from ``requirement.txt``:

     `````shell
     pip install --requirement requirements.txt
     `````

### ADB

The Android Debug Bridge (``adb``) is a versatile command-line tool that allows a computer to communicate with a cell phone and run a series of ``shell`` commands. You can get the ``adb`` tool by downloading [SDK Platform-Tools](https://developer.android.google.cn/studio/releases/platform-tools?hl=zh-cn) from Google, and it is recommended that you install We recommend installing version 34.0 and above. After installation, make sure ``adb`` is in the system environment variable. 

### FreakingAwesome-CLI (optional)

This project requires ``FreakingAwesome-CLI`` to convert the captured ``.frk`` files to database for further analysis.



## Run the experiment

### Initialize the device

- Make sure the device is ROOTed and the test app is installed.
- Reboot the phone.
- Make sure the device is connected to the computer via ``adb``, i.e. the device can be queried via ``adb devices``.

### Parameter Configuration

 The parameters required for the experiment are adjustable in ``config.yaml`` in the project directory, including:

The parameters required for the experiment can be adjusted in ``config.yaml`` in the project directory, including:

- ``app_list``: the list of APP packages to be used for testing; to modify the APP list, append it in the following format:

  `````yaml
  example_app_list: &example_app_list
      - com.example.app1
      - com.example.app2
      - ...
  `````

  And reference the above list as ``*example_app_list`` in ``test_app_list`` or ``stress_app_list``.

- ``base``: base parameters for the experiment run

  - ``serial``: specifies the serial number of the selected device, which can be determined from the value in the first column of ``adb devices``.
  - ``working_path``: absolute path to the project.
  - ``trace_path``: Path where the aging metrics data collected by the experiment will be placed.
  - ``test_app_list``: list of APPs launched sequentially in a short test sequence
  - ``stress_app_list``: list of APPs that cycle through aging operations during stress tests
  - ``stress_time_per_app``: the time interval (in minutes) between runs of each app in a stress test round
  - ``trace_interval``: interval (in seconds) between two adjacent runs of the tracing script to collect metrics
  - ``monkey_interval``: Interval (in milliseconds) between each Monkey event generation in a stress test
  - ``jank_threshold``: Sets OneTrace's threshold for determining jank events (in frames)

- ``run_t&s``: experimental parameters for combining stress tests and short fixed sequences

  - ``duration``: overall duration of the experiment (in hours)
  - ``t_xiaobai``: duration (in minutes) of each fixed test sequence monitoring round
  - ``t_stress``: duration of each stress test round (in minutes)

- ``run_stress``: pure stress test experiment parameters

  - ``duration``: overall duration of the experiment in hours
  - ``sample_interval``: interval between two adjacent samples

### Run the experiment

Make sure your phone is unlocked and on the desktop, and run ``run_t&s.py`` using your previously configured Python interpreter, depending on the type of experiment desired:

`````shell
python run_t&s.py
`````
or ``run_stress.py``:

`````shell
python run_stress.py
`````

> On first run, uiautomator2 may install some dependencies on your phone.

If it runs properly, you will be able to observe in:

- Fixed/random sequence runs on the phone, depending on the experimental parameters set.

  > Tips: You may need to adjust the power plan during the run to ensure that the computer does not go to hibernation/sleep during the experiment. You can also use [PowerToys Awake](https://learn.microsoft.com/windows/powertoys/awake) on the Windows side to quickly adjust the hibernation strategy without changing the power plan.

- (After ≥ one round) observe the file structure in ``trace_path`` as follows:

`````shell
tracing_path
├── otrace0
│ └── OT_TRACE_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.frk
│ └── ...
├── otrace1

│ └── ...
├── otrace ...

│ └── ...
├── lt.csv
├── jank0.csv
├── jank1.csv
├── jank ...
├── tracing0.csv
tracing1.csv
├── tracing ...
`````

## Data Analysis

The files and scripts required for data analysis are located in the ``data_analysis`` folder in the project directory.

### Data preprocessing

Since the collected indicators come from different formats and different data formats exist, it is necessary to first preprocess the indicator data. This function is performed by the ``. /data_analysis/impl_dataprocess.py``.

> TIPS: Before that, you may need to batch call the CLI to convert the FRK files in each folder of the ``trace_path`` to DB. this can be done by adding a new folder to the ``. /data_analysis/frk2db.py `` by calling ``convert_sql_impl()``.

The preprocessor will be implemented in the ``exp_dir`` output file: ``indicators_dir``.

- ``indicators_data.pkl``: packaged as ``pd.DataFrame`` containing the raw indicator data, with rows corresponding to the indicators, columns corresponding to the results of each experiment, and the elements of the DataFrame consisting of a list of the values of the indicators obtained during the experiment.
- ``indicators_intrested.csv``: Estimate the trend of the indicator data based on ``pymannkendall``, and output the results of the trend test of each indicator in each experiment to csv, the results may be: no trend, increasing, decreasing.

### Indicator analysis

The path is ``. /data_analysis/indicator_analysis.ipynb`` Jupyter Notebook enables analysis and visualization of indicator data. See the Notebook internals for instructions on how to do this.

