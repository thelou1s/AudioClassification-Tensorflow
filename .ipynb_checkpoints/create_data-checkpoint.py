import os
import random

import librosa
import pandas as pd
import numpy as np
import tensorflow as tf
from tqdm import tqdm


debug = True


# 获取浮点数组
def _float_feature(value):
    if not isinstance(value, list):
        value = [value]
    return tf.train.Feature(float_list=tf.train.FloatList(value=value))


# 获取整型数据
def _int64_feature(value):
    if not isinstance(value, list):
        value = [value]
    return tf.train.Feature(int64_list=tf.train.Int64List(value=value))


# 把数据添加到TFRecord中
def data_example(data, label):
    feature = {
        'data': _float_feature(data),
        'label': _int64_feature(label),
    }
    return tf.train.Example(features=tf.train.Features(feature=feature))


# 开始创建tfrecord数据
def create_data_tfrecord(data_list_path, save_path):
    with open(data_list_path, 'r') as f:
        data = f.readlines()
    with tf.io.TFRecordWriter(save_path) as writer:
        for d in tqdm(data):
            try:
                path, label = d.replace('\n', '').split('\t')
                wav, sr = librosa.load(path, sr=16000)
                intervals = librosa.effects.split(wav, top_db=20)
                wav_output = []
                # [可能需要修改参数] 音频长度 16000 * 秒数
                wav_len = int(16000 * 2.04)
                for sliced in intervals:
                    wav_output.extend(wav[sliced[0]:sliced[1]])
                for i in range(5):
                    # 裁剪过长的音频，过短的补0
                    if len(wav_output) > wav_len:
                        l = len(wav_output) - wav_len
                        r = random.randint(0, l)
                        wav_output = wav_output[r:wav_len + r]
                    else:
                        wav_output.extend(np.zeros(shape=[wav_len - len(wav_output)], dtype=np.float32))
                    wav_output = np.array(wav_output)
                    # 转成梅尔频谱
                    ps = librosa.feature.melspectrogram(y=wav_output, sr=sr, hop_length=256).reshape(-1).tolist()
                    # [可能需要修改参数] 梅尔频谱shape ，librosa.feature.melspectrogram(y=wav_output, sr=sr, hop_length=256).shape
                    if len(ps) != 128 * 128: continue
                    tf_example = data_example(ps, int(label))
                    writer.write(tf_example.SerializeToString())
                    if len(wav_output) <= wav_len:
                        break
            except Exception as e:
                print(e)


# 生成数据列表
def get_data_list(audio_path, list_path):
    sound_sum = 0
    audios = os.listdir(audio_path)

    f_train = open(os.path.join(list_path, 'train_list.txt'), 'w')
    f_test = open(os.path.join(list_path, 'test_list.txt'), 'w')

    for i in range(len(audios)):
        sounds = os.listdir(os.path.join(audio_path, audios[i]))
        for sound in sounds:
            sound_path = os.path.join(audio_path, audios[i], sound)
            # if debug: print('get_data_list, sound_path = ' + str(sound_path))
            t = librosa.get_duration(filename=sound_path)
            # [可能需要修改参数] 过滤小于2.1秒的音频
            if t >= 2.1:
                if sound_sum % 100 == 0:
                    f_test.write('%s\t%d\n' % (sound_path, i))
                else:
                    f_train.write('%s\t%d\n' % (sound_path, i))
                sound_sum += 1
        print("Audio：%d/%d" % (i + 1, len(audios)))

    f_test.close()
    f_train.close()


# 创建UrbanSound8K数据列表
def get_urbansound8k_list(path, urbansound8k_cvs_path):
    data_list = []
    data = pd.read_csv(urbansound8k_cvs_path)
    # 过滤掉长度少于3秒的音频
    valid_data = data[['slice_file_name', 'fold', 'classID', 'class']][data['end'] - data['start'] >= 3]
    valid_data['path'] = 'fold' + valid_data['fold'].astype('str') + '/' + valid_data['slice_file_name'].astype('str')
    for row in valid_data.itertuples():
        data_list.append([row.path, row.classID])

    f_train = open(os.path.join(path, 'train_list.txt'), 'w')
    f_test = open(os.path.join(path, 'test_list.txt'), 'w')

    for i, data in enumerate(data_list):
        sound_path = os.path.join('dataset/UrbanSound8K/audio/', data[0])
        if i % 100 == 0:
            f_test.write('%s\t%d\n' % (sound_path, data[1]))
        else:
            f_train.write('%s\t%d\n' % (sound_path, data[1]))

    f_test.close()
    f_train.close()


if __name__ == '__main__':
    if (debug): print('__main__, get_urbansound8k_list')
    get_urbansound8k_list('dataset', 'dataset/UrbanSound8K/metadata/UrbanSound8K.csv')
    
    if (debug): print('__main__, get_data_list')
    get_data_list('dataset/UrbanSound8K/audio', 'dataset')
    
    if (debug): print('__main__, create_data_tfrecord train.tfrecord')
    create_data_tfrecord('dataset/train_list.txt', 'dataset/train.tfrecord')
    
    if (debug): print('__main__, create_data_tfrecord test.tfrecord')
    create_data_tfrecord('dataset/test_list.txt', 'dataset/test.tfrecord')
