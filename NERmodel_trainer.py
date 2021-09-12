import re
import random
import pickle
from pathlib import Path

# Import NLP libraries
import spacy
from spacy.training import Example
from spacy.language import Language
from spaczz.pipeline import SpaczzRuler


def remove_unicode(string):
    """
    Function to remove Unicode characters in a string.
    """
    string_unicode = string.replace('\xa0', ' ')
    string_encode = string_unicode.encode("utf-8", "xmlcharrefreplace")
    string_decode = string_encode.decode()
    return string_decode


def sent_generator(train_text, model):
    """
    This function generates a list of sentences in the training text data.
    """
    regex = re.compile(r'(\s+$)|([^\S]\n+)') # Match and remove empty sentences

    train_doc = model(remove_unicode(train_text))
    train_sent = set([sent.text for sent in train_doc.sents
                    if not regex.match(sent.text)])

    return train_sent


def add_pipe_SpaczzRuler(Labels, model):
    """
    This function adds the spaczz_ruler, which is a fuzzy matcher, to the NLP pipeline.

    Labels: DataFrame with 2 columns. The first columen is the NER label, and the 
        second column is the patern to be matched.
    model: spaCy nlp model
    """
    patterns = []

    for rec in Labels.to_records(index=False):
        label = {'label': rec[0], 
                'pattern': rec[1], 
                'type': 'fuzzy', 
                'kwargs': {'fuzzy_func': 'quick', 'min_r1': 70, 'min_r2': 90}}

        patterns.append(label)

    if 'ner' in model.pipe_names:
        spaczz_ruler = model.add_pipe("spaczz_ruler", after='ner')
    else:
        spaczz_ruler = SpaczzRuler(model)
    spaczz_ruler.add_patterns(patterns)

    return spaczz_ruler


class build_TrainData:

    def __init__(self, train_text, model=None):
        """
        Create training data in the format required to train a NER pipeline using spaCy.

        train_text: plain text data to be used for training a custom NER model
        model: spaCy language model
        """

        if model is not None:
            nlp = spacy.load(model)
            print(f"Loaded '{model}' model.")
        else:
            nlp = spacy.blank('en')

        if 'parser' in nlp.pipe_names:
            # Add a new rule for the start of a sentence to the pipeline
            @Language.component("sent_start_rule")
            def sent_start_rule(doc):
                for token in doc[:-1]:
                    if token.text.startswith('\n'):
                        doc[token.i+1].is_sent_start = True
                    elif token.text.startswith('\r\n'):
                        doc[token.i+1].is_sent_start = True
                return doc

            nlp.add_pipe('sent_start_rule', before='parser')

        self.model = nlp
        self.train_sents = sent_generator(train_text, nlp)


    def TrainData(self, labels, verbose=True, save_results=True):
        """
        This function creates the training data in the format required for SpaCy.
        
        labels: DataFrame with 2 columns. The first columen is the NER label, and the 
            second column is the patern to be matched.
        """

        # Add SpaczzRuler, fuzzy token matcher, to nlp pipeline
        if 'spaczz_ruler' not in self.model.pipe_names:
            spaczz_ruler = add_pipe_SpaczzRuler(labels, self.model)

        # Match labels to every sentence in the train_text
        Train_Data = []
        for n, sent in enumerate(self.train_sents):
            doc = self.model.make_doc(sent)
            doc = spaczz_ruler(doc)

            entities = [(ent.start_char, ent.end_char, ent.label_) for ent in doc.ents 
                        if ent.label_ in labels.iloc[:, 1].tolist()]

            if entities:
                inst = (sent, {'entities': entities})
                Train_Data.append(inst)

            if verbose:
                if n%50 == 0:
                    print(f'{n:4d} sentences processed; {len(Train_Data):4d} training samples saved.')

            if save_results:
                if n%50 == 0:
                    with open("NER_Train_Data.txt", "wb") as fp:
                        pickle.dump(Train_Data, fp)
                    
        if save_results:
            with open("NER_Train_Data.txt", "wb") as fp:
                pickle.dump(Train_Data, fp)

        self.train_data = Train_Data

        return Train_Data
        

def train_costume_NER(train_data, model=None, n_iter=50, batch=None, output_dir=None):
    """
    This function trains a custom NER using spaCy.

    train_data: custom entity training data for spaCy NER pipeline.
    model: spaCy language model
    n_iter (int): number of iterations the training data is passed through the model trainer.
    batch (int): number of training data instances to be passed in every interation of training.
    output_dir: path to save the trained model
    """
    if batch is None:
        batch = len(train_data)

    if model is not None:
        nlp = spacy.load(model)
        print(f"Loaded {model} model.")
    else:
        nlp = spacy.blank('en')
        print("Created blank 'en' model")

    # set up the pipeline
    if 'ner' not in nlp.pipe_names:
        Language.component("ner")
        nlp.add_pipe('ner', last=True)
        ner = nlp.get_pipe('ner')
    else:
        ner = nlp.get_pipe('ner')

    # Add labels to the NER
    for _, annotations in train_data:
        for ent in annotations.get('entities'):
            ner.add_label(ent[2])

    # Train the recognizer by disabling the unnecessary pipelines except for NER
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != 'ner']
    with nlp.disable_pipes(*other_pipes):  # only train NER
        if model is None:
            optimizer = nlp.begin_training()
        else:
            optimizer = nlp.create_optimizer()
        for iter in range(n_iter):
            random.shuffle(train_data)
            losses = {}
            for text, entity_offsets in random.sample(train_data, batch):
                doc = nlp.make_doc(text)
                example = Example.from_dict(doc, entity_offsets)
                nlp.update([example],
                        drop=0.5,
                        sgd=optimizer,
                        losses=losses)
            print(f'Iter: {iter+1} - losses: {losses}')

    # Save the model to directory
    if output_dir is not None:
        nlp.to_disk(Path(output_dir))
        print("Saved model to ", output_dir)

    return nlp