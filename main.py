from pathlib import Path
from piece import Piece
from music21 import pitch, exceptions21
import pprint
import pandas as pd

ROOT = Path(__file__).resolve().parent

file_path1 = ROOT / 'music_sheets' / 'd_major_fugue.xml'
file_path2 = ROOT / 'music_sheets' / 'intermezzo.xml'
file_path3 = ROOT / 'music_sheets' / 'ravel_concerto.xml'

fugue = Piece(file_path3)
print(fugue.notes)

suggestions = fugue.get_key_suggestion()

def ask_starting_points(suggestions):
    starting_points = {}
    print('input midi number or pitch name with octave for starting point: \n part | enter for default (suggested by software)')
    for (instrument_number, part), suggestion in suggestions:
        while True:
            #accept user input, default to suggestion (press enter)
            answer = input(f'{instrument_number, part} | [{pitch.Pitch(suggestion)}|{suggestion}]: ').strip() or str(suggestion)

            try:
                #handles the problem that user inputs are always string
                #isdigit() accepts positive integers
                if answer.isdigit():
                    if 12 <= int(answer) <= 127:
                        suggest_pitch_object = pitch.Pitch(int(answer))
                    else:
                        raise ValueError('midi number needs to be between 12 and 127')
                else:
                    suggest_pitch_object = pitch.Pitch(answer) #raise PitchException if not a pitch
                    if suggest_pitch_object.octave == None:
                        raise ValueError('input should be either nameWithOctave or midi number, i.e. D#4 or 63')
                    
                starting_points[(instrument_number, part)] = suggest_pitch_object

            except exceptions21.Music21Exception as e:
                print(' ', e)
                print('input should be either nameWithOctave or midi number, i.e. D#4 or 63')
                continue

            except ValueError as e:
                print(' ', e)
                continue

            break
    pprint.pprint(starting_points)
            
ask_starting_points(suggestions)




