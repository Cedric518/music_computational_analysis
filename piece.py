from importlib.resources import path
import xml.etree.ElementTree as ET
from music21 import converter, pitch
import warnings
from pprint import pprint
import pandas as pd


warnings.filterwarnings('ignore', message='Could not import wedge')

class Piece:
    def __init__(self, file_path):
        self.file_path = file_path
        self.root = self._get_root()
        self.score = self._get_score_with_voice()
        self.voices = self._get_voices()
        self.transpose = self._check_transpose()
        self.notes, self.measure_mark = self.get_notes()
        self.starting_point_suggestion = self.get_starting_point_suggestion()
        # self.R = self.get_R()


    def _get_root(self):
        return ET.parse(self.file_path).getroot()

        
    def _get_score_with_voice(self):
        for note in self.root.findall('.//note'):
            voice = note.find('voice').text
            footnote = ET.Element('footnote')
            footnote.text = voice
            note.insert(0, footnote)
            if note.find('footnote').text != note.find('voice').text:
                raise ValueError('footnote having different number than voice')
        text_with_footnote = ET.tostring(self.root, encoding='unicode')
        score = converter.parse(text_with_footnote, format='musicxml').toSoundingPitch()
        return score


    def _get_voices(self):
        voices = []
        for el in self.score.recurse().getElementsByClass(['Note', 'Chord']):
            part = el.getInstrument(returnDefault=False).partId
            voice = el.notes[0].editorial.footnotes[0].text if el.isChord else el.editorial.footnotes[0].text
            instrument = el.getInstrument(returnDefault=False).partName
            key = ((part, voice), {instrument})

            if key in voices:
                _, instrument_set = voices[voices.index(key)]
                instrument_set.add(instrument)
            else:
                voices.append(key)

        return voices

            
    def _check_transpose(self):
        transposes = []
        for part in self.root.findall('part'):
            transpose = part.find('.//transpose')
            if transpose is not None:
                transposes.append((
                    f'instrument: {self.root.find(f"part-list/score-part[@id='{part.get('id')}']").findtext('part-name')}',
                    f'semitone: {transpose.findtext('chromatic')}', 
                    f'octave: {transpose.findtext('octave-change')}')
                    )
        if transpose is None:
            transposes = ['there is no transposition info in the xml file, make sure isntruments are not transposed']
        return transposes

    #<part> is not required by xml, which is a problem for the categorization, so we check first.
    def missing_voice_counts(self):
        return {p.get('id'): sum(1 for n in p.iter('note') if n.find('voice') is None)
        for p in self.root.findall('part')}

    #this function takes the desired measure number can give dictionary where key indicates beat and notes as elements
    #third parameter being optional for debugging purposes if ever need to check single beat within the measure
    def _get_notes_in_measure(self, measure_number, beat=None):
            measure = {}
            # measure[-1] = ('pitch', 'midi number', 'pitchClass', 'measureNumber', 'offset', 'voice', 'part', 'instrument')
    
            #this gets all the notes in the measure and appends their name, measurenumber, offset, and voice number to the list.
            for note in self.score.recurse().getElementsByClass('Note'):
                if note.measureNumber == measure_number:
    
                    #('pitch', 'midi number', 'pitchClass', 'measureNumber', 'offset', ('part', 'voice'), 'instrument')
                    name_with_octave = note.nameWithOctave
                    midi_number = note.pitch.midi
                    pitch_class = note.pitch.pitchClass  
                    measureN = note.measureNumber
                    offset = note.offset
                    part = note.getInstrument(returnDefault=False).partId
                    voice = note.editorial.footnotes[0].text
                    key = (part, voice)
                    instrument = note.getInstrument(returnDefault=False).partName
    
                    item = (name_with_octave, midi_number, pitch_class, measureN, offset, key, instrument)
                    
                    measure.setdefault(offset, []).append(item)
                    #if there does not exist note.offset key in measure dictionary, then generate one; and a list where item is appened
                    #if there exist note.offset key in measure dictionary, then append the item into the list.
    
            # this does the same thing as above but takes the highest pitch in a chord
            for chord in self.score.recurse().getElementsByClass('Chord'):
                if chord.measureNumber == measure_number:
                    high_note = max(chord.pitches) #this give a pitch, not a note in music21
    
                    name_with_octave = high_note.nameWithOctave
                    midi_number = high_note.midi
                    pitch_class = high_note.pitchClass
                    measureN = chord.measureNumber
                    offset = chord.offset
                    part = chord.getInstrument(returnDefault=False).partId
                    voice = chord.notes[0].editorial.footnotes[0].text
                    key = (part, voice)
                    instrument = chord.getInstrument(returnDefault=False).partName
                    item = (name_with_octave, midi_number, pitch_class, measureN, offset, key, instrument)
                    measure.setdefault(offset, []).append(item)
    
            #sorts the dictionary by the key, as the key represents the beat
            measure = dict(sorted(measure.items()))
            # print(pprint.pprint(measure, indent=4))
            if beat is not None:
                return measure[beat]
            return measure
    
    #this function gives two return 1st. unmodified notes (midi number), NaN if no notes. in the format of pandas.DataFrame | 2nd measure_mark, a list that tells where each measure is located
    #NaN for no notes
    def get_notes(self):

        
        max_measure = max([int(c.get('number')) for c in self.root.findall('.//measure') if c.get('number').isdigit()])
        min_measure = min([int(c.get('number')) for c in self.root.findall('.//measure') if c.get('number').isdigit()])

        
        keys = {voice_part:n for n, (voice_part, _) in enumerate(self.voices)}
        measure_mark = {}
        columns = [voice_part for voice_part, _ in self.voices] #so column does not include set
        notes = []
        # notes.append([0] * len(self.voices))
        labels = []

        #per measure ->
        for measure in range(min_measure, max_measure+1):
            measure_mark[measure] = len(notes)
            #per offset ->
            for (offset, values) in self._get_notes_in_measure(measure).items():
                chords = [None for i in range(len(self.voices))] #the container for chords later
                #per notes in each offset
                for value in values:
                    chords[keys[value[5]]] = value[1]                 #value[5]= ('P1', '5') the key to the matching index of the list of notes in chord
                # print(f'MEASURE {measure}, OFFSET {offset}')
                # print(chords)
                notes.append(chords)
                labels.append((measure, offset))

        index = pd.MultiIndex.from_tuples(labels, names=['measure', 'offset'])
        notes= pd.DataFrame(notes, columns=columns, index=index)
        return notes, measure_mark

    def __repr__(self):
        return f'Piece({self.file_path!r}, {len(self.voices)} voices)' 

    #this method allows us to use object as a list to return notes in measure [k]
    def __getitem__(self, measure_number):
        return self._get_notes_in_measure(measure_number)

    #return the starting point (closet tonic to each voice)
    def get_starting_point_suggestion(self, d = 12):
        medians = self.notes.median()    #takes each (p1,1) and find median of each column after all the NaN was filled
        tonic = self.score.analyze('key').tonic.midi #analyze key gives most time
        tonics = [i*12 + (tonic % d) for i in range((200//d))]
        recommendations = []

        #this loop finds the closet tonic to each voice.
        for part, median in medians.items():
            closest_idx = (pd.Series(tonics) - median).abs().idxmin()
            recommendations.append((part, tonics[int(closest_idx)]))

        return recommendations

# returns data where each voice is transposed according to the starting point, if d is passed then return modded
    def get_R(self, starting_points):
        #the following creates a DataFrame with columns = ('P1', '1') and values = starting=points
        basepoints = pd.DataFrame([pitch.midi for pitch in starting_points.values()]).T
        basepoints.columns = list(starting_points.keys()) 

        #the data in this dataframe is midi number not, on the R.
        R_midi = pd.concat([basepoints, self.notes], ignore_index = False)

        #minus the start point so each point becomes relative to the origin
        R = (R_midi - R_midi.loc[0]).ffill()

        #debugging purpose, this prints nameWithOctaves for verification of notes!!
        #print('NOTES')
        # with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', 1000):
        #     print(R_midi.map(lambda m: pitch.Pitch(midi=int(m)).nameWithOctave, na_action='ignore'))
        
        return R

    def get_R_total(self, R):
        return R.sum(axis = 1, numeric_only = True).to_frame(name='total_movements')

    #this function gives the amount of loops each voice has
    def get_loops(self, R, d = 12):
        loops = pd.DataFrame()
        loops = R.where(abs(R) >= d, other = 0) // 12
        loops['total_loops'] = loops.sum(axis=1, numeric_only = True)
        return loops
        



'''
part = instrument
voice = voice within instrument, so for example, piano will most likely have two parts, so does violin

strategy to identify voicelines musically:
if same part and voice -> the same voice
if same part and different voice -> different voice
'''
