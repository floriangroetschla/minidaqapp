local moo = import "moo.jsonnet";
local cmd = import "appfwk-cmd-make.jsonnet";

local NUMBER_OF_FAKE_DATA_PRODUCERS = 3;

local fdp_ns = {
    generate_config_params(linkno=1) :: {
        temporarily_hacked_link_number: linkno
    },
};

local qdict = {
    time_sync_q: cmd.qspec("time_sync_q", "FollyMPMCQueue", 100),
    trigger_inhibit_q: cmd.qspec("trigger_inhibit_q", "FollySPSCQueue", 20),
    trigger_decision_q: cmd.qspec("trigger_decision_q", "FollySPSCQueue", 20),
    trigdec_for_dataflow_bookkeeping: cmd.qspec("trigger_decision_copy_for_bookkeeping", "FollySPSCQueue", 20),
    trigdec_for_inhibit: cmd.qspec("trigger_decision_copy_for_inhibit", "FollySPSCQueue", 20),
    trigger_record_q: cmd.qspec("trigger_record_q", "FollySPSCQueue", 20),
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
             [cmd.mspec("ftss", "FakeTimeSyncSource",
                  cmd.qinfo("time_sync_sink", qdict.time_sync_q.inst, cmd.qdir.output)),
              cmd.mspec("tde", "TriggerDecisionEmulator", [
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
                  cmd.qinfo("trigger_inhibit_output_queue", qdict.trigger_inhibit_q.inst, "output")])] +
              [cmd.mspec("fdp"+idx, "FakeDataProd", [
                   cmd.qinfo("data_request_input_queue", qdict["data_requests_"+idx].inst, "input"),
                   cmd.qinfo("data_fragment_output_queue", qdict["data_fragments_"+idx].inst, "output")])
               for idx in std.range(1, NUMBER_OF_FAKE_DATA_PRODUCERS)
              ])
              { waitms: 1000 },

    cmd.conf([cmd.mcmd("ftss",
                {
                  "sync_interval_ticks": 64000000
                }),
              cmd.mcmd("tde",
                {
                  "links" : [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                  "min_links_in_request" : NUMBER_OF_FAKE_DATA_PRODUCERS,
                  "max_links_in_request" : NUMBER_OF_FAKE_DATA_PRODUCERS,
                  "min_readout_window_ticks" : 320000,
                  "max_readout_window_ticks" : 320000, 
                  "trigger_interval_ticks" : 64000000
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
                })] +
              [cmd.mcmd("fdp"+idx, fdp_ns.generate_config_params(idx))
               for idx in std.range(1, NUMBER_OF_FAKE_DATA_PRODUCERS)
              ]) { waitms: 1000 },

    cmd.start(42) { waitms: 1000 },

    cmd.stop() { waitms: 1000 },
]
