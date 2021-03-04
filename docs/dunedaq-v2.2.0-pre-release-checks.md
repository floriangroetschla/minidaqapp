## MiniDAQ app python-based configuration smoke test

### Overview
An python-based DAQ application configuration generation example is available in `minidaqapp`, in the `thea/python-confgen` branch.
The `minidaqapp.fake_app_confgen` produces a fake minidaqapp configuration, where a number of parameters are configurable.
The module implements the `generate` function that similar arguments as its jsonnet counterpart: 
```
def generate(
        NUMBER_OF_DATA_PRODUCERS=2,          
        DATA_RATE_SLOWDOWN_FACTOR = 10,
        RUN_NUMBER = 333, 
        TRIGGER_RATE_HZ = 1.0,
        DATA_FILE="./frames.bin",
        OUTPUT_PATH=".",
    )
```

A CLI is provided by the module. It allows invoke the config generation from shell and specify the parameters as options (see below).

###  Setting up a work area for python-based configuration test

After setting up the runtime environment `minidaqapp.fake_app_confgen` is reachable via `PYTHONPATH`, e.g.

```
python -m minidaqapp.fake_app_confgen -d /tmp/frames.bin -o /tmp my_minidaq_config.json
```
Minimal cut & paste instructions for your convenience:
```sh
git clone https://github.com/DUNE-DAQ/daq-buildtools.git -b v2.0.1
git clone https://github.com/DUNE-DAQ/daq-release.git -b thea/prep-dunedaq-v2.2.0
source daq-buildtools/dbt-setup-env.sh
mkdir pywork
cd pywork
dbt-create.sh -r ../daq-release/configs/ dunedaq-v2.2.0-prep
dbt-setup-build-environment
cd sourcecode/
git clone https://github.com/DUNE-DAQ/daq-cmake -b v1.2.2
git clone https://github.com/DUNE-DAQ/cmdlib -b v1.0.2
git clone https://github.com/DUNE-DAQ/appfwk.git -b v2.1.0
git clone https://github.com/DUNE-DAQ/dataformats.git -b v1.0.0
git clone https://github.com/DUNE-DAQ/dfmessages.git -b v1.0.0
git clone https://github.com/DUNE-DAQ/dfmodules.git -b v1.1.1
git clone https://github.com/DUNE-DAQ/trigemu.git -b v1.0.0
git clone https://github.com/DUNE-DAQ/readout.git -b v1.0.1
git clone https://github.com/DUNE-DAQ/minidaqapp.git -b v1.2.0
dbt-build.sh
dbt-setup-runtime-environment
```

### Generating a new configuration
After setting up the runtime environment `minidaqapp.fake_app_confgen` is reachable via `PYTHONPATH`, e.g.
```
python -m minidaqapp.fake_app_confgen -d /tmp/frames.bin -o /tmp my_minidaq_config.json
```

The `-h/--help` flag is the quickest way to check what `minidaqapp.fake_app_confgen` options are available, when in doubt:
```
--(minidaqapp)--> python -m minidaqapp.fake_app_confgen --help
Usage: fake_app_confgen.py [OPTIONS] [JSON_FILE]

  JSON_FILE: Input raw data file. JSON_FILE: Output json configuration file.

Options:
  -n, --number-of-data-producers INTEGER
  -s, --data-rate-slowdown-factor INTEGER
  -r, --run-number INTEGER
  -t, --trigger-rate-hz FLOAT
  -d, --data-file PATH
  -o, --output-path PATH
  -h, --help                      Show this message and exit.
```

The so-created configuration can be tested following the instructions from the [Simple instructions for running the app
](Simple-instructions-for-running-the-app)
```daq_application -c stdin://./my_minidaq_config.json```

### Summary of changes to minidaqapp repositories
1. `appfwk`: added `StartParams` and `EmptyParams` records.
            added `appfwk.utils` utility functions.
2. **FIXED** `dfmodules`: minor issue with empty string records. 
   ```
   s.field("file_index_prefix", self.fnprefix, "", doc="Prefix for the file index part of the filename"),
   ```
   Issue reported to Brett and fixed.
