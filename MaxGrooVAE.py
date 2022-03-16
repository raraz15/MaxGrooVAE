# Adapted from https://github.com/behzadhaki/CMC_SMC

from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient

from magenta.models.music_vae.trained_model import TrainedModel

from IO import max_to_NN_to_max, model_weights_path, model_config

# connection parameters
RECEIVE_IP = "192.168.235.19"
SEND_IP="192.168.235.72"
receiving_from_pd_port = 5000
sending_to_pd_port = 6000


def BPM_groove_handler(address, *args):
    """Takes a space separated string, parses it to BPM, Groove and gets composes a drum loop."""
    print('Groove Received. Composing...')
    message=args[0].split(' ') # First value is the BPM, rest is the groove
    BPM[0]=float(message[0])
    groove[0]=' '.join(message[1:])
    # Get the NN composition
    NN_output=max_to_NN_to_max(groove[0], BPM[0], groovae_2bar_tap)
    # Flatten the array for sending to Max
    output[0]=[i for row in NN_output for i in row]
    # Send it to Max
    py_to_pd_OscSender.send_message("/pattern/0", output[0])
    print('Sent the Drum Composition.')

#def temperature_handler(address, *args):
#    T[0]=args[0]
#    print(f'Temperature change. Setting to: {T[0]}')

# define the handler for quit message message
def quit_message_handler(address, *args):
    quitFlag[0] = True
    print("QUITTING!")

def default_handler(address, *args):
    print(f"No action taken for message {address}: {args}")    


if __name__ == '__main__':

    # Lists for storing received values
    groove = ['0.0000 0.0300 120.0000 0.0625 0.0925 0.0000 0.1250 0.1550 0.0000 0.1875 0.2175 0.0000 0.2500 0.2800 120.0000 0.3125 0.3425 0.0000 0.3750 0.4050 0.0000 0.4375 0.4675 0.0000 0.5000 0.5300 120.0000 0.5625 0.5925 0.0000 0.6250 0.6550 0.0000 0.6875 0.7175 0.0000 0.7500 0.7800 120.0000 0.8125 0.8425 0.0000 0.8750 0.9050 0.0000 0.9375 0.9675 0.0000 1.0000 1.0300 120.0000 1.0625 1.0925 0.0000 1.1250 1.1550 0.0000 1.1875 1.2175 0.0000 1.2500 1.2800 120.0000 1.3125 1.3425 0.0000 1.3750 1.4050 0.0000 1.4375 1.4675 0.0000 1.5000 1.5300 120.0000 1.5625 1.5925 0.0000 1.6250 1.6550 0.0000 1.6875 1.7175 0.0000 1.7500 1.7800 120.0000 1.8125 1.8425 0.0000 1.8750 1.9050 0.0000 1.9375 1.9675 0.0000']
    BPM = [120]
    quitFlag = [False]
    output=[['0']*32]
    T=[1.0]

    # create an instance of the osc_sender class
    py_to_pd_OscSender = SimpleUDPClient(SEND_IP, sending_to_pd_port)

    # ------------------ OSC Receiver from Pd ------------------ #
    # dispatcher is used to assign a callback to a received osc message
    # in other words the dispatcher routes the osc message to the right action using the address provided
    dispatcher = Dispatcher()
    # pass the handlers to the dispatcher
    dispatcher.map("/groove*", BPM_groove_handler)
    #dispatcher.map("/temperature*", temperature_handler)
    dispatcher.map("/quit*", quit_message_handler)
    # default_handler for messages that don't have dedicated handlers
    dispatcher.set_default_handler(default_handler)
    # python-osc method for establishing the UDP communication with pd
    server = BlockingOSCUDPServer((RECEIVE_IP, receiving_from_pd_port), dispatcher)

    # ------------------ Neural Drum Composer ------------------- #
    # Load the model
    print('\nLoading the model...')
    groovae_2bar_tap = TrainedModel(config=model_config,
                                    batch_size=1,
                                    checkpoint_dir_or_path=model_weights_path)      
    print('Done!')
    print('Listening...\n')

    # ------------------- Communication - Processing ------------ #

    while (quitFlag[0] is False):
        server.handle_request()