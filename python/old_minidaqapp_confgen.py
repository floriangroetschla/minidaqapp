#!/usr/bin/env python3
import moo.otypes

from dunedaq.env import get_moo_model_path
moo.otypes.load_types('appfwk-cmd-schema.jsonnet', get_moo_model_path())
moo.otypes.load_types('trigemu-TriggerDecisionEmulator-schema.jsonnet', get_moo_model_path())
moo.otypes.load_types('dfmodules-RequestGenerator-schema.jsonnet', get_moo_model_path())
moo.otypes.load_types('dfmodules-FragmentReceiver-schema.jsonnet', get_moo_model_path())
moo.otypes.load_types('dfmodules-DataWriter-schema.jsonnet', get_moo_model_path())
moo.otypes.load_types('dfmodules-HDF5DataStore-schema.jsonnet', get_moo_model_path())
moo.otypes.load_types('readout-FakeCardReader-schema.jsonnet', get_moo_model_path())
moo.otypes.load_types('readout-DataLinkHandler-schema.jsonnet', get_moo_model_path())

import json
import math

import dunedaq.appfwk.cmd as cmd # AddressedCmd, 
import dunedaq.trigemu.triggerdecisionemulator as tde
import dunedaq.dfmodules.requestgenerator as rqg
import dunedaq.dfmodules.fragmentreceiver as ffr
import dunedaq.dfmodules.datawriter as dw
import dunedaq.dfmodules.hdf5datastore as hdf5ds
import dunedaq.readout.fakecardreader as fcr
import dunedaq.readout.datalinkhandler as dlh

# Time to waait on pop()
QUEUE_POP_WAIT_MS=100;
# local clock speed Hz
CLOCK_SPEED_HZ = 50000000;


