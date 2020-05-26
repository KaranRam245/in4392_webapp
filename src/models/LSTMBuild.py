
from tensorflow.keras import Model
from tensorflow.keras.layers import Embedding,Bidirectional,GlobalMaxPool1D,Dense,LSTM
from tensorflow.keras.activations import relu,sigmoid

class LSTMBuild(Model):

    def __init__(self):
        super(LSTMBuild,self).__init__()
        self.embedding=Embedding(10,1)
        self.BiLSTM1=Bidirectional(LSTM(15,return_sequences=True))
        self.globalMaxPool1=GlobalMaxPool1D()
        self.dense1=Dense(6,activation=sigmoid)
    
    def call(self,inputs): 
        x=self.embedding(inputs)
        x=self.BiLSTM1(x)
        x=self.globalMaxPool1(x)
        return self.dense1(x)
        

    
    def set_pretrained_embeddings(self,num_words,embeddingDim,weights,trainable=False):
        self.embedding=Embedding(num_words,embeddingDim,trainable=trainable,weights=[weights],embeddings_initializer=None)