3. `readout`: 
   - `DataLinkHandler`'s and `FakeCardReader`'s `Str` type was defined as a string matching the `string` pattern.
   - Dashes `-` converted to `_` in instance names,
4. `minidaqapp`: added `fake_app_confgen` module.


### Additional information
- `minidaqapp.confgen` imports the queue and module specifications from schema files using `moo.otypes.load_types`. The search path for schema files is set as part of the runtime environment. It includes daq ups packages as local packages (from `build/<package_name>/schema/`). Therefore `dbt-build.sh` must be run before any local changes can be picked up. The same applies to python modules.
- In `minidaqapp.fake_app_confgen` the pramble
  ```python
  # Set moo schema search path
  from dunedaq.env import get_moo_model_path
  import moo.io
  moo.io.default_load_path = get_moo_model_path()
  ```
  is needed to provide `moo` with the location of `schema` folders in dunedaq packages.
  `get_moo_model_path` is a convenience function that uses the `DUNEDAQ_SHARE_PATH` to create the path list expected by `moo`.
- Importing schema in python requires 2 steps:
  1. Loading the schema in moo
     ```python
     # Load configuration types
     import moo.otypes
     moo.otypes.load_types('appfwk-cmd-schema.jsonnet')
     ```
  2. and importing the moo-created python classes in the current scope
     ```python
     import dunedaq.appfwk.cmd as cmd # AddressedCmd, 
     ```
     The imported module namespace corresponds to the namespace defined in jsonnet
     ```jsonnet
     local s = moo.oschema.schema("dunedaq.appfwk.cmd");
     ```
- The records defined in the schema files are converted in python classes, e.g.
  ```jsonnet
    qspec: s.record("QueueSpec", [
        s.field("kind", self.qkind,
                doc="The kind (type) of queue"),
        s.field("inst", self.inst,
                doc="Instance name"),
        s.field("capacity", self.capacity,
                doc="The queue capacity"),
    ], doc="Queue specification"),
  ```
  where the name of the class corresponds to the record name and _not_ the jsonnet variable (`qspec`, in the previous example)
  ```python
  >>> qs = cmd.QueueSpec(inst="time_sync_q", kind='FollyMPMCQueue', capacity=100)
  >>> print(qs)
  <record QueueSpec, fields: {kind, inst, capacity}>
  >>> print(qs.inst)
  time_sync_q
  >>> print(qs.pod())
  {'kind': 'FollyMPMCQueue', 'inst': 'time_sync_q', 'capacity': 100}
  ```
* Trying to assign a value of the wrong kind to a field will result in an error, at construction
  ```python
  >>> qs = cmd.QueueSpec(inst="time_sync_q", kind='FollyMPMCQueue', capacity="aaa")
  Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
    File "<record QueueSpec>", line 15, in __init__
    File "/home/ale/devel/dd-2-2-0-py/pywork/dbt-pyvenv/src/moo/moo/otypes.py", line 144, in update
      self._from_dict(kwds)
    File "/home/ale/devel/dd-2-2-0-py/pywork/dbt-pyvenv/src/moo/moo/otypes.py", line 187, in _from_dict
      self._value[fname] = item(fval)
    File "<number QueueCapacity>", line 13, in __init__
    File "/home/ale/devel/dd-2-2-0-py/pywork/dbt-pyvenv/src/moo/moo/otypes.py", line 483, in update
      self._value = numpy.array(val, type)
  ValueError: invalid literal for int() with base 10: 'aaa'
  ```
  or in a post-creation assignment
  ```python
  >>> qs.inst = 4
  Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
    File "<record QueueSpec>", line 45, in inst
    File "<string InstName>", line 16, in __init__
    File "/home/ale/devel/dd-2-2-0-py/pywork/dbt-pyvenv/src/moo/moo/otypes.py", line 361, in update
      raise ValueError(f'illegal type for string {cname}: {type(val)}')
  ValueError: illegal type for string InstName: <class 'int'>
  ```
  **WARNING**: In the current `moo` version this check applies to POD fields but not to record fields. In the latter case, assigning a variable of the wrong kind will not result in an error. This is a bug which needs fixing.