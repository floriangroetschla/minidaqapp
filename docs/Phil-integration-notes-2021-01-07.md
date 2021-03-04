Working area based on instructions here:

https://github.com/DUNE-DAQ/minidaqapp/wiki/Simple-instructions-for-running-the-app

And readout package based on instructions here:

https://github.com/DUNE-DAQ/readout/blob/master/README.md

The exact commit hashes and branches of everything in my working area are:

```
./minidaqapp    467f2ea     feature/add-config-with-readout-fragments
./trigemu       fab62e7     main                                   
./dfmodules     5c78443     main                                   
./readout       3860dfe     master                                 
./filecmd       223b0de     master                                 
./appfwk        465e33d     develop                                
./dfmessages    b68cdee     main                                   
./daq-cmake     c055599     develop                                
./dataformats   2bd9175     (tag:snapshot_before_changes_06Jan2021)
```

`src/ReadoutModel.hpp:67` is modified to read `fake_trigger_ = false;`

`minidaqapp/schema/slightlyreal-minidaq-app-readout-timesyncs.jsonnet` is like `slightlyreal-minidaq-app.jsonnet` but the readout modules `DataLinkHandler` and `FakeCardReader` are included, and `FakeTimeSyncSource` is removed. `TimeSync` messages are sent from the `DataLinkHandler` to `TriggerDecisionEmulator` (instead of from `FakeTimeSyncSource` as before). The `FakeDataProd` modules remain, and are connected to the fragment receiver. The `DataLinkHandler`'s data output is not connected to anything.

I can run `slightlyreal-minidaq-app-readout-timesyncs.json` "successfully" in that it doesn't crash, doesn't print lots of errors (although there are some), and a non-empty HDF5 file is created at the end.

The latest item is `slightlyreal-minidaq-app-readout-fragments.json(net)` which removes the `FakeDataProd`s and connects the `DataLinkHandler`s up to the request and fragment response queues. Currently there is just one link, and `daq_application` crashes when I run with this config. I suspect memory corruption.

## Update 2021-01-11

These hashes/branches, which include all the latest changes to `dataformats`:

```
./minidaqapp         88f7475    * feature/fake-readout-multi-link
./trigemu            6edc45e    * philiprodrigues/trigger-delay
./dfmodules          3852625    * feature/TriggerRecordHeader
./readout            a690616    * philiprodrigues/multi-link-trigger-match
./filecmd            223b0de    * master
./appfwk             b4b8145    * philiprodrigues/folly-queue-no-spin (develop should be fine too)
./dfmessages         b68cdee    * main
./daq-cmake          c055599    * develop
./dataformats        122d517    * (HEAD detached at snapshot_after_changes_11Jan2021)
```

`src/ReadoutModel.hpp:67` is (still) modified to read `fake_trigger_ = false;`

Ran `minidaqapp/test/minidaq-app-fake-readout.json` which has two links and uses (non-fake) `RequestGenerator` and `FragmentReceiver`. The data rate in `FakeCardReader` is slowed down by a factor of 100 because the machine I'm using doesn't seem to be able to handle the full rate. This results in lots of HDF5 files which look to have a sensible size (~500kB per file), each containing exactly one fragment, or the `TriggerRecordHeader`:

```
> h5dump -H fake_minidaqapp_run000000_file000[456].hdf5 
HDF5 "fake_minidaqapp_run000000_file0004.hdf5" {
GROUP "/" {
   GROUP "TriggerRecord00002" {
      DATASET "TriggerRecordHeader" {
         DATATYPE  H5T_STD_I8LE
         DATASPACE  SIMPLE { ( 96, 1 ) / ( 96, 1 ) }
      }
   }
}
}
HDF5 "fake_minidaqapp_run000000_file0005.hdf5" {
GROUP "/" {
   GROUP "TriggerRecord00002" {
      GROUP "FELIX" {
         GROUP "APA000" {
            DATASET "Link00" {
               DATATYPE  H5T_STD_I8LE
               DATASPACE  SIMPLE { ( 562440, 1 ) / ( 562440, 1 ) }
            }
         }
      }
   }
}
}
HDF5 "fake_minidaqapp_run000000_file0006.hdf5" {
GROUP "/" {
   GROUP "TriggerRecord00002" {
      GROUP "FELIX" {
         GROUP "APA000" {
            DATASET "Link01" {
               DATATYPE  H5T_STD_I8LE
               DATASPACE  SIMPLE { ( 562440, 1 ) / ( 562440, 1 ) }
            }
         }
      }
   }
}
}
```