#!/usr/bin/env python3
import moo.otypes

from dunedaq.env import get_moo_model_path
moo.otypes.load_types('appfwk-cmd-schema.jsonnet', get_moo_model_path())
# moo.otypes.load_types('readout-DataLinkHandler-schema.jsonnet', get_moo_model_path())git 
# moo.otypes.load_types('readout-FelixCardReader-schema.jsonnet', get_moo_model_path())git 

import json

import dunedaq.appfwk.cmd as cmd # AddressedCmd, 
# import dunedaq.readout.datalinkhandler as ldh
# import dunedaq.readout.felixcardreader as fcr


def genconf(NUMBER_OF_DATA_PRODUCERS):

    # Define modules and queues
    queue_specs = cmd.QueueSpecs(
        [
            cmd.QueueSpec(inst="time_sync_q", kind='FollyMPMCQueue', capacity=100),
            cmd.QueueSpec(inst="trigger_inhibit_q", kind='FollySPSCQueue', capacity=20),
            cmd.QueueSpec(inst="trigger_decision_q", kind='FollySPSCQueue', capacity=20),
            cmd.QueueSpec(inst="trigger_decision_copy_for_bookkeeping", kind='FollySPSCQueue', capacity=20),
            cmd.QueueSpec(inst="trigdec_for_inhibit", kind='FollySPSCQueue', capacity=20),
            cmd.QueueSpec(inst="trigger_record_q", kind='FollySPSCQueue', capacity=20),
            cmd.QueueSpec(inst="data_fragments_q", kind='FollyMPMCQueue', capacity=100),
        ] + [
            cmd.QueueSpec(inst=f"data_requests_{idx}", kind='FollySPSCQueue', capacity=20)
                for idx in range(NUMBER_OF_DATA_PRODUCERS)
        ] + [
            cmd.QueueSpec(inst=f"fake_link_{idx}", kind='FollySPSCQueue', capacity=100000)
                for idx in range(NUMBER_OF_DATA_PRODUCERS)
        ]
    )

    mod_specs = [
        cmd.ModSpec(inst="tde", plugin="TriggerDecisionEmulator",
            data=cmd.ModInit(
                qinfos=cmd.QueueInfos([
                        cmd.QueueInfo(name="linkdata", inst="time_sync_q", dir="input"),
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
                        cmd.QueueInfo(name="trigger_decision_for_inhibit", inst="trigdec_for_inhibit", dir="input"),
                        cmd.QueueInfo(name="trigger_inhibit_output_queue", inst="trigger_inhibit_q", dir="output"),
                    ])
                )
            ), 

        cmd.ModSpec(inst="fake-source", plugin="FakeCardReader",
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
                            cmd.QueueInfo(name="raw-input", inst=f"fake_link_{idx}", dir="input"),
                            cmd.QueueInfo(name="timesync", inst="time_sync_q", dir="output"),
                            cmd.QueueInfo(name="requests", inst=f"data_requests_{idx}", dir="input"),
                            cmd.QueueInfo(name="fragments", inst="data_fragments_q", dir="output"),
                            ])
                    )
                ) for idx in range(NUMBER_OF_DATA_PRODUCERS)
        ]

print(mod_specs)


if __name__ == '__main__':
    genconf(1)