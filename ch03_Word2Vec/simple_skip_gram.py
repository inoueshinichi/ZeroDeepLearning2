import sys
sys.path.append("/Users/inoueshinichi/Desktop/MyGithub/DeepLearning2_NLP") # 親ディレクトリのファイルをインポートするための設定
sys.path.append("/home/inoue/MyGithub/DeepLearning2_NLP")

import numpy as np
from common.layers import MatMul, Softmax, SoftmaxWithLoss


class SimpleSkipGram:

    def __init__(self, vocab_size, hidden_size):
        V, H = vocab_size, hidden_size

        # 重み
        W_in = 0.01 * np.random.randn(V, H).astype('f')
        W_out = 0.01 * np.random.randn(H, V).astype('f')

        # レイヤの生成
        self.in_layer = MatMul(W_in)
        self.out_layer = MatMul(W_out)
        self.loss_layer1 = SoftmaxWithLoss()
        self.loss_layer2 = SoftmaxWithLoss()

        # すべての重みと勾配をリストにまとめる
        self.layers = [self.in_layer, self.out_layer]
        self.params, self.grads = [], []
        for layer in self.layers:
            self.params += layer.params
            self.grads += layer.grads
        
        # メンバ変数に単語の分散表現を設定
        self.word_vecs = W_in

    
    def forward(self, contexts, target):
        h = self.in_layer.forward(target)
        s = self.out_layer.forward(h)
        l1 = self.loss_layer1.forward(s, contexts[:, 0]) # (N, 1)
        l2 = self.loss_layer2.forward(s, contexts[:, 1]) # (N, 1)
        loss = l1 + l2
        return loss

    def backward(self, dout=1):
        dl1 = self.loss_layer1.backward(dout)
        dl2 = self.loss_layer2.backward(dout)
        ds = dl1 + dl2
        dh = self.out_layer.backward(ds)
        self.in_layer.backward(dh)
        return None