def genconf(
    NUMBER_OF_DATA_PRODUCERS=2,          
    DATA_RATE_SLOWDOWN_FACTOR = 10,
    RUN_NUMBER = 333, 
    TRIGGER_RATE_HZ = 1.0
    ):
    
    trigger_interval_ticks = math.floor((1/TRIGGER_RATE_HZ) * CLOCK_SPEED_HZ/DATA_RATE_SLOWDOWN_FACTOR)

    # Define modules and queues
    queue_bare_specs = [
            cmd.QueueSpec(inst="time_sync_q", kind='FollyMPMCQueue', capacity=100),
            cmd.QueueSpec(inst="trigger_inhibit_q", kind='FollySPSCQueue', capacity=20),
            cmd.QueueSpec(inst="trigger_decision_q", kind='FollySPSCQueue', capacity=20),
            cmd.QueueSpec(inst="trigger_decision_copy_for_bookkeeping", kind='FollySPSCQueue', capacity=20),
            cmd.QueueSpec(inst="trigger_decision_copy_for_inhibit", kind='FollySPSCQueue', capacity=20),
            cmd.QueueSpec(inst="trigger_record_q", kind='FollySPSCQueue', capacity=20),
            cmd.QueueSpec(inst="data_fragments_q", kind='FollyMPMCQueue', capacity=100),
        ] + [
            cmd.QueueSpec(inst=f"data_requests_{idx}", kind='FollySPSCQueue', capacity=20)
                for idx in range(NUMBER_OF_DATA_PRODUCERS)
        ] + [
            cmd.QueueSpec(inst=f"fake_link_{idx}", kind='FollySPSCQueue', capacity=100000)
                for idx in range(NUMBER_OF_DATA_PRODUCERS)
        ]
    

    queue_specs = cmd.QueueSpecs(sorted(queue_bare_specs, key=lambda x: x.inst))

    mod_specs = [
        cmd.ModSpec(inst="tde", plugin="TriggerDecisionEmulator",
            data=cmd.ModInit(
                qinfos=cmd.QueueInfos([
                        cmd.QueueInfo(name="time_sync_source", inst="time_sync_q", dir="input"),
                        cmd.QueueInfo(name="trigger_inhibit_source", inst="trigger_inhibit_q", dir="input"),
                        cmd.QueueInfo(name="trigger_decision_sink", inst="trigger_decision_q", dir="output"),
                    ])
                )
            ),

        cmd.ModSpec(inst="rqg", plugin="RequestGenerator",
            data=cmd.ModInit(
                qinfos=cmd.QueueInfos([
                        cmd.QueueInfo(name="trigger_decision_input_queue", inst="trigger_decision_q", dir="input"),
                        cmd.QueueInfo(name="trigger_decision_for_event_building", inst="trigger_decision_copy_for_bookkeeping", dir="output"),
                        cmd.QueueInfo(name="trigger_decision_for_inhibit", inst="trigger_decision_copy_for_inhibit", dir="output"),
                    ] + [
                        cmd.QueueInfo(name=f"data_request_{idx}_output_queue", inst=f"data_requests_{idx}", dir="output")
                            for idx in range(NUMBER_OF_DATA_PRODUCERS)
                    ])
                )
            ),

        cmd.ModSpec(inst="ffr", plugin="FragmentReceiver",
            data=cmd.ModInit(
                qinfos=cmd.QueueInfos([
                        cmd.QueueInfo(name="trigger_decision_input_queue", inst="trigger_decision_copy_for_bookkeeping", dir="input"),
                        cmd.QueueInfo(name="trigger_record_output_queue", inst="trigger_record_q", dir="output"),
                        cmd.QueueInfo(name="data_fragment_input_queue", inst="data_fragments_q", dir="input"),
                    ])
                )
            ),   

        cmd.ModSpec(inst="datawriter", plugin="DataWriter",
            data=cmd.ModInit(
                qinfos=cmd.QueueInfos([
                        cmd.QueueInfo(name="trigger_record_input_queue", inst="trigger_record_q", dir="input"),
                        cmd.QueueInfo(name="trigger_decision_for_inhibit", inst="trigger_decision_copy_for_inhibit", dir="input"),
                        cmd.QueueInfo(name="trigger_inhibit_output_queue", inst="trigger_inhibit_q", dir="output"),
                    ])
                )
            ), 

        cmd.ModSpec(inst="fake_source", plugin="FakeCardReader",
            data=cmd.ModInit(
                qinfos=cmd.QueueInfos([
                        cmd.QueueInfo(name=f"output_{idx}", inst=f"fake_link_{idx}", dir="output")
                            for idx in range(NUMBER_OF_DATA_PRODUCERS)
                        ])
                )
            ), 
        ] + [
            cmd.ModSpec(inst=f"datahandler_{idx}", plugin="DataLinkHandler",
                data=cmd.ModInit(
                    qinfos=cmd.QueueInfos([
                            cmd.QueueInfo(name="raw_input", inst=f"fake_link_{idx}", dir="input"),
                            cmd.QueueInfo(name="timesync", inst="time_sync_q", dir="output"),
                            cmd.QueueInfo(name="requests", inst=f"data_requests_{idx}", dir="input"),
                            cmd.QueueInfo(name="fragments", inst="data_fragments_q", dir="output"),
                            ])
                    )
                ) for idx in range(NUMBER_OF_DATA_PRODUCERS)
        ]

    print(mod_specs)
    appinit = cmd.Init(queues=queue_specs, modules=mod_specs)

    jstr = json.dumps(appinit.pod(), indent=4, sort_keys=True)
    print(jstr)

    initcmd = cmd.Command(
        id=cmd.CmdId("init"),
        data=appinit
    )

    confcmd = cmd.Command(
        id=cmd.CmdId("conf"),
        data=cmd.CmdObj(
            modules=cmd.AddressedCmds([
                cmd.AddressedCmd(match="tde", data=tde.ConfParams(
                    links=[idx for idx in range(NUMBER_OF_DATA_PRODUCERS)],
                    min_links_in_request=NUMBER_OF_DATA_PRODUCERS,
                    max_links_in_request=NUMBER_OF_DATA_PRODUCERS,
                    min_readout_window_ticks=1200,
                    max_readout_window_ticks=1200,
                    trigger_window_offset=1000,
                    # The delay is set to put the trigger well within the latency buff
                    trigger_delay_ticks=math.floor( 2* CLOCK_SPEED_HZ/DATA_RATE_SLOWDOWN_FACTOR),
                    # We divide the trigger interval by
                    # DATA_RATE_SLOWDOWN_FACTOR so the triggers are still
                    # emitted per (wall-clock) second, rather than being
                    # spaced out further
                    trigger_interval_ticks=trigger_interval_ticks,
                    clock_frequency_hz=CLOCK_SPEED_HZ/DATA_RATE_SLOWDOWN_FACTOR                    
                    )
                ),
                cmd.AddressedCmd(match="rqg", data=rqg.ConfParams(
                    map=rqg.mapgeoidqueue([
                            rqg.geoidinst(apa=0, link=idx, queueinstance=f"data_requests_{idx}") for idx in range(NUMBER_OF_DATA_PRODUCERS)
                        ])  
                    )
                ),
                cmd.AddressedCmd(match="ffr", data=ffr.ConfParams(
                        general_queue_timeout=QUEUE_POP_WAIT_MS
                    )
                ),
                cmd.AddressedCmd(match="datawriter", data=dw.ConfParams(
                        data_store_parameters=hdf5ds.ConfParams(
                            name="data_store",
                            # type = "HDF5DataStore", # default
                            # directory_path = ".", # default
                            # mode = "all-per-file", # default
                            max_file_size_bytes = 1073741834,
                            filename_parameters = hdf5ds.HDF5DataStoreFileNameParams(
                                overall_prefix = "fake_minidaqapp",
                                # digits_for_run_number = 6, #default
                                file_index_prefix = "file"
                            ),
                            file_layout_parameters = hdf5ds.HDF5DataStoreFileLayoutParams(
                                trigger_record_name_prefix= "TriggerRecord",
                                digits_for_trigger_number = 5,
                            )
                        )
                    )
                ),
                cmd.AddressedCmd(match="fake_source", data=fcr.Conf(
                        link_ids=list(range(NUMBER_OF_DATA_PRODUCERS)),
                        # input_limit=10485100, # default
                        rate_khz = CLOCK_SPEED_HZ/(25*12*DATA_RATE_SLOWDOWN_FACTOR*1000),
                        raw_type = "wib",
                        data_filename = "./frames.bin",
                        queue_timeout_ms = QUEUE_POP_WAIT_MS
                    )
                ),
            ] + [
                    cmd.AddressedCmd(match=f"datahandler_{idx}", data=dlh.Conf(
                        raw_type = "wib",
                        # fake_trigger_flag=0, # default
                        source_queue_timeout_ms= QUEUE_POP_WAIT_MS,
                        latency_buffer_size = 3*CLOCK_SPEED_HZ/(25*12*DATA_RATE_SLOWDOWN_FACTOR),
                        pop_limit_pct = 0.8,
                        pop_size_pct = 0.1,
                        apa_number = 0,
                        link_number = idx
                        )) for idx in range(NUMBER_OF_DATA_PRODUCERS)
                ]
            )
        )
    )


    jstr = json.dumps(confcmd.pod(), indent=4, sort_keys=True)
    print(jstr)

    startpars = cmd.StartParams(run=RUN_NUMBER)
    startcmd = cmd.Command(
        id=cmd.CmdId("start"),
        data=cmd.CmdObj(
            modules=cmd.AddressedCmds([
                    cmd.AddressedCmd(match="datawriter", data=startpars),
                    cmd.AddressedCmd(match="ffr", data=startpars),
                    cmd.AddressedCmd(match="datahandler_.*", data=startpars),
                    cmd.AddressedCmd(match="fake_source", data=startpars),
                    cmd.AddressedCmd(match="rqg", data=startpars),
                    cmd.AddressedCmd(match="tde", data=startpars),
                ])
            )
        )

    jstr = json.dumps(startcmd.pod(), indent=4, sort_keys=True)
    print("="*80+"\nStart\n\n", jstr)

    emptypars = cmd.EmptyParams()

    stopcmd = cmd.Command(
        id=cmd.CmdId("stop"),
            data=cmd.CmdObj(
                modules=cmd.AddressedCmds([
                        cmd.AddressedCmd(match="tde", data=emptypars),
                        cmd.AddressedCmd(match="rqg", data=emptypars),
                        cmd.AddressedCmd(match="fake_source", data=emptypars),
                        cmd.AddressedCmd(match="datahandler_.*", data=emptypars),
                        cmd.AddressedCmd(match="ffr", data=emptypars),
                        cmd.AddressedCmd(match="datawriter", data=emptypars),
                    ])
                )
            )

    jstr = json.dumps(stopcmd.pod(), indent=4, sort_keys=True)
    print("="*80+"\nStop\n\n", jstr)

    pausecmd = cmd.Command(
        id=cmd.CmdId("pause"),
            data=cmd.CmdObj(
                modules=cmd.AddressedCmds([
                    cmd.AddressedCmd(
                        match="",
                        data=emptypars
                   )]
                )
            )
        )


    jstr = json.dumps(pausecmd.pod(), indent=4, sort_keys=True)
    print("="*80+"\nPause\n\n", jstr)

    resumecmd = cmd.Command(
        id=cmd.CmdId("resume"),
            data=cmd.CmdObj(
                modules=cmd.AddressedCmds([
                        cmd.AddressedCmd(match="tde", data=tde.ResumeParams(
                            trigger_interval_ticks=trigger_interval_ticks
                        )),
                ])
            )
        )
    


    jstr = json.dumps(resumecmd.pod(), indent=4, sort_keys=True)
    print("="*80+"\nResume\n\n", jstr)

    scrapcmd = cmd.Command(
        id=cmd.CmdId("scrap"),
            data=cmd.CmdObj(
                modules=cmd.AddressedCmds([
                    cmd.AddressedCmd(
                        match="",
                        data=emptypars
                   )]
                )
            )
        )


    jstr = json.dumps(scrapcmd.pod(), indent=4, sort_keys=True)
    print("="*80+"\nScrap\n\n", jstr)

    # Create a list of commands
    cmd_seq = [initcmd, confcmd, startcmd, stopcmd, pausecmd, resumecmd, scrapcmd]

    # Print them as json (to be improved/moved out)
    jstr = json.dumps([c.pod() for c in cmd_seq], indent=4, sort_keys=True)
    return jstr
        
if __name__ == '__main__':
    with open('minidaq-app-fake-readout.json', 'w') as f:
        f.write(genconf())
