"""
Load raw audio files in time domain into dataset for training or testing
------------------------------------------------------------------------
Copyright: 2019 Wang,Zehui (wzehui@hotmail.com)
@author: Wang,Zehui
"""

import torch
import torchaudio
import pandas as pd
import os
import numpy as np
import random

from utils.MelFrequency import mel_freq


def process_index(csv_path, test_rate, val_rate, repeat_time):
    len_csv = len(pd.read_csv(csv_path))
    index = [n for n in range(len_csv)]

    random.seed(5)  # reproducibility
    test_index = random.sample(index, round(test_rate * len(index)))
    train_index = list(set(index)-set(test_index))

    val_index = random.sample(train_index, round(val_rate * len(train_index)))
    train_index = list(set(train_index)-set(val_index))

    len_o = len(train_index)
    for i in range(0, repeat_time):
        temp = random.sample(train_index, len_o)
        train_index.extend(temp)

    return train_index, val_index, test_index


class PreprocessData(object):

    def __init__(self, csv_path, file_path, index):
        csv_data = pd.read_csv(csv_path)
        self.index = index
        # initialize lists to hold file names, labels, and folder numbers
        self.file_names = []
        self.labels = []
        self.folder_names = []

        # loop through the csv entries and only add entries from folders in the folder list
        for i in range(len(csv_data)):
            row_element = csv_data.iloc[i, 0]
            row_element = row_element.split(";")
            self.file_names.append(row_element[0])
            self.folder_names.append(row_element[1])
            self.labels.append(int(row_element[2]))

        self.file_path = file_path
        self.mixer = torchaudio.transforms.DownmixMono()  # uses two channels, this will convert them to one

    def __getitem__(self, index):
        # format the file path and load the file
        path = self.file_path + str(self.folder_names[self.index[index]]) + os.sep + self.file_names[self.index[index]] + "_m" + ".wav"
        sound = torchaudio.load(path, out=None, normalization=True)
        # load returns a tensor with the sound data and the sampling frequency
        sound_data = self.mixer(sound[0])
        temp_data = torch.zeros([1, 120000])  # tempData accounts for audio clips that are too short
        if sound_data.numel() < 120000:
            temp_data[0, :sound_data.numel()] = sound_data[0, :]
        else:
            temp_data[0, :] = sound_data[0, :120000]
        sound_data = temp_data

        # Pre-emphasis
        pre_emphasis = 0.97
        sound_data_e = np.append(sound_data[0, 0].numpy(),
                                 (sound_data[0, 1:] - pre_emphasis * sound_data[0, :-1]).numpy())
        sound_data_e = torch.from_numpy(sound_data_e)
        sound_data_e = sound_data_e.unsqueeze(0)

        sound_data = mel_freq(sound_data_e, sound[1])
        sound_data = sound_data.unsqueeze(0)  # expand dimension from [*,nmel,nframe] to [*,1,nmel,nframe]
        return sound_data, self.labels[self.index[index]]

    def __len__(self):
        return len(self.index)
