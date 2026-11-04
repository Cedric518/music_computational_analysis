from importlib.resources import path
from pathlib import Path
import xml.etree.ElementTree as ET
from fractions import Fraction
from music21 import converter, stream
import pprint

STEP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

ROOT = Path(__file__).resolve().parent
file_path = ROOT / 'music_sheets' / 'intermezzo.xml'
file_path2 = ROOT / 'music_sheets' / 'ravel_concerto.xml'
file_path3 = ROOT / 'music_sheets' / 'd_major_fugue.xml'
score = converter.parse(file_path).stripTies()
# print(score.parts[1].measure(2).show('text'))
test = score.parts[1].measure(1)

def get_score(file_path):
    return converter.parse(file_path).stripTies()

#<part> is not required by xml, which is a problem for the categorization, so we check first.
def missing_voice_counts(file_path):
    root = ET.parse(file_path).getroot()
    return {p.get('id'): sum(1 for n in p.iter('note') if n.find('voice') is None)
            for p in root.findall('part')}

#this function looks into the .xml file and counts the number of voices in the score. It does this by looking for the 'part' elements in the xml tree, which represent different voices or instruments in the score. The function then prints out the attributes of each part, which can include information such as the instrument name and id.
def voice_count(file_path):
    keys = []
    root = ET.parse(file_path).getroot() #reads the whole file into a tree
    parts = root.findall('part')
    for part in parts:
        voices = {n.findtext('voice', 'none') for n in part.iter('note') if n.find('rest') is None}
        keys += [(part.get('id'), v) for v in voices]
    return keys, part

def get_R(file_path, keys):
    score = get_score(file_path)
    data = []
    print('notes')
    print(score.parts[1].measure(2).show('text'))
    print('RECURSE')
    print(score.parts[0].measure(1).recurse().show('text'))
    print('NOT RECURSE')
    for i in score.parts[0].measure(1).voices[1].notes:
        print(i)


def get_notes_in_measure(file_path, measure_number):
    score = get_score(file_path)
    measure = {}
    print('===Notes===')
    #this gets all the notes in the measure and appends their name, measurenumber, offset, and voice number to the list.
    for note in score.recurse().getElementsByClass('Note'):
        if note.measureNumber == measure_number:
            #('pitch', 'midi number', 'pitchClass', 'measureNumber', 'offset', 'voice')
            item = (note.nameWithOctave, note.pitch.midi, note.pitch.pitchClass, note.measureNumber, note.offset, note.activeSite.id) if isinstance(note.activeSite, stream.Voice) else (note.nameWithOctave, note.pitch.midi, note.pitch.pitchClass, note.measureNumber, note.offset, 'no voice')
            measure.setdefault(note.offset, []).append(item)
            #if there does not exist note.offset key in measure dictionary, then generate one; and a list where item is appened
            #if there exist note.offset key in measure dictionary, then append the item into the list.

    print('===Chord===')
    # this does the same thing as above but takes the highest pitch in a chord
    for chord in score.recurse().getElementsByClass('Chord'):
        if chord.measureNumber == measure_number:
            high_note = max(chord.pitches) #this give a pitch, not a note in music21
            item = (high_note.nameWithOctave, high_note.midi, high_note.pitchClass, chord.quarterLength, chord.offset, chord.activeSite.id) if isinstance(chord.activeSite, stream.Voice) else (high_note.nameWithOctave, high_note.midi, high_note.pitchClass, chord.quarterLength, chord.offset, 'no voice')
            measure.setdefault(note.offset, []).append(item)

    measure = dict(sorted(measure.items()))
    print(pprint.pprint(measure, indent=4))
    return measure
   

    

get_notes_in_measure(file_path, 2)