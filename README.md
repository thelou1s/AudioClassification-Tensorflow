
# 前言
本章我们来介绍如何使用Tensorflow训练一个区分不同音频的分类模型，例如你有这样一个需求，需要根据不同的鸟叫声识别是什么种类的鸟，这时你就可以使用这个方法来实现你的需求了。话不多说，来干。

# 环境准备
主要介绍libsora，PyAudio，pydub的安装，其他的依赖包根据需要自行安装。
 - Python 3.7
 - Tensorflow 2.0

## 安装libsora
最简单的方式就是使用pip命令安装，如下：
```shell
pip install pytest-runner
pip install librosa
```

如果pip命令安装不成功，那就使用源码安装，下载源码：[https://github.com/librosa/librosa/releases/](https://github.com/librosa/librosa/releases/)， windows的可以下载zip压缩包，方便解压。
```shell
pip install pytest-runner
tar xzf librosa-<版本号>.tar.gz 或者 unzip librosa-<版本号>.tar.gz
cd librosa-<版本号>/
python setup.py install
```

如果出现`libsndfile64bit.dll': error 0x7e`错误，请指定安装版本0.6.3，如`pip install librosa==0.6.3`

## 安装PyAudio
使用pip安装命令，如下：
```shell
pip install pyaudio
```
 在安装的时候需要使用到C++库进行编译，如果读者的系统是windows，Python是3.7，可以在这里下载whl安装包，下载地址：[https://github.com/intxcc/pyaudio_portaudio/releases](https://github.com/intxcc/pyaudio_portaudio/releases)

## 安装pydub
使用pip命令安装，如下：
```shell
pip install pydub
```

# 训练分类模型
把音频转换成训练数据最重要的是使用了librosa，使用librosa可以很方便得到音频的梅尔频谱（Mel Spectrogram），使用的API为`librosa.feature.melspectrogram()`，输出的是numpy值，可以直接用tensorflow训练和预测。关于梅尔频谱具体信息读者可以自行了解，跟梅尔频谱同样很重要的梅尔倒谱（MFCCs）更多用于语音识别中，对应的API为`librosa.feature.mfcc()`。同样以下的代码，就可以获取到音频的梅尔频谱，其中`duration`参数指定的是截取音频的长度。
```python
y1, sr1 = librosa.load(data_path, duration=2.97)
ps = librosa.feature.melspectrogram(y=y1, sr=sr1)
```

## 创建训练数据
根据上面的方法，我们创建Tensorflow训练数据，因为分类音频数据小而多，最好的方法就是把这些音频文件生成TFRecord，加快训练速度。创建`create_data.py`用于生成TFRecord文件。

首先需要生成数据列表，用于下一步的读取需要，`audio_path`为音频文件路径，用户需要提前把音频数据集存放在`dataset/audio`目录下，每个文件夹存放一个类别的音频数据，每条音频数据长度在5秒左右，如`dataset/audio/鸟叫声/······`。`audio`是数据列表存放的位置，生成的数据类别的格式为`音频路径\t音频对应的类别标签`。读者也可以根据自己存放数据的方式修改以下函数。
```python
# 生成数据列表
def get_data_list(audio_path, list_path):
    sound_sum = 0
    persons = os.listdir(audio_path)

    f_train = open(os.path.join(list_path, 'train_list.txt'), 'w')
    f_test = open(os.path.join(list_path, 'test_list.txt'), 'w')

    for i in range(len(persons)):
        sounds = os.listdir(os.path.join(audio_path, persons[i]))
        for sound in sounds:
            sound_path = os.path.join(audio_path, persons[i], sound)
            t = librosa.get_duration(filename=sound_path)
            # 过滤小于3秒的音频
            if t >= 3:
                if sound_sum % 100 == 0:
                    f_test.write('%s\t%d\n' % (sound_path, i))
                else:
                    f_train.write('%s\t%d\n' % (sound_path, i))
                sound_sum += 1
        print("Person：%d/%d" % (i + 1, len(persons)))

    f_test.close()
    f_train.close()
   
if __name__ == '__main__':
    get_data_list('dataset/audio', 'dataset')
```

有了以上的数据列表，就可开始生成TFRecord文件了。最终会生成`train.tfrecord`和`test.tfrecord`。
```python
import os
import librosa
import pandas as pd
import tensorflow as tf
from tqdm import tqdm


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
            path, label = d.replace('\n', '').split('\t')
            y1, sr1 = librosa.load(path, duration=2.97)
            ps = librosa.feature.melspectrogram(y=y1, sr=sr1).reshape(-1).tolist()
            tf_example = data_example(ps, int(label))
            writer.write(tf_example.SerializeToString())


if __name__ == '__main__':
    create_data_tfrecord('dataset/train_list.txt', 'dataset/train.tfrecord')
    create_data_tfrecord('dataset/test_list.txt', 'dataset/test.tfrecord')
```

Urbansound8K 是目前应用较为广泛的用于自动城市环境声分类研究的公共数据集，包含10个分类：空调声、汽车鸣笛声、儿童玩耍声、狗叫声、钻孔声、引擎空转声、枪声、手提钻、警笛声和街道音乐声。数据集下载地址：[https://zenodo.org/record/1203745/files/UrbanSound8K.tar.gz](https://zenodo.org/record/1203745/files/UrbanSound8K.tar.gz)。以下是针对Urbansound8K生成数据列表的函数。如果读者想使用该数据集，请下载并解压到`dataset`目录下，把生成数据列表代码改为以下代码。
```python
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
    get_urbansound8k_list('dataset', 'dataset/UrbanSound8K/metadata/UrbanSound8K.csv')
```

创建`reader.py`用于在训练时读取TFRecord文件数据。
```python
import tensorflow as tf


def _parse_data_function(example):
    data_feature_description = {
        'data': tf.io.FixedLenFeature([16384], tf.float32),
        'label': tf.io.FixedLenFeature([], tf.int64),
    }
    return tf.io.parse_single_example(example, data_feature_description)


def train_reader_tfrecord(data_path, num_epochs):
    raw_dataset = tf.data.TFRecordDataset(data_path)
    train_dataset = raw_dataset.map(_parse_data_function)
    train_dataset = train_dataset.shuffle(buffer_size=1000) \
        .repeat(count=num_epochs) \
        .batch(batch_size=32) \
        .prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
    return train_dataset


def test_reader_tfrecord(data_path):
    raw_dataset = tf.data.TFRecordDataset(data_path)
    test_dataset = raw_dataset.map(_parse_data_function)
    test_dataset = test_dataset.batch(batch_size=32)
    return test_dataset
```

## 训练
接着就可以开始训练模型了，创建`train.py`。我们搭建简单的卷积神经网络，通过把音频数据转换成梅尔频谱，数据的shape也相当于灰度图，所以我们可以当作图像的输入创建一个深度神经网络。然后定义优化方法和获取训练和测试数据。
```python
import tensorflow as tf
import reader
import numpy as np

class_dim = 5
EPOCHS = 500

model = tf.keras.models.Sequential([
    tf.keras.layers.Conv2D(filters=20, kernel_size=5, activation=tf.nn.relu, input_shape=(128, 128, 1)),
    tf.keras.layers.Conv2D(filters=50, kernel_size=5, activation=tf.nn.relu),
    tf.keras.layers.MaxPool2D(pool_size=2, strides=2),
    tf.keras.layers.BatchNormalization(),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(units=128, activation=tf.nn.relu),
    tf.keras.layers.Dense(units=class_dim, activation=tf.nn.softmax)
])

model.summary()


# 定义优化方法
optimizer = tf.keras.optimizers.Adam(learning_rate=1e-3)

train_dataset = reader.train_reader_tfrecord('dataset/train.tfrecord', EPOCHS)
test_dataset = reader.test_reader_tfrecord('dataset/test.tfrecord')
```

最后执行训练，每200个batch执行一次测试和保存模型。要注意的是在创建TFRecord文件时，已经把音频数据的梅尔频谱转换为一维list了，所以在数据输入到模型前，需要把数据reshape为之前的shape，操作方式为`reshape((-1, 128, 128, 1))`。
```python
for batch_id, data in enumerate(train_dataset):
    sounds = data['data'].numpy().reshape((-1, 128, 128, 1))
    labels = data['label']
    # 执行训练
    with tf.GradientTape() as tape:
        predictions = model(sounds)
        # 获取损失值
        train_loss = tf.keras.losses.sparse_categorical_crossentropy(labels, predictions)
        train_loss = tf.reduce_mean(train_loss)
        # 获取准确率
        train_accuracy = tf.keras.metrics.sparse_categorical_accuracy(labels, predictions)
        train_accuracy = np.sum(train_accuracy.numpy()) / len(train_accuracy.numpy())

    # 更新梯度
    gradients = tape.gradient(train_loss, model.trainable_variables)
    optimizer.apply_gradients(zip(gradients, model.trainable_variables))

    if batch_id % 20 == 0:
        print("Batch %d, Loss %f, Accuracy %f" % (batch_id, train_loss.numpy(), train_accuracy))

    if batch_id % 200 == 0 and batch_id != 0:
        test_losses = list()
        test_accuracies = list()
        for d in test_dataset:
            test_sounds = d['data'].numpy().reshape((-1, 128, 128, 1))
            test_labels = d['label']

            test_result = model(test_sounds)
            # 获取损失值
            test_loss = tf.keras.losses.sparse_categorical_crossentropy(test_labels, test_result)
            test_loss = tf.reduce_mean(test_loss)
            test_losses.append(test_loss)
            # 获取准确率
            test_accuracy = tf.keras.metrics.sparse_categorical_accuracy(test_labels, test_result)
            test_accuracy = np.sum(test_accuracy.numpy()) / len(test_accuracy.numpy())
            test_accuracies.append(test_accuracy)

        print('=================================================')
        print("Test, Loss %f, Accuracy %f" % (
            sum(test_losses) / len(test_losses), sum(test_accuracies) / len(test_accuracies)))
        print('=================================================')

        # 保存模型
        model.save(filepath='models/cnn.h5')
```


# 预测
在训练结束之后，我们得到了一个`cnn.h5`模型，我们使用这个模型预测音频，输入的硬盘不能小于2.97秒，也不能太长，因为之截取前面的2.97秒的音频进行预测。在执行预测之前，需要把音频转换为梅尔频谱数据，并把数据shape转换为(1, 128, 128, 1)，最后输出的结果即为音频对应的标签。
```python
import librosa
import numpy as np
import tensorflow as tf


model = tf.keras.models.load_model('models/cnn.h5')


# 读取音频数据
def load_data(data_path):
    y1, sr1 = librosa.load(data_path, duration=2.97)
    ps = librosa.feature.melspectrogram(y=y1, sr=sr1)
    ps = ps[np.newaxis, ..., np.newaxis]
    return ps


def infer(audio_path):
    data = load_data(audio_path)
    result = model.predict(data)
    lab = tf.argmax(result, 1)
    return lab


if __name__ == '__main__':
    # 要预测的音频文件
    path = ''
    label = infer(path)
    print('音频：%s 的预测结果标签为：%d' % (path, label))

```


# 其他
为了方便读取录制数据和制作数据集，这里提供了两个程序，首先是`record_audio.py`，这个用于录制音频，录制的音频帧率为44100，通道为2，16bit。
```python
import pyaudio
import wave
import uuid
from tqdm import tqdm
import os

s = input('请输入你计划录音多少秒：')

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = int(s)
WAVE_OUTPUT_FILENAME = "save_audio/%s.wav" % str(uuid.uuid1()).replace('-', '')

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("开始录音, 请说话......")

frames = []

for i in tqdm(range(0, int(RATE / CHUNK * RECORD_SECONDS))):
    data = stream.read(CHUNK)
    frames.append(data)

print("录音已结束!")

stream.stop_stream()
stream.close()
p.terminate()

if not os.path.exists('save_audio'):
    os.makedirs('save_audio')

wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

print('文件保存在：%s' % WAVE_OUTPUT_FILENAME)
os.system('pause')
```

创建`crop_audio.py`，在训练是只是裁剪前面的2.97秒的音频，所以我们要把录制的硬盘安装每3秒裁剪一段，把裁剪后音频存放在音频名称命名的文件夹中。最后把这些文件按照训练数据的要求创建数据列表，和生成TFRecord文件。
```python
import os
import uuid
import wave
from pydub import AudioSegment


# 按秒截取音频
def get_part_wav(sound, start_time, end_time, part_wav_path):
    save_path = os.path.dirname(part_wav_path)
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    start_time = int(start_time) * 1000
    end_time = int(end_time) * 1000
    word = sound[start_time:end_time]
    word.export(part_wav_path, format="wav")


def crop_wav(path, crop_len):
    for src_wav_path in os.listdir(path):
        wave_path = os.path.join(path, src_wav_path)
        print(wave_path[-4:])
        if wave_path[-4:] != '.wav':
            continue
        file = wave.open(wave_path)
        # 帧总数
        a = file.getparams().nframes
        # 采样频率
        f = file.getparams().framerate
        # 获取音频时间长度
        t = int(a / f)
        print('总时长为 %d s' % t)
        # 读取语音
        sound = AudioSegment.from_wav(wave_path)
        for start_time in range(0, t, crop_len):
            save_path = os.path.join(path, os.path.basename(wave_path)[:-4], str(uuid.uuid1()) + '.wav')
            get_part_wav(sound, start_time, start_time + crop_len, save_path)


if __name__ == '__main__':
    crop_len = 3
    crop_wav('save_audio', crop_len)
```