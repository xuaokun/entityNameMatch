from Levenshtein import *
import pickle
import re
import jieba.posseg as pseg
import heapq
import flask
import json
from flask import request

server = flask.Flask(__name__)
weight = pickle.load(open('weight.pkl', 'rb'))

class StringMatcher:
    def _reset_cache(self):
        self._ratio = self._distance = None
        self._opcodes = self._editops = self._matching_blocks = None

    def __init__(self, seq1='', seq2=''):
        self._str1, self._str2 = seq1, seq2
        self._reset_cache()

    def set_seqs(self, seq1, seq2):
        self._str1, self._str2 = seq1, seq2
        self._reset_cache()

    def set_seq1(self, seq1):
        self._str1 = seq1
        self._reset_cache()

    def set_seq2(self, seq2):
        self._str2 = seq2
        self._reset_cache()

    def get_opcodes(self):
        if not self._opcodes:
            if self._editops:
                self._opcodes = opcodes(self._editops, self._str1, self._str2)
            else:
                self._opcodes = opcodes(self._str1, self._str2)
        return self._opcodes

    def get_editops(self):
        if not self._editops:
            if self._opcodes:
                self._editops = editops(self._opcodes, self._str1, self._str2)
            else:
                self._editops = editops(self._str1, self._str2)
        return self._editops

    def get_matching_blocks(self):
        if not self._matching_blocks:
            self._matching_blocks = matching_blocks(self.get_opcodes(),
                                                    self._str1, self._str2)
        return self._matching_blocks

    def ratio(self):
        if not self._ratio:
            self._ratio = ratio(self._str1, self._str2)
        return self._ratio

    def partial_ratio(self, use_length=False, mismatch_length_point=0.2):
        blocks = self.get_matching_blocks()
        print(self._str1, self._str2, blocks)
        scores = []
        len1, len2 = len(self._str1), len(self._str2)
        # len_ratio = 2 * min(len1, len2) / (len1 + len2) if len1 and len2 else 0
        for block in blocks:
            long_start = block[1] - block[0] if (block[1] - block[0]) > 0 else 0
            long_end = long_start + len(self._str1)
            long_substr = self._str2[long_start:long_end]
            m2 = StringMatcher(self._str1, long_substr)
            r = m2.ratio()
            if use_length:
                scores.append(r - mismatch_length_point)
            else:
                scores.append(r)
        return max(scores)


def join_char(words_array):
    score = []
    temp = []
    for word in words_array:
        if len(word) > 1:
            if temp:
                score.append("".join(temp))
                temp = []
            score.append(word)
        else:# 单字
            temp.append(word)
    return score


def normalize(name, branch_words, re_chars):
    if name:
        score = re.sub(r"[%s]+" % re_chars, '', name)
        score = pseg.cut(score, HMM=False)
        words = []
        ns = []
        branch = []
        for x, flag in score:
            if x in branch_words:
                branch.append(x)
            elif flag == 'ns':
                ns.append(x)
            else:
                words.append(x)
        words = join_char(words)
        ns = "".join(ns)
        branch = "".join(branch)
        return words, ns, branch
    return [], "", ""


def get_main_sub(string_array, weight_sort_amount):
    if string_array and len(string_array) >= weight_sort_amount:
        weights = [weight.get(x, 0) for x in string_array]
        index = list(map(weights.index, heapq.nsmallest(weight_sort_amount, weights)))
        return "".join([x for i, x in enumerate(string_array) if i in index]), "".join([x for i, x in enumerate(string_array) if i not in index])
    elif string_array:
        weights = [weight.get(x, 0) for x in string_array]
        index = weights.index(min(weights))
        return string_array[index], "".join([x for i, x in enumerate(string_array) if i != index])
    return "", ""


def match_branch(branch, compare_branch, error_branch):
    if branch == compare_branch:
        return 0
    else:
        return error_branch


def match_area(area, compare_area, null_area, error_area):
    if area == compare_area:
        return 0
    elif not area or not compare_area or area in compare_area or compare_area in area:
        return null_area
    else:
        return error_area


def match_info(words_array, compare_array, mismatch_main, miss_field, weight_sort_amount):
    main, other = get_main_sub(words_array, weight_sort_amount)
    print('主体信息:', main, '附加信息:', other)
    main_, other_ = get_main_sub(compare_array, weight_sort_amount)
    print('比较主体信息:', main_, '比较附加信息:', other_)
    ratio = 1 if main == main_ else mismatch_main
    if not other or not other_:
        return ratio - miss_field
    elif len(other) <= len(other_):
        return ratio - (1 - StringMatcher(other, other_).partial_ratio(True))
    else:
        return ratio - (1 - StringMatcher(other_, other).partial_ratio(True))


