import time
import threading

#!pip install python-osc
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher

from magenta.models.music_vae import configs
from magenta.models.music_vae.trained_model import TrainedModel

from IO import max_to_NN_to_max, max_str_to_midi_array, GROOVAE_2BAR_TAP_FIXED_VELOCITY

# connection parameters
IP = "192.168.235.19" 
receiving_from_pd_port = 5000

class OscReceiver(threading.Thread):

    def __init__(self, ip, receive_from_port, quit_event, address_list, address_handler_list):
        """
        Constructor for OscReceiver CLASS

        :param ip:                      ip address that pd uses to send messages to python
        :param receive_from_port:       port  that pd uses to send messages to python
        :param quit_event:              a Threading.Event object, for finishing the receiving process
        :param address_list:            list of osc addresses that need to be assigned a specific handler
        :param address_handler_list:    the handlers for a received osc message
        """

        # we want the OscReceiver to run in a separate concurrent thread
        # hence it is a child instance of the threading.Thread class
        super(OscReceiver, self).__init__()

        # connection parameters
        self.ip = ip
        self.receiving_from_port = receive_from_port

        # dispatcher is used to assign a callback to a received osc message
        self.dispatcher = Dispatcher()

        # default handler
        def default_handler(address, *args):
            print(f"No action taken for message {address}: {args}")
        self.dispatcher.set_default_handler(default_handler)

        # assign each handler to it's corresponding message
        for ix, address in enumerate(address_list):
            self.dispatcher.map(address, address_handler_list[ix])

        # python-osc method for establishing the UDP communication with pd
        self.server = BlockingOSCUDPServer((self.ip, self.receiving_from_port), self.dispatcher)

        # used from outside the class/thread to signal finishing the process
        self.quit_event = quit_event

    def run(self):
        # When you start() an instance of the class, this method starts running
        print("running --- waiting for data")

        # Counter for the number messages are received
        count = 0

        # Keep waiting of osc messages (unless the you've quit the receiver)
        while not self.quit_event.is_set():

            # handle_request() waits until a new message is received
            # Messages are buffered! so if each loop takes a long time, messages will be stacked in the buffer
            # uncomment the sleep(1) line to see the impact of processing time
            self.server.handle_request()
            count = (count+1)                           # Increase counter
            #time.sleep(1)

    def get_ip(self):
        return self.ip

    def get_receiving_from_port(self):
        return self.receiving_from_port

    def get_server(self):
        return self.server

    def change_ip_port(self, ip, port):
        self.ip = ip
        self.receiving_from_port = port
        self.server = BlockingOSCUDPServer(self.ip, self.receiving_from_port)

if __name__ == '__main__':

    # Load the model
    groovae_2bar_tap = TrainedModel(config=configs.CONFIG_MAP['groovae_2bar_tap_fixed_velocity'],
                                    batch_size=1,
                                    checkpoint_dir_or_path=GROOVAE_2BAR_TAP_FIXED_VELOCITY) 

    # used to quit osc_receiver
    quit_event = threading.Event()

    ##################################################################
    ##################################################################
    ########### OSC MESSAGE HANDLERS #################################
    ##################################################################
    ##################################################################
    #  Values received from sliders or numboxes will be stored/updated
    #       in the dedicated lists: slider_values and num_box_values
    #       if you need more than 10 sliders, increase the length of
    #       the default lists in lines 96-98
    #
    #  The methods slider_message_handler and num_box_message_handler
    #       are in charge of updating the slider_values and num_box_values
    #       lists using the corresponding received osc messages
    
    # Lists for storing received values
    groove = ['']
    BPM = ['0 5 120']
    quitFlag = [False]

    # dispatcher is used to assign a callback to a received osc message
    # in other words the dispatcher routes the osc message to the right action using the address provided
    #dispatcher = Dispatcher()

    # define the handler for quit message message
    def quit_message_handler(address, *args):
        quitFlag[0] = True
        print("QUITTING!")

    def BPM_handler(address, *args):
        BPM[0] = args[0]

    # define the handler for messages starting with /slider/[slider_id]
    def groove_message_handler(address, *args):
        groove[0]=args[0]

    # Creat an OscReceiver instance using the above params and handlers
    address_list = ["/bpm*", "/groove*", "/quit*"]
    address_handler_list = [BPM_handler, groove_message_handler, quit_message_handler]
    osc_receiver_from_pd = OscReceiver(ip=IP, receive_from_port=receiving_from_pd_port, quit_event=quit_event,
                                       address_list=address_list, address_handler_list=address_handler_list)

    osc_receiver_from_pd.start()

    while (quitFlag[0] is False):
        time.sleep(1)
        
        midi_array=max_str_to_midi_array(groove[0], BPM[0])
        print(midi_array)        
        #print("sliders: ", slider_values, "nbox: ", num_box_values)

    # Note: after setting the quit_event, at least one message should be received for quitting to happen
    quit_event.set()
