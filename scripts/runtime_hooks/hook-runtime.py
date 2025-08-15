import os
import sys

def spacy_hook():
    # Add the model directory to sys.path if it's not there
    for module in ['en_core_web_md', 'en_core_sci_md', 'en_ner_bc5cdr_md']:
        model_dir = os.path.join(sys._MEIPASS, module)
        if model_dir not in sys.path:
            sys.path.insert(0, model_dir)


spacy_hook()