@server.route('/entity_match', methods=['GET'])
def entity_match():
    try:
        args = request.args
        if 'name' not in args or 'compareArr' not in args:
            return json.dumps({
                'status': 0,
                'data': [],
                'message': "please send params includes name, compareArr,"
                           " and compareArr should be names seperated by ','."
            })
        score = match(args['name'], args['compareArr'].split(','))
        print(score)
        return json.dumps({
            'status': 0,
            'data': score,
        })
    except Exception as e:
        print(e)
        return json.dumps({
            'status': -1,
            'data': str(e)
        })


def match(name, compare_array, branch_words=('分公司', '分支公司', '支公司', '分店', '分会', '分院', '分部', '分校'),
          re_chars='~`!#$%^&*()_+-/|\';":/.,?><br~·！@#￥%……&*（）——:-=“：’；、。，？\n 》《{}', weight_sort_amount=1,
          mismatch_main=0.3, miss_field=0.1, error_area=0.5, error_branch=0.7):
    score = {}
    name_, area, branch = normalize(name, branch_words, re_chars)
    print('实体信息提取', name_, area, branch)
    for i, compare in enumerate(compare_array):
        if name == compare:
            score[i] = 1
        else:
            compare_name, compare_area, compare_branch = normalize(compare, branch_words, re_chars)
            print('比较实体信息提取', compare_name, compare_area, compare_branch)
            ratio = match_info(name_, compare_name, mismatch_main, miss_field, weight_sort_amount)
            print('主体部分匹配度：', ratio)
            ratio_area = match_area(area, compare_area, miss_field, error_area)
            print('地区部分匹配扣除分值：', ratio_area)
            ratio_branch = match_branch(branch, compare_branch, error_branch)
            print('分支部分匹配扣除分值：', ratio_branch)
            score[i] = max(0, ratio - ratio_area - ratio_branch)
    return score


def match_subject(df_slice):
    compare_array = [re.sub(".*_", "", x) if "_" in x else "" for x in df_slice.k_kmqc_y]
    name = re.sub("<br/>.*", "", df_slice.k_xfdwmc)
    ratio = match(name, compare_array)
    global index
    index += 1
    if index % 1000 == 0:
        print(index)
    return {df_slice.k_kmqc_y[k]: v for k, v in ratio.items()}


if __name__ == "__main__":
    # index = 0
    weight = pickle.load(open('weight.pkl', 'rb'))
    # print(weight['南京'])
    # df = pickle.load(open('invoice_purchase.plk', 'rb'))
    # df = df[~df['k_xfdwmc'].isnull()]
    # df = df[df['k_xfdwmc'] != ""]
    # df['siamese'] = df.apply(lambda x: StringMatcher(x.k_xfdwmc, x.k_kmqc_x).partial_ratio(), axis=1)
    # df = df[df['siamese'] > 0.5][["k_xfdwmc", "k_kmqc_x", "k_kmqc_y"]]
    # df['match'] = df.apply(match_subject, axis=1)
    # df['match_subject'] = df['match'].apply(lambda x: {max(x, key=x.get): x[max(x, key=x.get)]})
    # df['bool_match'] = df.apply(lambda x: 1 if x.k_kmqc_x == list(x.match_subject.keys())[0] else 0, axis=1)
    # df.to_pickle("score.pkl")

    # df = pd.read_csv('weight.csv', header=None)
    # weight = {}
    # for index, row in df.iterrows():
    #     weight[row[0]] = row[1]
    # print(weight['南京'])
    # pickle.dump(weight, open('weight.pkl', 'wb'))
    # score = match('北京百度公司', ['百度有限公司', '北京千百度公司'])# 匹配度打分： 0.7 0.1
    # print(score)
    # print(join_char(['千', '千',  '百度']))
    # print(get_main_sub(['中华', '人民', '共和国'], 1))
    # a, b = 'spam', 'park'
    # mb = matching_blocks(editops(a, b), a, b)
    # print(''.join([a[x[0]:x[0] + x[2]] for x in mb]))
    # print(StringMatcher('公司', '有限责任公司').partial_ratio())
    server.run(host='0.0.0.0',
               port=1129,
               debug=True
               )