import os
import pickle

import pandas as pd
from tensorflow.keras.preprocessing import text, sequence


def train_tokenizer(filePath, maxVocabSize, maxSequenceLength):
    train = pd.read_csv(filePath)
    sentences = train["comment_text"]
    possible_labels = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
    targets = train[possible_labels].values

    tokenizer = text.Tokenizer(num_words=maxVocabSize)
    tokenizer.fit_on_texts(sentences)
    sequences = tokenizer.texts_to_sequences(sentences)

    with open(os.path.join(os.curdir, 'models', f'tokenizer_{maxVocabSize}.pickle'),
              'wb') as handle:
        pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)

    data = sequence.pad_sequences(sequences, maxlen=maxSequenceLength)

    return data, targets, tokenizer.word_index


def tokenize_text(tokenizer_path, text):
    with open(tokenizer_path, 'rb') as handle:
        tokenizer = pickle.load(handle)
        sequences = tokenizer.texts_to_sequences(text)
        return sequence.pad_sequences(sequences, 100)
