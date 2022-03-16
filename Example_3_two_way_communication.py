import random

from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient

from magenta.models.music_vae.trained_model import TrainedModel

from groovae_max import *

# connection parameters
ip = "127.0.0.1"
receiving_from_pd_port = 1415
sending_to_pd_port = 1123

drum_voice_pitch_map = {"kick": 36, 'snare': 38, 'tom-1': 47, 'tom-2': 42, 'chat': 64, 'ohat': 63}
drum_voices = list(drum_voice_pitch_map.keys())

if __name__ == '__main__':

    # Lists for storing received values
    velocity = [0]
    quitFlag = [False]

    # ------------------ OSC Receiver from Pd ------------------ #
    # create an instance of the osc_sender class above
    py_to_pd_OscSender = SimpleUDPClient(ip, sending_to_pd_port)
    # ---------------------------------------------------------- #

    # ------------------ OSC Receiver from Pd ------------------ #
    # dispatcher is used to assign a callback to a received osc message
    # in other words the dispatcher routes the osc message to the right action using the address provided
    dispatcher = Dispatcher()

    # define the handler for messages starting with /velocity]
    def velocity_message_handler(address, *args):
        velocity[0] = args[0]

    # define the handler for quit message message
    def quit_message_handler(address, *args):
        quitFlag[0] = True
        print("QUITTING!")

    # pass the handlers to the dispatcher
    dispatcher.map("/velocity*", velocity_message_handler)
    dispatcher.map("/quit*", quit_message_handler)

    # you can have a default_handler for messages that don't have dedicated handlers
    def default_handler(address, *args):
        print(f"No action taken for message {address}: {args}")
    dispatcher.set_default_handler(default_handler)

    # python-osc method for establishing the UDP communication with pd
    server = BlockingOSCUDPServer((ip, receiving_from_pd_port), dispatcher)
    # ---------------------------------------------------------- #

    # ------------------ NOTE GENERATION  ------------------ #
    # Load the model
    groovae_2bar_tap = TrainedModel(config=configs.CONFIG_MAP['groovae_2bar_tap_fixed_velocity'],
                                    batch_size=1,
                                    checkpoint_dir_or_path=GROOVAE_2BAR_TAP_FIXED_VELOCITY)    
    
    while (quitFlag[0] is False):
        server.handle_request()




        #max_array=max_to_NN_to_max(max_lst, BPM, model)

        # 1. generate a random pitched note with the provided received value
        pitch = int(random.randrange(40, 52))       # 1 octave
        vel = velocity[0]
        duration = int(random.randrange(0, 1000))

        # 2. select a random drum voice
        drum_voice = drum_voices[random.randint(0, 5)]

        # 3. Send Notes to pd (send pitch last to ensure syncing)
        py_to_pd_OscSender.send_message("/gamelan/velocity_duration", (velocity, duration))
        py_to_pd_OscSender.send_message("/gamelan/pitch", pitch)

        py_to_pd_OscSender.send_message("/drum/velocity_duration", (velocity, duration))
        py_to_pd_OscSender.send_message("/drum/pitch", drum_voice_pitch_map[drum_voice])

    # ---------------------------------------------------------- #