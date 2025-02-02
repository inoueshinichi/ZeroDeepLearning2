import sys
sys.path.append("/Users/inoueshinichi/Desktop/MyGithub/DeepLearning2_NLP")
sys.path.append("/home/inoue/Desktop/DeepLearning2_NLP")
import os
from common.np import *

from typing import (
    NoReturn,
    Union,
    List,
    Dict,
    Tuple,
    Callable
)

def to_cpu(x):
    import numpy
    if type(x) == numpy.ndarray:
        return x
    return np.asnumpy(x)


def to_gpu(x):
    import cupy
    if type(x) == cupy.ndarray:
        return x
    return cupy.asarray(x)

def clip_grads(grads: np.ndarray, max_norm: float):
    total_norm = 0
    for grad in grads:
        total_norm += np.sum(grad**2)
    total_norm = np.sqrt(total_norm)

    rate = max_norm / (total_norm + 1e-6)
    if rate < 1:
        for grad in grads:
            grad *= rate


def preprocess(text: str) -> Tuple[np.ndarray, Dict, Dict]:
    """コーパスを作る前処理

    Args:
        text (str): コーパスの元となる文字列

    Returns:
        Tuple[np.ndarray, Dict, Dict]: [description]
    """
    text = text.lower()
    text = text.replace('.', ' .')
    # print(f"text: {text}")

    words = text.split(' ')
    # print(f"words: {words}")

    # ------------
    word_to_id = {}
    id_to_word = {}

    for word in words:
        if word not in word_to_id:
            new_id = len(word_to_id)
            word_to_id[word] = new_id
            id_to_word[new_id] = word

    # print(f"word_to_id: {word_to_id}")
    # print(f"id_to_word: {id_to_word}")

    # import numpy as np
    corpus = [word_to_id[w] for w in words]
    corpus = np.array(corpus)
    # print(f"corpus: {corpus}")

    return corpus, word_to_id, id_to_word


def create_co_matrix(corpus: List[int], vocab_size: int, window_size: int = 1) -> np.ndarray:
    """共起行列の作成

    Args:
        corpus (List[int]): コーパス e.g. [0 1 2 3 4 1 5 6]
        vocab_size (int): 単語数
        window_size (int, optional): [description]. Defaults to 1.
    """
    corpus_size = len(corpus)
    co_matrix = np.zeros((vocab_size, vocab_size), dtype=np.int32)

    for idx, word_id in enumerate(corpus):
        for i in range(1, window_size + 1):
            left_idx = idx - i
            right_idx = idx + i

            if left_idx >= 0:
                left_word_id = corpus[left_idx]
                co_matrix[word_id, left_word_id] += 1

            if right_idx < corpus_size:
                right_word_id = corpus[right_idx]
                co_matrix[word_id, right_word_id] += 1

    return co_matrix


def cos_similarity(x: np.ndarray, y: np.ndarray, esp:float = 1e-8) -> float:
    """コサイン類似度

    Args:
        x (np.ndarray): 単語ベクトル
        y (np.ndarray): 単語ベクトル

    cosine_similarity = x・y / (||x|| * ||y||)

    Returns:
        float: コサイン類似度 [-1,+1]
    """
    nx = x / np.sqrt(np.sum(x**2) + esp)
    ny = y / np.sqrt(np.sum(y**2) + esp)

    return np.dot(nx, ny)



def most_similar(query: str, 
                 word_to_id: Dict[str, int], 
                 id_to_word: Dict[int, str],
                 word_matrix: np.ndarray, 
                 top:int = 5):
    """類似単語のランキング表示

    Args:
        query (str): クエリ(単語)
        word_to_id (Dict[str, int]): 単語から単語IDへのdict
        id_to_word (Dict[int, str]): 単語IDから単語へのdict
        word_matrix (np.ndarray): 共起行列(各行に対応する単語のベクトルが格納されている)
        top (int, optional): [description]. Defaults to 5.
    """

    # 1) クエリを取り出す
    if query not in word_to_id:
        print(f"{query} is not found.")
        return
    
    print("\n[query] " + query)
    query_id = word_to_id[query]
    query_vec = word_matrix[query_id]

    # 2) コサイン類似度を計算
    vocab_size = len(id_to_word)
    similarity = np.zeros(vocab_size)
    for i in range(vocab_size):
        similarity[i] = cos_similarity(word_matrix[i], query_vec)
    
    # 3) コサイン類似度の結果から、その値を高い順位出力
    count = 0
    for i in (-1 * similarity).argsort(): # argsort()は小さい順に出力する
        if id_to_word[i] == query:
            continue
        print(f" {id_to_word[i]}: {similarity[i]}")

        count += 1
        if count >= top:
            return


