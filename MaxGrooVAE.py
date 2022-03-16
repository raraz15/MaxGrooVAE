from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient

from groovae_max import max_str_to_midi_array

# connection parameters
IP = "192.168.235.19" 
receiving_from_pd_port = 5000
sending_to_pd_port = 1123

drum_voice_pitch_map = {"kick": 36, 'snare': 38, 'tom-1': 47, 'tom-2': 42, 'chat': 64, 'ohat': 63}
drum_voices = list(drum_voice_pitch_map.keys())

if __name__ == '__main__':

    # Lists for storing received values
    #velocity = [0]
    #min_pitch = 40
    #max_pitch = 52
    #num_box_values = [min_pitch,max_pitch]
    #slider_values = [1 for _ in range(6)]
    groove = ['']
    BPM = ['0 5 120']
    quitFlag = [False]

    # ------------------ OSC IPs / ports ------------------ #


    # ----------------------------------------------------------

    # ------------------ OSC Receiver from Pd ------------------ #
    # create an instance of the osc_sender class above
    py_to_pd_OscSender = SimpleUDPClient(IP, sending_to_pd_port)
    # ---------------------------------------------------------- #

    # ------------------ OSC Receiver from Pd ------------------ #
    # dispatcher is used to assign a callback to a received osc message
    # in other words the dispatcher routes the osc message to the right action using the address provided
    dispatcher = Dispatcher()

    # define the handler for messages starting with /velocity]
    #def velocity_message_handler(address, *args):
    #    #print(f"Received velocity value {args[0]}")
    #    velocity[0] = args[0]

    # define the handler for quit message message
    def quit_message_handler(address, *args):
        quitFlag[0] = True
        print("QUITTING!")

    ## define handler for messages starting with /nbox/[nbox_id]
    #def num_box_message_handler(address, *args):
    #    #print(f"Received num_box_message value {args[0]}")
    #    nbox_id = address.split("/")[-1]
    #    num_box_values[int(float(nbox_id))] = args[0] 
#
    ## define the handler for messages starting with /slider/[slider_id]
    #def slider_message_handler(address, *args):
    #    slider_id = address.split("/")[-1]
    #    slider_values[int(float(slider_id))] = args[0]  
    # 

    def BPM_handler(address, *args):
        #nbox_id = address.split("/")[-1]
        #print(args[0])
        BPM[0] = args[0]

    # define the handler for messages starting with /slider/[slider_id]
    def groove_message_handler(address, *args):
        #print(args[0])
        groove[0]=args[0]
        #print(groove)

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

    while (quitFlag[0] is False):
        server.handle_request()

        midi_array=max_str_to_midi_array(groove[0], BPM[0])

        # 3. Send Notes to pd (send pitch last to ensure syncing)
        #py_to_pd_OscSender.send_message("/gamelan/velocity_duration", (velocity, duration))
        #py_to_pd_OscSender.send_message("/gamelan/pitch", q_pitch)
#
        #py_to_pd_OscSender.send_message("/drum/velocity_duration", (velocity, duration))
        #py_to_pd_OscSender.send_message("/drum/pitch", drum_voice_pitch_map[drum_voice])     

    # ---------------------------------------------------------- #