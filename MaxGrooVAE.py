# Adapted from https://github.com/behzadhaki/CMC_SMC
import argparse
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient

from magenta.models.music_vae.trained_model import TrainedModel

from IO import max_to_NN_to_max, model_weights_path, model_config

# Lists for storing values
GROOVE = ['']
BPM=[120.0] 
quitFlag=[False]
T=[1.0] # Temperature
N_COMPOSITIONS=4 # Get N_COMPOSITIONS at a time

# Default connection parameters
RECEIVE_IP="192.168.109.19"
SEND_IP="192.168.109.72"
receiving_from_pd_port=5000
sending_to_pd_port=8000

# DRUM dict from https://magenta.tensorflow.org/datasets/groove
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
    print('\nGroove Received with Temperature {:.1f}.\nComposing...'.format(T[0]))
    inp_message=args[0].split(' ') # First value is the BPM, rest is the groove
    BPM[0]=float(inp_message[0])
    GROOVE[0]=' '.join(inp_message[1:]) # workaround osc
    # Get N_COMPOSITIONS drum compositions in Max readable format
    messages=max_to_NN_to_max(GROOVE[0], BPM[0], groovae_2bar_tap, temperature=T[0], N=N_COMPOSITIONS)
    # Send to Max by /pattern/drum/
    for i,msg in enumerate(messages):       
        for drum,max_str in msg.items():
            py_to_pd_OscSender.send_message(f"/pattern/{i}/{drum}", max_str) 
        print(f"{i}: {[DRUMS[n] for n in list(msg.keys())]}")
    py_to_pd_OscSender.send_message("/flag", 1) # Let Max know the transmission is complete
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

    parser = argparse.ArgumentParser()
    parser.add_argument('--send-ip', default=SEND_IP, type=str, help="Send IP.")
    parser.add_argument('--receive-ip', default=RECEIVE_IP, type=str, help="Receive IP.")
    parser.add_argument('--send-port', default=sending_to_pd_port, type=int, help="Send port for OSC.")
    parser.add_argument('--receive-port', default=receiving_from_pd_port, type=int, help="Send port for OSC.")
    args=parser.parse_args()

    # ------------------ OSC Sender to Max ---------------------- #
    py_to_pd_OscSender = SimpleUDPClient(args.send_ip, args.send_port)

    # ------------------ OSC Receiver from Max ------------------ #
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
    server = BlockingOSCUDPServer((args.receive_ip, args.receive_port), dispatcher)

    # ------------------ Neural Drum Composer ------------------- #
    # Load the model
    print('\nLoading the model...')
    groovae_2bar_tap = TrainedModel(config=model_config,
                                    batch_size=N_COMPOSITIONS,
                                    checkpoint_dir_or_path=model_weights_path)      
    print('Done!')
    print('Listening...')
    print(f'   Send IP: {args.send_ip} Port: {args.send_port}')
    print(f'Receive IP: {args.receive_ip} Port: {args.receive_port}')

    # ------------------- Communication - Processing ------------ #
    while (quitFlag[0] is False):
        server.handle_request()