def ppmi(C: np.ndarray, verbose: bool = False, eps: float = 1e-8) -> np.ndarray:
    """正の相互情報量に換装した共起行列(単語行列)を計算する

    Args:
        C (np.ndarray): 単語の出現頻度に着目した共起行列
        verbose (bool, optional): [description]. Defaults to False.
        eps (float, optional): [description]. Defaults to 1e-8.

    PMI(x,y) = log2(P(x,y)/P(x)*P(y)) 
             = log2({C(x,y)/N}/{C(x)/N}*{C(y)/N})
             = log2({C(x,y)*N}/{C(x)*C(y)})
    PMI(x,y) = -∞ になるパターンがあるので、
    PPMI(x,y) = max(0, PMI(x,y)) とする.(正の相互情報量)

    You say goodbye and I say hello .
    you: 0
    say: 1
    goodbye: 2
    and: 3
    I: 4
    say: 5
    hello: 6
    .: 7

    共起行列
        you | say | goodbye | and | I | hello | . 
    you   1     0         0     0   0       0   0
    say   1     0         1     0   1       1   0
goodbye   0     1         0     1設定   0       0   0
    and   0     0         1     0   1       0   0
      I   0     1         0     1   0       0   0
  hello   0     1         0     0   0       0   1
      .   0     0         0     0   0       1   0
    ---------------------------------------------
          2     3         2     2   2       2   1

    N = 14
    C(`say`,`goodbye`) = 1
    C(`say`) = 3
    C(`goodbye`) = 2

    PMI(`say`,`goodbye`) = log2(1*14 / 3*2)

    Returns:
        np.ndarray: [description]
    """

    M = np.zeros_like(C, dtype=np.float32) # PPMI
    N = np.sum(C) # 共起行列の全出現頻度
    S = np.sum(C, axis=0) # 周辺頻度
    total = C.shape[0] * C.shape[1]
    cnt = 0

    for i in range(C.shape[0]):
        for j in range(C.shape[1]):
            pmi = np.log2(C[i,j]*N / (S[j]*S[i]) + eps)
            M[i,j] = max(0, pmi)

            if verbose:
                cnt += 1
                if cnt % (total/100) == 0:
                    print("%.1f%% done" % (100*cnt / total))
    
    return M



    
def create_contexts_target(corpus: List[int], window_size: int = 1) -> Tuple[np.ndarray, np.ndarray]:
    """コーパスからコンテキストとターゲットを作成する

    Args:
        corpus (List[int]): [description]
        window_size (int, optional): [description]. Defaults to 1.

    Returns:
        Tuple[np.ndarray, np.ndarray]: [description]
    """
    target = corpus[window_size:-window_size]
    contexts = []

    for idx in range(window_size, len(corpus) - window_size):
        cs = []
        for t in range(-window_size, window_size + 1):
            if t == 0:
                continue
            cs.append(corpus[idx + t])
        contexts.append(cs)
    
    return np.array(contexts), np.array(target)



