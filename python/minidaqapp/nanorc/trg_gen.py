# testapp_noreadout_two_process.py

# This python configuration produces *two* json configuration files
# that together form a MiniDAQApp with the same functionality as
# MiniDAQApp v1, but in two processes. One process contains the
# TriggerDecisionEmulator, while the other process contains everything
# else. The network communication is done with the QueueToNetwork and
# NetworkToQueue modules from the nwqueueadapters package.
#
# As with testapp_noreadout_confgen.py
# in this directory, no modules from the readout package are used: the
# fragments are provided by the FakeDataProd module from dfmodules


# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes
moo.otypes.load_types('rcif/cmd.jsonnet')
moo.otypes.load_types('appfwk/cmd.jsonnet')
moo.otypes.load_types('appfwk/app.jsonnet')

moo.otypes.load_types('trigemu/triggerdecisionemulator.jsonnet')
moo.otypes.load_types('nwqueueadapters/queuetonetwork.jsonnet')
moo.otypes.load_types('nwqueueadapters/networktoqueue.jsonnet')
moo.otypes.load_types('serialization/networkobjectreceiver.jsonnet')
moo.otypes.load_types('serialization/networkobjectsender.jsonnet')

# Import new types
import dunedaq.cmdlib.cmd as basecmd # AddressedCmd, 
import dunedaq.rcif.cmd as rccmd # AddressedCmd, 
import dunedaq.appfwk.cmd as cmd # AddressedCmd, 
import dunedaq.appfwk.app as app # AddressedCmd,
import dunedaq.trigemu.triggerdecisionemulator as tde
import dunedaq.nwqueueadapters.networktoqueue as ntoq
import dunedaq.nwqueueadapters.queuetonetwork as qton
import dunedaq.serialization.networkobjectreceiver as nor
import dunedaq.serialization.networkobjectsender as nos

from appfwk.utils import mcmd, mrccmd, mspec

import json
import math
from pprint import pprint


#===============================================================================
def acmd(mods: list) -> cmd.CmdObj:
    """ 
    Helper function to create appfwk's Commands addressed to modules.
        
    :param      cmdid:  The coommand id
    :type       cmdid:  str
    :param      mods:   List of module name/data structures 
    :type       mods:   list
    
    :returns:   A constructed Command object
    :rtype:     dunedaq.appfwk.cmd.Command
    """
    return cmd.CmdObj(
        modules=cmd.AddressedCmds(
            cmd.AddressedCmd(match=m, data=o)
            for m,o in mods
        )
    )

