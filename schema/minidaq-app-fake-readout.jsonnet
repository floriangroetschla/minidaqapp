local moo = import "moo.jsonnet";
local cmd = import "appfwk-cmd-make.jsonnet";

local NUMBER_OF_DATA_PRODUCERS = 2;
// The factor by which to slow down data production in the
// FakeCardReader, in case the machine can't keep up
local DATA_RATE_SLOWDOWN_FACTOR = 1;

local qdict = {
  time_sync_q: cmd.qspec("time_sync_q", "FollyMPMCQueue", 100),
  trigger_inhibit_q: cmd.qspec("trigger_inhibit_q", "FollySPSCQueue", 20),
  trigger_decision_q: cmd.qspec("trigger_decision_q", "FollySPSCQueue", 20),
  trigdec_for_dataflow_bookkeeping: cmd.qspec("trigger_decision_copy_for_bookkeeping", "FollySPSCQueue", 20),
  trigdec_for_inhibit: cmd.qspec("trigger_decision_copy_for_inhibit", "FollySPSCQueue", 20),
  trigger_record_q: cmd.qspec("trigger_record_q", "FollySPSCQueue", 20),
  data_fragments_q: cmd.qspec("data_fragments_q", "FollyMPMCQueue", 100),
} + {
  ["data_requests_"+idx]: cmd.qspec("data_requests_"+idx, "FollySPSCQueue", 20),
  for idx in std.range(0, NUMBER_OF_DATA_PRODUCERS-1)
} + {
  ["fake_link_"+idx]: cmd.qspec("fake_link_"+idx, "FollySPSCQueue", 100000),
  for idx in std.range(0, NUMBER_OF_DATA_PRODUCERS-1)
};

local qspec_list = [
  qdict[xx]
  for xx in std.objectFields(qdict)
];

[
  cmd.init(qspec_list,
    [cmd.mspec("tde", "TriggerDecisionEmulator", [
      cmd.qinfo("time_sync_source", qdict.time_sync_q.inst, "input"),
      cmd.qinfo("trigger_inhibit_source", qdict.trigger_inhibit_q.inst, "input"),
      cmd.qinfo("trigger_decision_sink", qdict.trigger_decision_q.inst, "output")]),

      cmd.mspec("rqg", "RequestGenerator", [
        cmd.qinfo("trigger_decision_input_queue", qdict.trigger_decision_q.inst, "input"),
        cmd.qinfo("trigger_decision_for_event_building", qdict.trigdec_for_dataflow_bookkeeping.inst, "output"),
        cmd.qinfo("trigger_decision_for_inhibit", qdict.trigdec_for_inhibit.inst, "output")] +
        [cmd.qinfo("data_request_"+idx+"_output_queue", qdict["data_requests_"+idx].inst, "output")
          for idx in std.range(0, NUMBER_OF_DATA_PRODUCERS-1)
        ]),

      cmd.mspec("ffr", "FragmentReceiver", [
        cmd.qinfo("trigger_decision_input_queue", qdict.trigdec_for_dataflow_bookkeeping.inst, "input"),
        cmd.qinfo("trigger_record_output_queue", qdict.trigger_record_q.inst, "output"),
        cmd.qinfo("data_fragment_input_queue", qdict.data_fragments_q.inst, "input")
        ]),

      cmd.mspec("datawriter", "DataWriter", [
        cmd.qinfo("trigger_record_input_queue", qdict.trigger_record_q.inst, "input"),
        cmd.qinfo("trigger_decision_for_inhibit", qdict.trigdec_for_inhibit.inst, "input"),
        cmd.qinfo("trigger_inhibit_output_queue", qdict.trigger_inhibit_q.inst, "output")]),

      cmd.mspec("fake-source", "FakeCardReader", [
        cmd.qinfo("output_"+idx, qdict["fake_link_"+idx].inst, cmd.qdir.output)
          for idx in std.range(0, NUMBER_OF_DATA_PRODUCERS-1)
        ]),
    ] +
    [
      cmd.mspec("datahandler_"+idx, "DataLinkHandler", [
        cmd.qinfo("raw-input",  qdict["fake_link_"+idx].inst, cmd.qdir.input),
        cmd.qinfo("timesync",   qdict.time_sync_q.inst, cmd.qdir.output),
        cmd.qinfo("requests",   qdict["data_requests_"+idx].inst, cmd.qdir.input),
        cmd.qinfo("fragments",  qdict.data_fragments_q.inst,   cmd.qdir.output)
      ])
      for idx in std.range(0, NUMBER_OF_DATA_PRODUCERS-1)
    ] 
  )
  { waitms: 1000 },

  cmd.conf([
    cmd.mcmd("tde",
      {
        "links" : [idx
          for idx in std.range(0, NUMBER_OF_DATA_PRODUCERS-1)] ,
        "min_links_in_request" : NUMBER_OF_DATA_PRODUCERS,
        "max_links_in_request" : NUMBER_OF_DATA_PRODUCERS,
        "min_readout_window_ticks" : 1200,
        "max_readout_window_ticks" : 1200,
        "trigger_window_offset" : 1000,
        "trigger_delay_ticks" : 50000000,
        // We divide the trigger interval by
        // DATA_RATE_SLOWDOWN_FACTOR so the triggers are still
        // emitted once per (wall-clock) second, rather than being
        // spaced out further
        "trigger_interval_ticks" : std.floor(100000000/DATA_RATE_SLOWDOWN_FACTOR),
        "clock_frequency_hz" : 100000000/DATA_RATE_SLOWDOWN_FACTOR
      }),
    cmd.mcmd("rqg",
                {
                  "map" : [{"apa" : 0 , "link" : idx , "queueinstance" : qdict["data_requests_"+idx].inst} 
		  for idx in std.range(0, NUMBER_OF_DATA_PRODUCERS-1)] 
                }),
    cmd.mcmd("ffr",
                {
                  "general_queue_timeout" : 100,
                  "max_timestamp_diff" : 50000000
                }),
    cmd.mcmd("datawriter",
      {
        "data_store_parameters": {
          "name" : "data_store",
          "type" : "HDF5DataStore",
          "directory_path": "/tmp/",
          "mode": "all-per-file",
          "max_file_size_bytes": 1073741834,
          "filename_parameters": {
            "overall_prefix": "fake_minidaqapp",
            "digits_for_run_number": 6,
            "file_index_prefix": "file",
          },
          "file_layout_parameters": {
            "trigger_record_name_prefix": "TriggerRecord",
            "digits_for_trigger_number": 5,
          },
        }
      }),
    cmd.mcmd("fake-source",
      {
        "link_ids": [idx
          for idx in std.range(0, NUMBER_OF_DATA_PRODUCERS-1)],
        "input_limit": 10485100,
        "rate_khz": 2000000/12/DATA_RATE_SLOWDOWN_FACTOR/1000,
        "raw_type": "wib",
        "data_filename": "/tmp/frames.bin",
        "queue_timeout_ms": 3000
      }),
    ] +
    [cmd.mcmd("datahandler_"+idx,
      {
        "raw_type": "wib",
        "source_queue_timeout_ms": 3000,
        "latency_buffer_size": 1000000,
        "pop_limit_pct": 0.8,
        "pop_size_pct": 0.1,
        "apa_number": 0,
        "link_number": idx
      })
      for idx in std.range(0, NUMBER_OF_DATA_PRODUCERS-1)
    ]) { waitms: 1000 },

  cmd.start(333) { waitms: 1000 },

  cmd.stop() { waitms: 1000 },
]
