from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient

from magenta.models.music_vae import configs
from magenta.models.music_vae.trained_model import TrainedModel

from IO import max_to_NN_to_max, max_str_to_midi_array, GROOVAE_2BAR_TAP_FIXED_VELOCITY

# ------------------ OSC IPs / ports ------------------ #
# connection parameters
IP = "192.168.235.19" 
receiving_from_pd_port = 5000
sending_to_pd_port = 1123

drum_voice_pitch_map = {"kick": 36, 'snare': 38, 'tom-1': 47, 'tom-2': 42, 'chat': 64, 'ohat': 63}
drum_voices = list(drum_voice_pitch_map.keys())

if __name__ == '__main__':

    # Lists for storing received values
    groove = ['0.0000 0.0300 120.0000 0.0625 0.0925 0.0000 0.1250 0.1550 0.0000 0.1875 0.2175 0.0000 0.2500 0.2800 120.0000 0.3125 0.3425 0.0000 0.3750 0.4050 0.0000 0.4375 0.4675 0.0000 0.5000 0.5300 120.0000 0.5625 0.5925 0.0000 0.6250 0.6550 0.0000 0.6875 0.7175 0.0000 0.7500 0.7800 120.0000 0.8125 0.8425 0.0000 0.8750 0.9050 0.0000 0.9375 0.9675 0.0000 1.0000 1.0300 120.0000 1.0625 1.0925 0.0000 1.1250 1.1550 0.0000 1.1875 1.2175 0.0000 1.2500 1.2800 120.0000 1.3125 1.3425 0.0000 1.3750 1.4050 0.0000 1.4375 1.4675 0.0000 1.5000 1.5300 120.0000 1.5625 1.5925 0.0000 1.6250 1.6550 0.0000 1.6875 1.7175 0.0000 1.7500 1.7800 120.0000 1.8125 1.8425 0.0000 1.8750 1.9050 0.0000 1.9375 1.9675 0.0000']
    BPM = [120]
    quitFlag = [False]

    # ------------------ OSC Receiver from Pd ------------------ #
    # create an instance of the osc_sender class above
    py_to_pd_OscSender = SimpleUDPClient(IP, sending_to_pd_port)
    # ---------------------------------------------------------- #

    # ------------------ OSC Receiver from Pd ------------------ #
    # dispatcher is used to assign a callback to a received osc message
    # in other words the dispatcher routes the osc message to the right action using the address provided
    dispatcher = Dispatcher()

    # define the handler for quit message message
    def quit_message_handler(address, *args):
        quitFlag[0] = True
        print("QUITTING!")

    def BPM_handler(address, *args):
        BPM[0] = args[0]

    # define the handler for messages starting with /slider/[slider_id]
    def groove_message_handler(address, *args):
        groove[0]=args[0]

    # pass the handlers to the dispatcher
    dispatcher.map("/bpm*", BPM_handler)
    dispatcher.map("/groove*", groove_message_handler)
    dispatcher.map("/quit*", quit_message_handler)

    # you can have a default_handler for messages that don't have dedicated handlers
    def default_handler(address, *args):
        print(f"No action taken for message {address}: {args}")
    dispatcher.set_default_handler(default_handler)

    # python-osc method for establishing the UDP communication with pd
    server = BlockingOSCUDPServer((IP, receiving_from_pd_port), dispatcher)
    # ---------------------------------------------------------- #

    # ------------------ NOTE GENERATION  ------------------ #
    # Load the model
    groovae_2bar_tap = TrainedModel(config=configs.CONFIG_MAP['groovae_2bar_tap_fixed_velocity'],
                                    batch_size=1,
                                    checkpoint_dir_or_path=GROOVAE_2BAR_TAP_FIXED_VELOCITY)      

    while (quitFlag[0] is False):
        server.handle_request()

        output=max_to_NN_to_max(groove[0], BPM[0], groovae_2bar_tap)

        # 3. Send Notes to pd (send pitch last to ensure syncing)
        #py_to_pd_OscSender.send_message("/gamelan/velocity_duration", (velocity, duration))
        #py_to_pd_OscSender.send_message("/gamelan/pitch", q_pitch)
#
        #py_to_pd_OscSender.send_message("/drum/velocity_duration", (velocity, duration))
        #py_to_pd_OscSender.send_message("/drum/pitch", drum_voice_pitch_map[drum_voice])     

    # ---------------------------------------------------------- #