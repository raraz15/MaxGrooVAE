import copy
from collections import defaultdict

import numpy as np

import note_seq
from note_seq.protobuf import music_pb2

from magenta.models.music_vae import configs

dc_tap = configs.CONFIG_MAP['groovae_2bar_tap_fixed_velocity'].data_converter
model_config=configs.CONFIG_MAP['groovae_2bar_tap_fixed_velocity']
model_weights_path="groovae_2bar_tap_fixed_velocity.tar"

N_BARS=2
BEATS_PER_BAR=4
STEPS_PER_QUARTER_NOTE=4
N_STEPS=N_BARS*BEATS_PER_BAR*STEPS_PER_QUARTER_NOTE
VELOCITY=85 # Fixed Value

# If a sequence has notes at time before 0.0, scootch them up to 0
def start_notes_at_0(s):
    for n in s.notes:
        if n.start_time < 0:
            n.end_time -= n.start_time
            n.start_time = 0
    return s

# Some midi files come by default from different instrument channels
# Quick and dirty way to set midi files to be recognized as drums
def set_to_drums(ns):
    for n in ns.notes:
        n.instrument=9
        n.is_drum = True
        
# quickly change the tempo of a midi sequence and adjust all notes
def change_tempo(note_sequence, new_tempo):
    new_sequence = copy.deepcopy(note_sequence)
    ratio = note_sequence.tempos[0].qpm / new_tempo
    for note in new_sequence.notes:
        note.start_time = note.start_time * ratio
        note.end_time = note.end_time * ratio
    new_sequence.tempos[0].qpm = new_tempo
    return new_sequence

# Calculate quantization steps but do not remove microtiming
def quantize(s, steps_per_quarter=4):
    s_=copy.deepcopy(s)
    return note_seq.sequences_lib.quantize_note_sequence(s_,steps_per_quarter)

# Destructively quantize a midi sequence
def flatten_quantization(s):
    beat_length = 60. / s.tempos[0].qpm
    step_length = beat_length / 4 #s.quantization_info.steps_per_quarter
    new_s = copy.deepcopy(s)
    for note in new_s.notes:
        note.start_time = step_length * note.quantized_start_step
        note.end_time = step_length * note.quantized_end_step
    return new_s    

def add_silent_note(note_sequence, num_bars):
    tempo = note_sequence.tempos[0].qpm
    length = 60/tempo * 4 * num_bars
    note_sequence.notes.add(
        instrument=9, pitch=42, velocity=0, start_time=length-0.02, 
        end_time=length-0.01, is_drum=True)

def is_4_4(s):
    ts = s.time_signatures[0]
    return (ts.numerator == 4 and ts.denominator ==4)

def quantize_to_beat_divisions(beat, division=32):
    """Quantize a floating point beat? to a 1/division'th beat"""
    if division!=1: 
        return (beat//(1/division))*(1/division)
    else: # do not quantize
        return beat    


# quick method for turning a drumbeat into a tapped rhythm
def get_tapped_2bar(s, velocity=VELOCITY, ride=False):
    new_s = dc_tap.from_tensors(dc_tap.to_tensors(s).inputs)[0]
    new_s = change_tempo(new_s, s.tempos[0].qpm)
    if velocity != 0:
        for n in new_s.notes:
            n.velocity = velocity
    if ride:
        for n in new_s.notes:
            n.pitch = 42
    return new_s

def drumify(s, model, temperature=0.5):
    encoding, mu, sigma = model.encode([s])
    decoded = model.decode(encoding, length=N_STEPS, temperature=temperature)
    return decoded[0]    

def max_str_to_midi_array(max_str, BPM):
    """max_list timing are in bars. Assumes 4/4 timing"""
    max_str=max_str.split(' ')
    assert len(max_str)==3*N_STEPS, 'List length wrong!'
    beat_dur=60/BPM # in sec
    midi_array=[]
    for i in range((len(max_str)//3)):
        start_step=4*float(max_str[3*i]) # in beats
        end_step=4*float(max_str[3*i+1]) # in beats
        vel=float(max_str[3*i+2])
        start_time=start_step*beat_dur
        end_time=end_step*beat_dur
        midi_array.append([start_time,end_time,vel])
    return np.array(midi_array)

def make_tap_sequence(midi_array, BPM, velocity=VELOCITY, tpq=220):
    """Creates a NoteSequence object from a midi_array."""
    note_sequence=music_pb2.NoteSequence()
    note_sequence.tempos.add(qpm=BPM)
    note_sequence.ticks_per_quarter=tpq
    note_sequence.time_signatures.add(numerator=BEATS_PER_BAR, denominator=4)
    note_sequence.key_signatures.add()
    for onset_time, offset_time, onset_velocity in midi_array:
        if onset_velocity: # Non-zero velocity notes only
            note_sequence.notes.add(instrument=9, # Drum MIDI Program number
                                    pitch=42, # Constant
                                    is_drum=True,
                                    velocity=velocity,
                                    start_time=onset_time,
                                    end_time=offset_time)
    note_sequence.total_time=N_BARS*BEATS_PER_BAR*(60/BPM)
    return note_sequence 

def NN_output_to_Max(h, BPM, pre_quantization=False, beat_quantization_division=1):
    """Return in [start_beat, duration_in_beats, velocity, pitch]"""
    _h=copy.deepcopy(h)
    beat_dur=60/BPM
    if pre_quantization:
        _h=quantize(_h)
    midi_arrays=defaultdict(lambda: np.zeros(N_BARS*BEATS_PER_BAR*1000)) # embed the velocities
    for note in _h.notes:
        start_beat=quantize_to_beat_divisions(note.start_time/beat_dur, beat_quantization_division)
        end_beat=quantize_to_beat_divisions(note.end_time/beat_dur, beat_quantization_division)      
        start=int(start_beat*1000)
        end=int(end_beat*1000)
        midi_arrays[note.pitch][start:end]=note.velocity
    messages={drum: ' '.join([str(v) for v in array]) for drum,array in midi_arrays.items()} # Cast it to str for Max
    return messages

# TODO: take beat_quantization_division 
def max_to_NN_to_max(max_lst, BPM, model, temperature=1.0, beat_quantization_division=64):
    """takes a max list, gets NN output and puts it in Max readable format."""
    # List to array
    midi_array=max_str_to_midi_array(max_lst, BPM)
    # Convert it into the pre-NN input format
    note_sequence=make_tap_sequence(midi_array, BPM)
    note_sequence=quantize(note_sequence)
    set_to_drums(note_sequence)
    # Convert to NN input format
    note_sequence=start_notes_at_0(note_sequence)
    note_sequence=change_tempo(get_tapped_2bar(note_sequence, velocity=VELOCITY, ride=True), BPM)
    assert BPM==note_sequence.tempos[0].qpm, 'Tempo conversion failed at tapped bar creation'
    # Get NN prediction
    h=change_tempo(drumify(note_sequence, model, temperature=temperature), BPM)
    assert BPM==h.tempos[0].qpm, 'Tempo conversion failed at NN creation'
    # Convert to Max array
    MAX_array=NN_output_to_Max(h, BPM, beat_quantization_division=beat_quantization_division)
    return MAX_array      