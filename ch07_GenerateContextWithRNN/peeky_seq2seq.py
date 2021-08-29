import sys
sys.path.append("/Users/inoueshinichi/Desktop/DeepLearning2_NLP") # 親ディレクトリのファイルをインポートするための設定
sys.path.append("/home/inoue/MyGithub/DeepLearning2_NLP")

from common.time_layers import TimeEmbedding, TimeLSTM, TimeAffine, TimeSoftmaxWithLoss
from common.base_model import BaseModel
from seq2seq import Seq2seq, Encoder

import numpy as np


class PeekyDecoder:
    def __init__(self, vocab_size, wordvec_size, hidden_size):
        V, D, H = vocab_size, wordvec_size, hidden_size
        rn = np.random.randn

        embed_W = rn(V, D) / 100
        lstm_Wx = rn(H + D, 4 * H) / np.sqrt(H + D)
        lstm_Wh = rn(H, 4 * H) / np.sqrt(H)
        lstm_b  = rn(4 * H)
        affine_W = rn(H + H, V) / np.sqrt(H + H)
        affine_b = np.zeros(V, dtype=np.float32)

        self.embed = TimeEmbedding(embed_W)
        self.lstm = TimeLSTM(lstm_Wx, lstm_Wh, lstm_b, statefull = True)
        self.affine = TimeAffine(affine_W, affine_b)

        self.params, self.grads = [], []
        for layer in (self.embed, self.lstm, self.affine):
            self.params += layer.params
            self.grads += layer.grads
        self.cache = None

    
    def forward(self, xs, h):
        N, T = xs.shape
        N, H = h.shape

        self.lstm.set_state(h)

        out = self.embed.forward(xs)

        # TimeLSTMへの入力を拡張する
        hs = np.repeat(h, T, axis=0).reshape(N, T, H)
        out = np.concatenate((hs, out), axis=2) # (N, T, H + D)

        # TimeAffineへの入力を拡張する
        out = self.lstm.forward(out)
        out = np.concatenate((hs, out), axis=2)
    
        score = self.affine.foward(out)
        self.cache = H
        return score

    
    def backward(self, dscore):
        H = self.cache

        dout = self.affine.backward(dscore)
        dout, dhs0 = dout[:, :, H:], dout[:, :, :H]
        dout = self.lstm.backward(dout)
        dembed, dhs1 = dout[:, :, H:], dout[:, :, :H]
        self.embed.backward(dembed)

        dhs = dhs0 + dhs1
        dh = self.lstm.dh + np.sum(dhs, axis=1) # 時間方向に集約
        return dh


    def generate(self, h, start_id, sample_size):
        sampled = []
        char_id = start_id
        self.lstm.set_state(h)

        H = h.shape[1]
        peeky_h = h.reshape(1, 1, H)
        for _ in range(sample_size):
            x = np.array([char_id]).reshape((1, 1))
            out = self.embed.forward(x)

            out = np.concatenate((peeky_h, out), axis=2)
            out = self.lstm.forward(out)
            out = np.concatenate((peeky_h, out), axis=2)
            score = self.affine.forward(out)

            char_id = np.argmax(score.flatten())
            sampled.append(char_id)

        return sampled


class PeekySeq2seq(Seq2seq):
    def __init__(self, vocab_size, wordvec_size, hidden_size):
        V, D, H = vocab_size, wordvec_size, hidden_size
        self.encoder = Encoder(V, D, H)
        self.decoder = PeekyDecoder(V, D, H)
        self.softmax = TimeSoftmaxWithLoss()

        self.params = self.encoder.params + self.decoder.params
        self.grads  =self.encoder.grads + self.decoder.grads

        