import os
import streamlit as st
import numpy as np

class Glove:

    def __init__(self,EMBEDDING_DIM):
        self.EMBEDDING_DIM=EMBEDDING_DIM
        self.GLOVESTORAGE=os.path.join(os.path.dirname(os.path.abspath(__file__)),'glove_embeddings')
        self.word2vec={}
        self.embedding_matrix=[]

    def _getEmbeddings(self):
        with open(os.path.join(self.GLOVESTORAGE,'glove.6B.%sd.txt' % self.EMBEDDING_DIM)) as f:
            for i,line in enumerate(f):
                values = line.split()
                word = values[0]
                vec = np.asarray(values[1:], dtype='float32')
                self.word2vec[word] = vec
    
    def fillPretrainedEmbeddings(self,word2idx,maxVocabSize):
        self._getEmbeddings()
        num_words = min(maxVocabSize, len(word2idx) + 1)
        self.embedding_matrix = np.zeros((num_words, self.EMBEDDING_DIM))
        for word, i in word2idx.items():
            if i < maxVocabSize:
                embedding_vector = self.word2vec.get(word)
                if embedding_vector is not None:
                    # words not found in embedding index will be all zeros.
                    self.embedding_matrix[i] = embedding_vector
        
        return self.embedding_matrix