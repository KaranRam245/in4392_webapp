import streamlit as st
from src.data import Glove
from src.data.Glove import Glove
from src.data import Tokenize
from src.models.ConvNet1D import ConvNet1D
from src.models.LSTMBuild import LSTMBuild
from tensorflow.keras.callbacks import ModelCheckpoint
from src.reporting.trainingplot import plot_training_results
import os

models_storage = os.path.join(os.curdir, 'models')
st.title("Inappropriate comment classification")

available_models = ['Conv 1D', 'LSTM']

st.sidebar.title("Model Settings")
selectedModel = st.sidebar.selectbox("Please select the model you would like to use",
                                     available_models)
showAdvancedOptions = st.sidebar.checkbox('Show Advanced Training Options', False)

if showAdvancedOptions:
    MAX_SEQUENCE_LENGTH = st.sidebar.slider("Max sequence length", 20, 100, 100)
    MAX_VOCAB_SIZE = st.sidebar.slider("Max Vocab Size", 10000, 20000, 10000)
    EMBEDDING_DIM = st.sidebar.selectbox("Embedding Dimension", [50, 100, 200, 300])
    VALIDATION_SPLIT = st.sidebar.slider("Validation Split", 0.1, 0.5, 0.2, 0.1)
    BATCH_SIZE = st.sidebar.slider("Batch Size", 16, 256, 128, 2)
    EPOCHS = st.sidebar.slider("Epochs", 1, 500, 10, 1)
    trainModel = st.sidebar.button("Train")
else:
    MAX_SEQUENCE_LENGTH = 100
    MAX_VOCAB_SIZE = 20000
    EMBEDDING_DIM = 100
    VALIDATION_SPLIT = 0.2
    BATCH_SIZE = 128
    EPOCHS = 1
    trainModel = st.sidebar.button("Train")

with st.spinner("Loading utilities..."):
    GloveObject = Glove(EMBEDDING_DIM=EMBEDDING_DIM)

if trainModel and selectedModel is 'Conv 1D':
    st.write(
        f"Model training with following parameters - Max sequence length: {MAX_SEQUENCE_LENGTH},Max Vocab Size: {MAX_VOCAB_SIZE}")

    trainingPath = os.path.join(os.curdir, 'src', 'data', 'train', 'train.csv')
    data, targets, word2idx = Tokenize.train_tokenizer(trainingPath, MAX_VOCAB_SIZE,
                                                       MAX_SEQUENCE_LENGTH)
    embedding_matrix = GloveObject.fillPretrainedEmbeddings(word2idx, MAX_VOCAB_SIZE)
    num_words = min(MAX_VOCAB_SIZE, len(word2idx) + 1)
    callbacks = [ModelCheckpoint(os.path.join(models_storage, 'Conv1D.h5'), monitor='val_acc',
                                 save_best_only=True)]
    model = ConvNet1D()
    model.set_pretrained_embeddings(num_words, EMBEDDING_DIM, embedding_matrix)

    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['acc'])
    history = model.fit(data, targets, batch_size=BATCH_SIZE, epochs=EPOCHS,
                        validation_split=VALIDATION_SPLIT, callbacks=callbacks)
    plot_training_results(history.history)

elif trainModel and selectedModel is 'LSTM':

    trainingPath = os.path.join(os.curdir, 'src', 'data', 'train', 'train.csv')
    data, targets, word2idx = Tokenize.train_tokenizer(trainingPath, MAX_VOCAB_SIZE,
                                                       MAX_SEQUENCE_LENGTH)
    embedding_matrix = GloveObject.fillPretrainedEmbeddings(word2idx, MAX_VOCAB_SIZE)
    num_words = min(MAX_VOCAB_SIZE, len(word2idx) + 1)
    callbacks = [ModelCheckpoint(os.path.join(models_storage, 'LSTM.h5'), monitor='val_acc',
                                 save_best_only=True)]
    model = LSTMBuild()
    model.set_pretrained_embeddings(num_words, EMBEDDING_DIM, embedding_matrix)

    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['acc'])
    history = model.fit(data, targets, batch_size=BATCH_SIZE, epochs=EPOCHS,
                        validation_split=VALIDATION_SPLIT)
    plot_training_results(history.history)