#===============================================================================
def generate(
        NETWORK_ENDPOINTS: list,
        NUMBER_OF_DATA_PRODUCERS: int = 2,          
        DATA_RATE_SLOWDOWN_FACTOR: int = 1,
        RUN_NUMBER: int = 333, 
        TRIGGER_RATE_HZ: float = 1.0,
        DATA_FILE: str = "./frames.bin",
        OUTPUT_PATH: str = ".",
        TOKEN_COUNT: int = 10,
        CLOCK_SPEED_HZ: int = 50000000,
    ):
    """
    { item_description }
    """
    cmd_data = {}

    required_eps = {'trigdec', 'triginh', 'timesync'}
    if not required_eps.issubset(NETWORK_ENDPOINTS):
        raise RuntimeError(f"ERROR: not all the required endpoints ({', '.join(required_eps)}) found in list of endpoints {' '.join(NETWORK_ENDPOINTS.keys())}")


    # Derived parameters
    TRG_INTERVAL_TICKS = math.floor((1/TRIGGER_RATE_HZ) * CLOCK_SPEED_HZ/DATA_RATE_SLOWDOWN_FACTOR)
    MIN_READOUT_WINDOW_TICKS = math.floor(CLOCK_SPEED_HZ/(DATA_RATE_SLOWDOWN_FACTOR*1000))
    MAX_READOUT_WINDOW_TICKS = math.floor(CLOCK_SPEED_HZ/(DATA_RATE_SLOWDOWN_FACTOR*1000))
    TRIGGER_WINDOW_OFFSET=math.floor(CLOCK_SPEED_HZ/(DATA_RATE_SLOWDOWN_FACTOR*2000))
    # The delay is set to put the trigger well within the latency buff
    TRIGGER_DELAY_TICKS=math.floor(CLOCK_SPEED_HZ/DATA_RATE_SLOWDOWN_FACTOR)

    # Define modules and queues
    queue_bare_specs = [
            app.QueueSpec(inst="time_sync_from_netq", kind='FollySPSCQueue', capacity=100),
            app.QueueSpec(inst="token_from_netq", kind='FollySPSCQueue', capacity=20),
            app.QueueSpec(inst="trigger_decision_to_netq", kind='FollySPSCQueue', capacity=20),
        ]

    # Only needed to reproduce the same order as when using jsonnet
    queue_specs = app.QueueSpecs(sorted(queue_bare_specs, key=lambda x: x.inst))


    mod_specs = [
        mspec("qton_trigdec", "QueueToNetwork", [
                        app.QueueInfo(name="input", inst="trigger_decision_to_netq", dir="input")
                    ]),

        mspec("ntoq_token", "NetworkToQueue", [
                        app.QueueInfo(name="output", inst="token_from_netq", dir="output")
                    ]),

        mspec("ntoq_timesync", "NetworkToQueue", [
                        app.QueueInfo(name="output", inst="time_sync_from_netq", dir="output")
                    ]),

        mspec("tde", "TriggerDecisionEmulator", [
                        app.QueueInfo(name="time_sync_source", inst="time_sync_from_netq", dir="input"),
                        app.QueueInfo(name="token_source", inst="token_from_netq", dir="input"),
                        app.QueueInfo(name="trigger_decision_sink", inst="trigger_decision_to_netq", dir="output"),
                    ]),
        ]

    cmd_data['init'] = app.Init(queues=queue_specs, modules=mod_specs)

    cmd_data['conf'] = acmd([
                ("qton_trigdec", qton.Conf(msg_type="dunedaq::dfmessages::TriggerDecision",
                                           msg_module_name="TriggerDecisionNQ",
                                           sender_config=nos.Conf(ipm_plugin_type="ZmqSender",
                                                                  address=NETWORK_ENDPOINTS["trigdec"],
                                                                  stype="msgpack")
                                           )
                 ),

                 ("ntoq_token", ntoq.Conf(msg_type="dunedaq::dfmessages::TriggerDecisionToken",
                                            msg_module_name="TriggerDecisionTokenNQ",
                                            receiver_config=nor.Conf(ipm_plugin_type="ZmqReceiver",
                                                                     address=NETWORK_ENDPOINTS["triginh"])
                                            )
                 ),

                ("ntoq_timesync", ntoq.Conf(msg_type="dunedaq::dfmessages::TimeSync",
                                           msg_module_name="TimeSyncNQ",
                                           receiver_config=nor.Conf(ipm_plugin_type="ZmqReceiver",
                                                                    address=NETWORK_ENDPOINTS["timesync"])
                                           )
                ),

                ("tde", tde.ConfParams(
                        links=[idx for idx in range(NUMBER_OF_DATA_PRODUCERS)],
                        min_links_in_request=NUMBER_OF_DATA_PRODUCERS,
                        max_links_in_request=NUMBER_OF_DATA_PRODUCERS,
                        min_readout_window_ticks=MIN_READOUT_WINDOW_TICKS,
                        max_readout_window_ticks=MAX_READOUT_WINDOW_TICKS,
                        trigger_window_offset=TRIGGER_WINDOW_OFFSET,
                        # The delay is set to put the trigger well within the latency buff
                        trigger_delay_ticks=TRIGGER_DELAY_TICKS,
                        # We divide the trigger interval by
                        # DATA_RATE_SLOWDOWN_FACTOR so the triggers are still
                        # emitted per (wall-clock) second, rather than being
                        # spaced out further
                        trigger_interval_ticks=TRG_INTERVAL_TICKS,
                        clock_frequency_hz=CLOCK_SPEED_HZ/DATA_RATE_SLOWDOWN_FACTOR,
                        initial_token_count=TOKEN_COUNT                    
                        )),
            ])

    startpars = rccmd.StartParams(run=RUN_NUMBER, disable_data_storage=False)
    cmd_data['start'] = acmd([
            ("qton_trigdec", startpars),
            ("ntoq_token", startpars),
            ("ntoq_timesync", startpars),
            ("tde", startpars),
        ])

    cmd_data['stop'] = acmd([
            ("qton_trigdec", None),
            ("ntoq_timesync", None),
            ("ntoq_token", None),
            ("tde", None),
        ])

    cmd_data['pause'] = acmd([
            ("", None)
        ])

    cmd_data['resume'] = acmd([
            ("tde", tde.ResumeParams(
                            trigger_interval_ticks=TRG_INTERVAL_TICKS
                        ))
        ])

    cmd_data['scrap'] = acmd([
            ("", None)
        ])

    return cmd_data