def convert_one_hot(corpus, vocab_size):
    '''one-hot表現への変換
        :param corpus: 単語IDのリスト（1次元もしくは2次元のNumPy配列）
        :param vocab_size: 語彙数設定
        :return: one-hot表現（2次元もしくは3次元のNumPy配列）
    '''
    N = corpus.shape[0]
    one_hot = None

    if corpus.ndim == 1:
        one_hot = np.zeros((N, vocab_size), dtype=np.int32)
        for idx, word_id in enumerate(corpus):
            one_hot[idx, word_id] = 1

    elif corpus.ndim == 2:
        C = corpus.shape[1]
        one_hot = np.zeros((N, C, vocab_size), dtype=np.int32)
        for idx_0, word_ids in enumerate(corpus):
            for idx_1, word_id in enumerate(word_ids):
                one_hot[idx_0, idx_1, word_id] = 1

    return one_hot


def normalize(x):
    if x.ndim == 2:
        s = np.sqrt((x * x).sum(1))
        x /= s.reshape((s.shape[0], 1))
    elif x.ndim == 1:
        s = np.sqrt((x * x).sum())
        x /= s
    return x


def analogy(a, b, c, word_to_id, id_to_word, word_matrix, top=5, answer=None):
    for word in (a, b, c):
        if word not in word_to_id:
            print('%s is not found' % word)
            return

    print('\n[analogy] ' + a + ':' + b + ' = ' + c + ':?')
    a_vec, b_vec, c_vec = word_matrix[word_to_id[a]], word_matrix[word_to_id[b]], word_matrix[word_to_id[c]]
    query_vec = b_vec - a_vec + c_vec
    query_vec = normalize(query_vec)

    similarity = np.dot(word_matrix, query_vec)

    if answer is not None:
        print("==>" + answer + ":" + str(np.dot(word_matrix[word_to_id[answer]], query_vec)))

    count = 0
    for i in (-1 * similarity).argsort(): # 降順
        if np.isnan(similarity[i]):
            continue
        if word_to_id[i] in (a, b, c):
            continue

        print(' {0}: {1}'.format(id_to_word[i], similarity[i]))

        count += 1
        if count >= top:
            return


def eval_perplexity(model, corpus, batch_size=10, time_size=35):
    print('evaluating perplexity ...')
    corpus_size = len(corpus)
    total_loss, loss_cnt = 0, 0
    max_iters = (corpus_size - 1) // (batch_size * time_size)
    jump = (corpus_size - 1) // batch_size

    for iters in range(max_iters):
        xs = np.zeros((batch_size, time_size), dtype=np.int32)
        ts = np.zeros((batch_size, time_size), dtype=np.int32)
        time_offset = iters * time_size
        offsets = [time_offset + (i * jump) for i in range(batch_size)]
        for t in range(time_size):
            for i, offset in enumerate(offsets):
                xs[i, t] = corpus[(offset + t) % corpus_size]
                ts[i, t] = corpus[(offset + t + 1) % corpus_size]

        try:
            loss = model.forward(xs, ts, train_flg=False)
        except TypeError:
            loss = model.forward(xs, ts)
        total_loss += loss

        sys.stdout.write('\r%d / %d' % (iters, max_iters))
        sys.stdout.flush()

    print('')
    ppl = np.exp(total_loss / max_iters)
    return ppl


def eval_seq2seq(model, question, correct, id_to_char,
                 verbos=False, is_reverse=False):
    correct = correct.flatten()
    # 頭の区切り文字
    start_id = correct[0]
    correct = correct[1:]
    guess = model.generate(question, start_id, len(correct))

    # 文字列へ変換
    question = ''.join([id_to_char[int(c)] for c in question.flatten()])
    correct = ''.join([id_to_char[int(c)] for c in correct])
    guess = ''.join([id_to_char[int(c)] for c in guess])

    if verbos:
        if is_reverse:
            question = question[::-1]

        colors = {'ok': '\033[92m', 'fail': '\033[91m', 'close': '\033[0m'}
        print('Q', question)
        print('T', correct)

        is_windows = os.name == 'nt'

        if correct == guess:
            mark = colors['ok'] + '☑' + colors['close']
            if is_windows:
                mark = 'O'
            print(mark + ' ' + guess)
        else:
            mark = colors['fail'] + '☒' + colors['close']
            if is_windows:
                mark = 'X'
            print(mark + ' ' + guess)
        print('---')

    return 1 if guess == correct else 0
