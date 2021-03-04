# Introduction

The MiniDAQApp v1 demonstrates the following, within a single application using the DUNE DAQ application framework:
* creation and distribution of trigger decisions to frontend readout modules
* creation of data fragments in response to trigger decisions (from fake FELIX TPC data)
* building of events from multiple data fragments
* writing of events to disk in HDF5 format

Some of the many things that are not included in this version of the application are:
* readout of a real FELIX card
* any interprocess communication
* much error handling
* interface with data selection system

# Modules and queues

The organization of MiniDAQApp v1 in terms of app framework modules and queues is shown in the diagram below:

![](https://user-images.githubusercontent.com/36311946/104197413-9dcf6700-53ea-11eb-84be-faec37d60fd9.png)

## Data flow modules

### `RequestGenerator`
The request generator constantly loops over its input queue (trigger decisions produced_&_sent by the TDE described below). For each trigger decision we loop over its trigger decision components. Each trigger decision component is then converted into its corresponding DataRequest (`dfmessages::DataRequest`) and by means of its GeoID (`dataformats::GeoID`) each DataRequest is then mapped into its corresponding DataLinkHandler queue. Finally each DataRequest generated is then sent to the corresponding DataLinkHandler (output) queue. 

The mapping between GeoID and DataLinkHandler (output) queue is done at configuration time and it is defined  [RequestGenerator-schema](https://github.com/DUNE-DAQ/dfmodules/blob/develop/schema/dfmodules-RequestGenerator-schema.jsonnet)

 
### `FragmentReceiver`
The fragment receiver constantly loops between its input queues (fragments and trigger decisions) to pulls the objects and keeps them stored in `books`, i.g. maps whose keys are unique trigger IDs. The trigger IDs consist of the pair of trigger_number and run_number and they are used to associate a trigger decisions with its corresponding fragments. Once the books contain for a trigger requests the corresponding number of associated fragments, a trigger record is created and it is sent to output. Please note that we only check the number of fragments, we don't check if there is a GeoID match. 

The system is simple and so there are not many configurable elements.  There is a timeout that at the moment is simply controlling how much time is necessary before the receiver starts to complain that a certain fragments is too late. The timeout is in timestamps between the last receiver trigger decision and the the fragment timestamp. 

### `DataWriter`

The data writer is responsible for writing out trigger records to a file. Currently, the data store is implemented with the HDF5 format and the data written for each trigger record is structured by "detector_type/APA_number/link_number". The TriggerRecordHeader is also included in each TriggerRecord entry. Here is an example of the structure of an HDF5 file as written by the data writer: 
```
GROUP "TriggerRecord00013" {
      GROUP "FELIX" {
         GROUP "APA000" {
            DATASET "Link00" {
               DATATYPE  H5T_STD_I8LE
               DATASPACE  SIMPLE { ( 27912, 1 ) / ( 27912, 1 ) }
            }
      }
      DATASET "TriggerRecordHeader" {
         DATATYPE  H5T_STD_I8LE
         DATASPACE  SIMPLE { ( 288, 1 ) / ( 288, 1 ) }
      }
   }
```   

An inhibit mechanism is also in place in case the data writer is not able to sustain the rate of incoming data.
    
The data writer accepts multiple configuration parameters. The most relevant are the `directory_path` (path where the output file is stored), `max_file_size_bytes` (maximum size in bytes of each output file) and `filename_parameters`.


## Readout modules
Details about the Readout specific software package can be found in the [repository](https://github.com/DUNE-DAQ/readout/wiki#functional-elements).

### `FakeCardSource`
This module stands as software emulator of a readout card. In it's current state it acts as a fake FELIX card with a configurable amount of front-end links. The emulated front-end is a single WIB link, that can replay a memory buffer with a ratelimiter that is set to the same rate as a real link. Memory buffers are loaded from ProtoDUNE raw binay data files. The module is also updating a timestamp in the WIB frames, essentially creating a useful, fake data stream that relies on timestamp and WIB frame checks. Further FE emulators (TP, PD) will be implemented in the upcoming releases.

### `DataLinkHandler`
The "link" handler modules are responsible for providing a generic (not depending on specific front-end data type) implementation of the readout system's functional elements: raw processing pipeline, latency buffer, request handling and others. The design supports the easy change of FE specialized components. A full set of the features that are needed for the local data request domain, is included and implemented in the current version.  

## Miscellaneous modules

### [`TriggerDecisionEmulator`](https://github.com/DUNE-DAQ/trigemu/tree/develop/plugins)

`TriggerDecisionEmulator` (TDE) creates trigger decisions and sends them to the dataflow subsystem. In this respect, it is effectively a fake Module-Level Trigger. TDE generates triggers at fixed timestamp intervals, controlled by configuration. Each trigger decision requests data for a random window of time, and from a random number of links. The random values are between limits set by configuration - the lower and upper bounds may be set equal to effectively remove the randomness. The full set of configuration parameters can be seen in [the `TriggerDecisionEmulator` schema](https://github.com/DUNE-DAQ/trigemu/blob/develop/schema/trigemu-TriggerDecisionEmulator-schema.jsonnet).

The `TimeSync` message queue needs some explanation: TDE must generate trigger decisions with timestamps that are likely to be present in the data in the frontend buffers - that is, timestamps that are close to "now". In the full system with a real data selection system, this happens automatically, since the trigger decisions are generated based on the data coming from the frontend, but in the MiniDAQApp v1, we have to fake it. We do this by having the `DataLinkHandler` modules periodically send the timestamp of the newest item in their buffers to the TDE, allowing it to estimate the "current" timestamp.
