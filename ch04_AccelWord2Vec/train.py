import sys
sys.path.append("/Users/inoueshinichi/Desktop/MyGithub/DeepLearning2_NLP") # 親ディレクトリのファイルをインポートするための設定
sys.path.append("/home/inoue/MyGithub/DeepLearning2_NLP")

import numpy as np
from common import config
# GPUで実行する場合(cupy)
# config.GPU = True
import pickle
from common.trainer import Trainer
from common.optimizer import Adam
from cbow import CBOW
from common.utils import create_contexts_target, to_cpu, to_gpu
from dataset import ptb

def main():
    """CBOWモデルの学習
    """

    # ハイパーパラメータの設定
    window_size = 5
    hidden_size = 100
    batch_size = 100
    max_epoch = 1

    # データの読み込み
    corpus, word_to_id, id_to_word = ptb.load_data('train')
    vocab_size = len(word_to_id)

    contexts, target = create_contexts_target(corpus, window_size)
    if config.GPU:
        contexts, target = to_gpu(contexts), to_gpu(target)
    
    # モデルなどの生成
    model = CBOW(vocab_size, hidden_size, window_size, corpus)
    optimizer = Adam()
    trainer = Trainer(model, optimizer)

    # 学習開始
    trainer.fit(contexts, target, max_epoch, batch_size)
    trainer.plot()


    # 後ほど利用できるように、必要なデータを保存
    word_vecs = model.word_vecs

    if config.GPU:
        word_vecs = to_cpu(word_vecs)
    params = {}
    params['word_vecs'] = word_vecs.astype(np.float16)
    params['word_to_id'] = word_to_id
    params['id_to_word'] = id_to_word
    pkl_file = 'cbow_params.pkl'
    with open(pkl_file, 'wb') as f:
        pickle.dump(params, f, -1)


    
if __name__ == "__main__":
    main()