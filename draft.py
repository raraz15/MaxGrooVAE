#dc_quantize = configs.CONFIG_MAP['groovae_2bar_humanize'].data_converter

# Calculate how far off the beat a note is
def get_offset(s, note_index):
    q_s = flatten_quantization(quantize(s))
    true_onset = s.notes[note_index].start_time
    quantized_onset = q_s.notes[note_index].start_time
    diff = quantized_onset - true_onset
    beat_length = 60. / s.tempos[0].qpm
    step_length = beat_length / 4#q_s.quantization_info.steps_per_quarter
    offset = diff/step_length
    return offset 

def preprocess_2bar(s):
    return dc_quantize.from_tensors(dc_quantize.to_tensors(s).outputs)[0]

# quick method for removing microtiming and velocity from a sequence
def get_quantized_2bar(s, velocity=0):
    new_s = dc_quantize.from_tensors(dc_quantize.to_tensors(s).inputs)[0]
    new_s = change_tempo(new_s, s.tempos[0].qpm)
    if velocity != 0:
        for n in new_s.notes:
            n.velocity = velocity
    return new_s

#def make_click_track(s):
#  last_note_time = max([n.start_time for n in s.notes])
#  beat_length = 60. / s.tempos[0].qpm 
#  i = 0
#  times = []
#  while i*beat_length < last_note_time:
#    times.append(i*beat_length)
#    i += 1
#  return librosa.clicks(times)

def combine_sequences(seqs):
  # assumes a list of 2 bar seqs with constant tempo
  for i, seq in enumerate(seqs):
    shift_amount = i*(60 / seqs[0].tempos[0].qpm * 4 * 2)
    if shift_amount > 0:
      seqs[i] = note_seq.sequences_lib.shift_sequence_times(seq, shift_amount)
  return note_seq.sequences_lib.concatenate_sequences(seqs)

def combine_sequences_with_lengths(sequences, lengths):
  seqs = copy.deepcopy(sequences)
  total_shift_amount = 0
  for i, seq in enumerate(seqs):
    if i == 0:
      shift_amount = 0
    else:
      shift_amount = lengths[i-1]
    total_shift_amount += shift_amount
    if total_shift_amount > 0:
      seqs[i] = note_seq.sequences_lib.shift_sequence_times(seq, total_shift_amount)
  combined_seq = music_pb2.NoteSequence()
  for i in range(len(seqs)):
    tempo = combined_seq.tempos.add()
    tempo.qpm = seqs[i].tempos[0].qpm
    tempo.time = sum(lengths[0:i-1])
    for note in seqs[i].notes:
      combined_seq.notes.extend([copy.deepcopy(note)])
  return combined_seq

# Allow encoding of a sequence that has no extracted examples
# by adding a quiet note after the desired length of time
def add_silent_note(note_sequence, num_bars):
  tempo = note_sequence.tempos[0].qpm
  length = 60/tempo * 4 * num_bars
  note_sequence.notes.add(
    instrument=9, pitch=42, velocity=0, start_time=length-0.02, 
    end_time=length-0.01, is_drum=True)
  
def get_bar_length(note_sequence):
    tempo = note_sequence.tempos[0].qpm
    return 60/tempo * 4

def sequence_is_shorter_than_full(note_sequence):
    return note_sequence.notes[-1].start_time < get_bar_length(note_sequence)