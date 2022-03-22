# Adapted from https://github.com/behzadhaki/CMC_SMC
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient

from magenta.models.music_vae.trained_model import TrainedModel

from IO import max_to_NN_to_max, model_weights_path, model_config

N_COMPOSITIONS=4

# connection parameters
RECEIVE_IP =  "192.168.109.19"
SEND_IP= "192.168.109.72"
receiving_from_pd_port = 5000
sending_to_pd_port = 6500

DRUMS={36: 'Kick',
       38: 'Snare (Head)',
       42: 'HH Closed (Bow)',
       45: "Tom 2",
       46: 'HH Open (Bow)',
       48: "Tom 1",
       49: 'Crash 1 (Bow)',
       50: "Tom 1 (Rim)",
       51: "Ride (Bow)"
       }

def BPM_groove_handler(address, *args):
    """Takes a space separated string, parses it to BPM, Groove and composes a drum loop."""
    print('\nGroove Received with Temperature {:.2f}.\nComposing...'.format(T[0]))
    inp_message=args[0].split(' ') # First value is the BPM, rest is the groove
    BPM[0]=float(inp_message[0])
    groove[0]=' '.join(inp_message[1:]) # workaround osc
    # Get N_COMPOSITIONS drum compositions in Max readable format
    messages=max_to_NN_to_max(groove[0], BPM[0], groovae_2bar_tap, temperature=T[0], N=N_COMPOSITIONS)
    # Send to Max by /composition/drum/
    for i,msg in enumerate(messages):       
        for drum,max_str in msg.items():
            py_to_pd_OscSender.send_message(f"/pattern/{i}/{drum}", max_str) 
        print(f"{i}: {[DRUMS[n] for n in list(msg.keys())]}")
    print('Sent all the Compositions.')

def temperature_handler(address, *args):
    T[0]=args[0]
    #print(f'\nTemperature change. Setting to: {T[0]}')

# define the handler for quit message message
def quit_message_handler(address, *args):
    quitFlag[0] = True
    print("\nQUITTING!")

def default_handler(address, *args):
    print(f"\nNo action taken for message {address}: {args}")    

if __name__ == '__main__':

    # Lists for storing received values
    groove = ['0.0000 0.0300 120.0000 0.0625 0.0925 0.0000 0.1250 0.1550 0.0000 0.1875 0.2175 0.0000 0.2500 0.2800 120.0000 0.3125 0.3425 0.0000 0.3750 0.4050 0.0000 0.4375 0.4675 0.0000 0.5000 0.5300 120.0000 0.5625 0.5925 0.0000 0.6250 0.6550 0.0000 0.6875 0.7175 0.0000 0.7500 0.7800 120.0000 0.8125 0.8425 0.0000 0.8750 0.9050 0.0000 0.9375 0.9675 0.0000 1.0000 1.0300 120.0000 1.0625 1.0925 0.0000 1.1250 1.1550 0.0000 1.1875 1.2175 0.0000 1.2500 1.2800 120.0000 1.3125 1.3425 0.0000 1.3750 1.4050 0.0000 1.4375 1.4675 0.0000 1.5000 1.5300 120.0000 1.5625 1.5925 0.0000 1.6250 1.6550 0.0000 1.6875 1.7175 0.0000 1.7500 1.7800 120.0000 1.8125 1.8425 0.0000 1.8750 1.9050 0.0000 1.9375 1.9675 0.0000']
    BPM = [120]
    quitFlag = [False]
    output=[]
    T=[1.0]

    # create an instance of the osc_sender class
    py_to_pd_OscSender = SimpleUDPClient(SEND_IP, sending_to_pd_port)

    # ------------------ OSC Receiver from Pd ------------------ #
    # dispatcher is used to assign a callback to a received osc message
    # in other words the dispatcher routes the osc message to the right action using the address provided
    dispatcher = Dispatcher()
    # pass the handlers to the dispatcher
    dispatcher.map("/groove*", BPM_groove_handler)
    dispatcher.map("/temperature*", temperature_handler)
    dispatcher.map("/quit*", quit_message_handler)
    # default_handler for messages that don't have dedicated handlers
    dispatcher.set_default_handler(default_handler)
    # python-osc method for establishing the UDP communication with pd
    server = BlockingOSCUDPServer((RECEIVE_IP, receiving_from_pd_port), dispatcher)

    # ------------------ Neural Drum Composer ------------------- #
    # Load the model
    print('\nLoading the model...')
    groovae_2bar_tap = TrainedModel(config=model_config,
                                    batch_size=N_COMPOSITIONS,
                                    checkpoint_dir_or_path=model_weights_path)      
    print('Done!')
    print('Listening...')

    # ------------------- Communication - Processing ------------ #
    while (quitFlag[0] is False):
        server.handle_request()