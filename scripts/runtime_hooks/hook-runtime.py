import os
import sys

def spacy_hook():
    # Add the model directory to sys.path if it's not there
    model_dir = os.path.join(sys._MEIPASS, 'en_core_web_md')
    if model_dir not in sys.path:
        sys.path.insert(0, model_dir)

spacy_hook()