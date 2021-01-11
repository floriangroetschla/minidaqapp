local moo = import "moo.jsonnet";
local cmd = import "appfwk-cmd-make.jsonnet";

local NUMBER_OF_FAKE_DATA_PRODUCERS = 1;
// The factor by which to slow down data production in the
// FakeCardReader, in case the machine can't keep up
local DATA_RATE_SLOWDOWN_FACTOR = 100;

local qdict = {
  time_sync_q: cmd.qspec("time_sync_q", "FollyMPMCQueue", 100),
  trigger_inhibit_q: cmd.qspec("trigger_inhibit_q", "FollySPSCQueue", 20),
  trigger_decision_q: cmd.qspec("trigger_decision_q", "FollySPSCQueue", 20),
  trigdec_for_dataflow_bookkeeping: cmd.qspec("trigger_decision_copy_for_bookkeeping", "FollySPSCQueue", 20),
  trigdec_for_inhibit: cmd.qspec("trigger_decision_copy_for_inhibit", "FollySPSCQueue", 20),
  trigger_record_q: cmd.qspec("trigger_record_q", "FollySPSCQueue", 20),
  fake_link: cmd.qspec("fakelink-0", "FollySPSCQueue",  100000),
} + {
  ["data_requests_"+idx]: cmd.qspec("data_requests_"+idx, "FollySPSCQueue", 20),
  for idx in std.range(1, NUMBER_OF_FAKE_DATA_PRODUCERS)
} + {
  ["data_fragments_"+idx]: cmd.qspec("data_fragments_"+idx, "FollySPSCQueue", 20),
  for idx in std.range(1, NUMBER_OF_FAKE_DATA_PRODUCERS)
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

      cmd.mspec("frg", "FakeReqGen", [
        cmd.qinfo("trigger_decision_input_queue", qdict.trigger_decision_q.inst, "input"),
        cmd.qinfo("trigger_decision_for_event_building", qdict.trigdec_for_dataflow_bookkeeping.inst, "output"),
        cmd.qinfo("trigger_decision_for_inhibit", qdict.trigdec_for_inhibit.inst, "output")] +
        [cmd.qinfo("data_request_"+idx+"_output_queue", qdict["data_requests_"+idx].inst, "output")
          for idx in std.range(1, NUMBER_OF_FAKE_DATA_PRODUCERS)
        ]),

      cmd.mspec("ffr", "FakeFragRec", [
        cmd.qinfo("trigger_decision_input_queue", qdict.trigdec_for_dataflow_bookkeeping.inst, "input"),
        cmd.qinfo("trigger_record_output_queue", qdict.trigger_record_q.inst, "output")] +
        [cmd.qinfo("data_fragment_"+idx+"_input_queue", qdict["data_fragments_"+idx].inst, "input")
          for idx in std.range(1, NUMBER_OF_FAKE_DATA_PRODUCERS)
        ]),

      cmd.mspec("datawriter", "DataWriter", [
        cmd.qinfo("trigger_record_input_queue", qdict.trigger_record_q.inst, "input"),
        cmd.qinfo("trigger_decision_for_inhibit", qdict.trigdec_for_inhibit.inst, "input"),
        cmd.qinfo("trigger_inhibit_output_queue", qdict.trigger_inhibit_q.inst, "output")]),

      cmd.mspec("fake-source", "FakeCardReader",
        cmd.qinfo("output", qdict.fake_link.inst, cmd.qdir.output)),
    ] +
    [
      cmd.mspec("fake-handler", "DataLinkHandler", [
        cmd.qinfo("raw-input",  qdict.fake_link.inst, cmd.qdir.input),
        cmd.qinfo("timesync",   qdict.time_sync_q.inst, cmd.qdir.output),
        cmd.qinfo("requests",   qdict["data_requests_"+idx].inst, cmd.qdir.input),
        cmd.qinfo("fragments",  qdict["data_fragments_"+idx].inst,   cmd.qdir.output)
      ])
      for idx in std.range(1, NUMBER_OF_FAKE_DATA_PRODUCERS)
    ] 
  )
  { waitms: 1000 },

  cmd.conf([
    cmd.mcmd("tde",
      {
        "links" : [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "min_links_in_request" : NUMBER_OF_FAKE_DATA_PRODUCERS,
        "max_links_in_request" : NUMBER_OF_FAKE_DATA_PRODUCERS,
        "min_readout_window_ticks" : 1200,
        "max_readout_window_ticks" : 1200,
        "trigger_window_offset" : 600,
        "trigger_delay_ticks" : 20000,
        // We divide the trigger interval by
        // DATA_RATE_SLOWDOWN_FACTOR so the triggers are still
        // emitted once per (wall-clock) second, rather than being
        // spaced out further
        "trigger_interval_ticks" : std.floor(50000000/DATA_RATE_SLOWDOWN_FACTOR),
        "clock_frequency_hz" : 50000000/DATA_RATE_SLOWDOWN_FACTOR
      }),
    cmd.mcmd("datawriter",
      {
        "data_store_parameters": {
          "name" : "data_store",
          "type" : "HDF5DataStore",
          "directory_path": ".",
          "mode": "all-per-file",
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
        "link_id": 0,
        "input_limit": 10485100,
        "rate_khz": 2000000/12/DATA_RATE_SLOWDOWN_FACTOR/1000,
        "raw_type": "wib",
        "data_filename": "/tmp/frames.bin",
        "queue_timeout_ms": 2000
      }),
    cmd.mcmd("fake-handler",
      {
        "raw_type": "wib",
        "source_queue_timeout_ms": 2000,
        "latency_buffer_size": 100000,
        "pop_limit_pct": 0.8,
        "pop_size_pct": 0.3,
        "apa_number": 0,
        "link_number": 1
      }),
  ]) { waitms: 1000 },

  cmd.start(42) { waitms: 1000 },

  cmd.stop() { waitms: 1000 },
]
