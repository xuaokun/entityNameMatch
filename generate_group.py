from subject_match import *
import flask
import json
from flask import request

server = flask.Flask(__name__)
weight = pickle.load(open('weight.pkl', 'rb'))
min_similarity = 0.7
# score = match('北京百度公司', ['百度有限公司', '北京千百度公司'])# 匹配度打分： 0.7 0.1
# print(score)
# word_list = ['北京百度公司', '百度有限公司', '百度有限责任公司', '北京千百度公司']


# 1、生成相似度矩阵
# similar_martrix = []
# result_arr = [] # 分组结果
# for word in word_list:
#     score = match(word, word_list)
#     similar_martrix.append(list(score.values()))
# print(similar_martrix)
#         # for one_group in result_arr:
#         #     if word in one_group:
#
#
# difSet = set()
# for i, i_arr in enumerate(similar_martrix):
#     if word_list[i] in difSet: #若词语已经归类，则从下个词语继续
#         continue
#     difSet.add(word_list[i])
#     new_arr = [word_list[i]]
#     for j, sim in enumerate(i_arr):
#         if i == j:
#             continue
#         if sim >= min_similarity:
#             difSet.add(word_list[j])
#             new_arr.append(word_list[j])
#     result_arr.append(new_arr)
# print(result_arr)
# print(difSet)

@server.route('/get_entity_group', methods=['GET'])
def getSimilarGroup():
    try:
        args = request.args
        if 'word_list' not in args:
            return json.dumps({
                'status': 0,
                'data': [],
                'message': "please send params includes word_list,"
                           " and word_list should be names seperated by ','."
            })
        word_list = args['word_list'].split(',')
        # 1、生成相似度矩阵
        similar_martrix = []
        result_arr = []  # 分组结果
        for word in word_list:
            score = match(word, word_list)
            similar_martrix.append(list(score.values()))
        difSet = set()
        for i, i_arr in enumerate(similar_martrix):
            if word_list[i] in difSet:  # 若词语已经归类，则从下个词语继续
                continue
            difSet.add(word_list[i])
            new_arr = [word_list[i]]
            for j, sim in enumerate(i_arr):
                if i == j:
                    continue
                if sim >= min_similarity:
                    difSet.add(word_list[j])
                    new_arr.append(word_list[j])
            result_arr.append(new_arr)
        print(result_arr)
        return json.dumps({
            'status': 0,
            'data': result_arr,
        })
    except Exception as e:
        print(e)
        return json.dumps({
            'status': -1,
            'data': str(e)
        })


if __name__ == "__main__":
    # weight = pickle.load(open('weight.pkl', 'rb'))
    server.run(host='0.0.0.0',
               port=1130,
               debug=True
               )