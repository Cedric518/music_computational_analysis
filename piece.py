from importlib.resources import path
from pathlib import Path
import xml.etree.ElementTree as ET
from fractions import Fraction
from music21 import converter
import warnings
warnings.filterwarnings('ignore', message='Could not import wedge')

class Piece:
    def __init__(self, file_path):
        self.file_path = file_path
        self.root = self._get_root()
        self.score = self._get_score_with_voice()
        self.voices = self._voice_count()
        self.transpose = self._check_transpose()
        self.R, self.measure_mark = self.get_R()

    def _get_root(self):
        return ET.parse(self.file_path).getroot()
        
    def _get_score_with_voice(self):
        root = self.root

        for note in root.findall('.//note'):
            voice = note.find('voice').text
            footnote = ET.Element('footnote')
            footnote.text = voice
            note.insert(0, footnote)
            if note.find('footnote').text != note.find('voice').text:
                raise ValueError('footnote having different number than voice')

        text_with_footnote = ET.tostring(root, encoding='unicode')
        score = converter.parse(text_with_footnote, format='musicxml').toSoundingPitch()
        return score

    def _voice_count(self):
        keys = []
        root = self.root
        parts = root.findall('part')
        for part in parts:
            voices = {n.findtext('voice', 'none') for n in part.iter('note') if n.find('rest') is None}
            keys += [(part.get('id'), v) for v in voices]
        return keys

    def _check_transpose(self):
        root = self.root
        transposes = []
        for part in root.findall('part'):
            transpose = part.find('.//transpose')
            if transpose is not None:
                transposes.append((
                    f'instrument: {root.find(f"part-list/score-part[@id='{part.get('id')}']").findtext('part-name')}',
                    f'semitone: {transpose.findtext('chromatic')}', 
                    f'octave: {transpose.findtext('octave-change')}')
                    )
        if transpose is None:
            transposes = ['there is no transposition info in the xml file, make sure isntruments are not transposed']
        return transposes

    #<part> is not required by xml, which is a problem for the categorization, so we check first.
    def missing_voice_counts(self):
        root = self.root
        return {p.get('id'): sum(1 for n in p.iter('note') if n.find('voice') is None)
        for p in root.findall('part')}

    #this function takes the desired measure number can give dictionary where key indicates beat and notes as elements
    #third parameter being optional for debugging purposes if ever need to check single beat within the measure
    def get_notes_in_measure(self, measure_number, beat=None):
            score = self.score
            measure = {}
            # measure[-1] = ('pitch', 'midi number', 'pitchClass', 'measureNumber', 'offset', 'voice', 'part', 'instrument')
    
            #this gets all the notes in the measure and appends their name, measurenumber, offset, and voice number to the list.
            for note in score.recurse().getElementsByClass('Note'):
                if note.measureNumber == measure_number:
    
                    #('pitch', 'midi number', 'pitchClass', 'measureNumber', 'offset', ('part', 'voice'), 'instrument')
                    pitch = note.nameWithOctave
                    midi_number = note.pitch.midi
                    pitch_class = note.pitch.pitchClass
                    measureN = note.measureNumber
                    offset = note.offset
                    part = note.getInstrument(returnDefault=False).partId
                    voice = note.editorial.footnotes[0].text
                    key = (part, voice)
                    instrument = note.getInstrument(returnDefault=False).partName
    
                    item = (pitch, midi_number, pitch_class, measureN, offset, key, instrument)
                    
                    measure.setdefault(offset, []).append(item)
                    #if there does not exist note.offset key in measure dictionary, then generate one; and a list where item is appened
                    #if there exist note.offset key in measure dictionary, then append the item into the list.
    
            # this does the same thing as above but takes the highest pitch in a chord
            for chord in score.recurse().getElementsByClass('Chord'):
                if chord.measureNumber == measure_number:
                    high_note = max(chord.pitches) #this give a pitch, not a note in music21
    
                    pitch = high_note.nameWithOctave
                    midi_number = high_note.midi
                    pitch_class = high_note.pitchClass
                    measureN = chord.measureNumber
                    offset = chord.offset
                    part = chord.getInstrument(returnDefault=False).partId
                    voice = chord.notes[0].editorial.footnotes[0].text
                    key = (part, voice)
                    instrument = chord.getInstrument(returnDefault=False).partName
                    item = (pitch, midi_number, pitch_class, measureN, offset, key, instrument)
                    measure.setdefault(offset, []).append(item)
    
            #sorts the dictionary by the key, as the key represents the beat
            measure = dict(sorted(measure.items()))
            # print(pprint.pprint(measure, indent=4))
            if beat is not None:
                return measure[beat]
            return measure
    
    #this function gives unmodified R
    def get_R(self):
        root = self.root
        voices = self.voices

        max_measure = max([int(c.get('number')) for c in root.findall('.//measure')])
        min_measure = min([int(c.get('number')) for c in root.findall('.//measure')])
        
        r = []
        r.append(voices)
        keys = {v:n for n, v in enumerate(voices)}
        measure_mark = {}
        #per measure ->
        for measure in range(min_measure, max_measure+1):
            measure_mark[measure] = len(r)
            #per offset ->
            for (offset, values) in self.get_notes_in_measure(measure).items():
                chords = [None for i in range(len(voices))] #the container for chords later
                #per notes in each offset
                for value in values:
                    chords[keys[value[5]]] = value[1]                 #value[5]= ('P1', '5') the key to the matching index of the list of notes in chord

                # print(f'MEASURE {measure}, OFFSET {offset}')
                # print(chords)
                r.append(chords)
        return r, measure_mark

    def __repr__(self):
        return f'Piece({self.file_path!r}, {len(self.voices)} voices)' 

    #this method allows us to use object as a list to return notes in measure [k]
    def __getitem__(self, measure_number):
        return self.get_notes_in_measure(measure_number)
'''
part = instrument
voice = voice within instrument, so for example, piano will most likely have two parts, so does violin

strategy to identify voicelines musically:
if same part and voice -> the same voice
if same part and different voice -> different voice
'''
