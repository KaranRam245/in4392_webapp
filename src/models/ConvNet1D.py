from tensorflow.keras import Model
from tensorflow.keras.layers import Embedding, Conv1D, MaxPool1D, GlobalMaxPool1D, Dense
from tensorflow.keras.activations import relu, sigmoid


class ConvNet1D(Model):

    def __init__(self):
        super(ConvNet1D, self).__init__()
        self.embedding = Embedding(10, 1)
        self.conv1 = Conv1D(128, 3, activation=relu)
        self.maxPool1 = MaxPool1D(3)
        self.conv2 = Conv1D(128, 3, activation=relu)
        self.maxPool2 = MaxPool1D(3)
        self.conv2 = Conv1D(128, 3, activation=relu)
        self.globalMaxPool1 = GlobalMaxPool1D()
        self.dense1 = Dense(128, activation=relu)
        self.dense2 = Dense(6, activation=sigmoid)

    def call(self, inputs):
        x = self.embedding(inputs)
        x = self.conv1(x)
        x = self.maxPool1(x)
        x = self.conv2(x)
        x = self.maxPool2(x)
        x = self.conv2(x)
        x = self.globalMaxPool1(x)
        x = self.dense1(x)
        return self.dense2(x)

    def set_pretrained_embeddings(self, num_words, embeddingDim, weights, trainable=False):
        self.embedding = Embedding(num_words, embeddingDim, trainable=trainable, weights=[weights],
                                   embeddings_initializer=None)
