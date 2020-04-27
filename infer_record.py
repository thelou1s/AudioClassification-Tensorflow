import wave
import librosa
import numpy as np
import pyaudio
import tensorflow as tf

# 获取网络模型
model = tf.keras.models.load_model('models/cnn.h5')

# 录音参数
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 3
WAVE_OUTPUT_FILENAME = "infer_audio.wav"

# 打开录音
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)


# 读取音频数据
def load_data(data_path):
    y1, sr1 = librosa.load(data_path, duration=2.97)
    ps = librosa.feature.melspectrogram(y=y1, sr=sr1)
    ps = ps[..., np.newaxis]
    ps = np.array([ps]).astype(np.float32)
    return ps


# 获取录音数据
def record_audio():
    print("开始录音......")

    frames = []
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("录音已结束!")

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    return WAVE_OUTPUT_FILENAME


# 预测
def infer(audio_data):
    result = model.predict(audio_data)
    lab = tf.argmax(result, 1)
    return lab


if __name__ == '__main__':
    try:
        while True:
            # 加载数据
            data = load_data(record_audio())

            # 获取预测结果
            label = infer(data)
            print('预测的标签为：%d' % label)
    except Exception as e:
        print(e)
        stream.stop_stream()
        stream.close()
        p.terminate()