# -*- coding: utf-8 -*-
"""Detecting-risky-tackles-in-sport-videos-using-Transformer-v4

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1nvnKQCMmANny2_ORSrb5f7W_78Wlhbaw

# Video Classification with Transformers

**Description:** Training a video classifier with hybrid transformers.

This example is a follow-up to the
[Video Classification with a CNN-RNN Architecture](https://keras.io/examples/vision/video_classification/)
example. This time, we will be using a Transformer-based model
([Vaswani et al.](https://arxiv.org/abs/1706.03762)) to classify videos. You can follow
[this book chapter](https://livebook.manning.com/book/deep-learning-with-python-second-edition/chapter-11)
in case you need an introduction to Transformers (with code). After reading this
example, you will know how to develop hybrid Transformer-based models for video
classification that operate on CNN feature maps.

This example requires TensorFlow 2.5 or higher, as well as TensorFlow Docs, which can be
installed using the following command:
"""

#!pip install -q git+https://github.com/tensorflow/docs

"""## Data collection"""

# Connect to drive
#from google.colab import drive
#drive.mount('/content/gdrive')

"""## Setup"""

#from tensorflow_docs.vis import embed
from tensorflow.keras import layers
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.utils import class_weight


import matplotlib.pyplot as plt
import tensorflow as tf
#import pandas as pd
import numpy as np
#import imageio
import cv2
import os

#from google.colab.patches import cv2_imshow

"""## Define hyperparameters"""

MAX_SEQ_LENGTH = 20
NUM_FEATURES = 1024
IMG_SIZE = 1920 #128
#class_weights = {0:1.0, 1:3.}
EPOCHS = 100

"""## Data preparation

We will mostly be following the same data preparation steps in this example, except for
the following changes:

* We reduce the image size to 128x128 instead of 224x224 to speed up computation.
* Instead of using a pre-trained [InceptionV3](https://arxiv.org/abs/1512.00567) network,
we use a pre-trained
[DenseNet121](http://openaccess.thecvf.com/content_cvpr_2017/papers/Huang_Densely_Connected_Convolutional_CVPR_2017_paper.pdf)
for feature extraction.
* We directly pad shorter videos to length `MAX_SEQ_LENGTH`.

First, let's load up the
[DataFrames](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html).
"""

#center_crop_layer = layers.CenterCrop(IMG_SIZE, IMG_SIZE)

def crop_center(frame):
    cropped = center_crop_layer(frame[None, ...])
    cropped = cropped.numpy().squeeze()
    return cropped

"""## Data visualization"""

cap = cv2.VideoCapture('/content/gdrive/MyDrive/ksutackle_dataset/risky_7.mp4')

while True:
  try:
    ret, frame = cap.read()
    if not ret:
      break
    #cv2_imshow(frame)
    #frame = crop_center(frame)
    #cv2_imshow(frame)
    frame = frame[:,:,[1,2,0]]
    print(frame.shape)
    #cv2_imshow(frame)


  finally:
    cap.release()





# Following method is modified from this tutorial:
# https://www.tensorflow.org/hub/tutorials/action_recognition_with_tf_hub
def load_video(path, max_frames=0):
    cap = cv2.VideoCapture(path)
    frames = []
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            #frame = crop_center(frame)
            frame = cv2.resize(frame, (IMG_SIZE,IMG_SIZE))
            frame = frame[:, :, [2, 1, 0]]
            frames.append(frame)

            if len(frames) == max_frames:
                break
    finally:
        cap.release()
    return np.array(frames)

def build_feature_extractor():
    feature_extractor = keras.applications.DenseNet121(
        weights="imagenet",
        include_top=False,
        pooling="avg",
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
    )
    preprocess_input = keras.applications.densenet.preprocess_input

    inputs = keras.Input((IMG_SIZE, IMG_SIZE, 3))
    preprocessed = preprocess_input(inputs)

    outputs = feature_extractor(preprocessed)
    return keras.Model(inputs, outputs, name="feature_extractor")


feature_extractor = build_feature_extractor()

# Label preprocessing with StringLookup.
label_tag = ['risky', 'safe']
label_processor = keras.layers.StringLookup(
    num_oov_indices=0, vocabulary=np.unique(label_tag), mask_token=None
)
print(label_processor.get_vocabulary())

label_processor(label_tag).numpy()

def prepare_all_videos(root_dir):
    
    video_paths = os.listdir(root_dir)[:20]
    labels = [video_path.split('_')[0] for video_path in video_paths][:20]
    num_samples = len(labels)
    print('num_samples ', num_samples)
    #labels = label_processor(labels[..., None]).numpy()

    labels = label_processor(labels).numpy()
    print('labels: ', labels)

    # `frame_features` are what we will feed to our sequence model.
    frame_features = np.zeros(
        shape=(num_samples, MAX_SEQ_LENGTH, NUM_FEATURES), dtype="float32"
    )


    frames_size = []

    # For each video.
    for idx, path in enumerate(video_paths):
        # Gather all its frames and add a batch dimension.
        frames = load_video(os.path.join(root_dir, path))

        frames_size.append(len(frames))

        # Pad shorter videos.
        if len(frames) < MAX_SEQ_LENGTH:
            diff = MAX_SEQ_LENGTH - len(frames)
            padding = np.zeros((diff, IMG_SIZE, IMG_SIZE, 3))
            frames = np.concatenate(frames, padding)

        frames = frames[None, ...]

        # Initialize placeholder to store the features of the current video.
        temp_frame_features = np.zeros(
            shape=(1, MAX_SEQ_LENGTH, NUM_FEATURES), dtype="float32"
        )

        # Extract features from the frames of the current video.
        for i, batch in enumerate(frames):
            video_length = batch.shape[0]
            length = min(MAX_SEQ_LENGTH, video_length)
            for j in range(length):
                if np.mean(batch[j, :]) > 0.0:
                    temp_frame_features[i, j, :] = feature_extractor.predict(
                        batch[None, j, :]
                    )

                else:
                    temp_frame_features[i, j, :] = 0.0

        frame_features[idx,] = temp_frame_features.squeeze()
    print(f'min frame: {min(frames_size)}\n max frame: {max(frames_size)}')
    return frame_features, labels


data, labels = prepare_all_videos('../../ksutackle_dataset/')

train_data_all, test_data, train_labels_all, test_labels = train_test_split(data, labels, test_size=0.20, random_state=42)
train_data, val_data, train_labels, val_labels = train_test_split(train_data_all, train_labels_all, test_size=0.30, random_state=45)
print(f"Frame features in train set: {train_data.shape}")
#class_weights = class_weight.compute_class_weight('balanced', np.unique(train_labels), np.unique(train_labels))

risky, safe = np.bincount(train_labels)
total = safe + risky
print('Examples:\n    Total: {}\n    Risky: {} ({:.2f}% of total)\n'.format(
    total, risky, 100 * risky / total))


# Scaling by total/2 helps keep the loss to a similar magnitude.
# The sum of the weights of all examples stays the same.
weight_for_0 = (1 / safe) * (total / 2.0)
weight_for_1 = (1 / risky) * (total / 2.0)

class_weights = {0: weight_for_0, 1: weight_for_1}

print('Weight for class 0: {:.2f}'.format(weight_for_0))
print('Weight for class 1: {:.2f}'.format(weight_for_1))


METRICS = [
      keras.metrics.TruePositives(name='tp'),
      keras.metrics.FalsePositives(name='fp'),
      keras.metrics.TrueNegatives(name='tn'),
      keras.metrics.FalseNegatives(name='fn'),
      keras.metrics.BinaryAccuracy(name='accuracy'),
      keras.metrics.Precision(name='precision'),
      keras.metrics.Recall(name='recall'),
      keras.metrics.AUC(name='auc'),
      keras.metrics.AUC(name='prc', curve='PR'), # precision-recall curve
]

"""## Building the Transformer-based model

We will be building on top of the code shared in
[this book chapter](https://livebook.manning.com/book/deep-learning-with-python-second-edition/chapter-11) of
[Deep Learning with Python (Second ed.)](https://www.manning.com/books/deep-learning-with-python)
by François Chollet.

First, self-attention layers that form the basic blocks of a Transformer are
order-agnostic. Since videos are ordered sequences of frames, we need our
Transformer model to take into account order information.
We do this via **positional encoding**.
We simply embed the positions of the frames present inside videos with an
[`Embedding` layer](https://keras.io/api/layers/core_layers/embedding). We then
add these positional embeddings to the precomputed CNN feature maps.
"""

class PositionalEmbedding(layers.Layer):
    def __init__(self, sequence_length, output_dim, **kwargs):
        super().__init__(**kwargs)
        self.position_embeddings = layers.Embedding(
            input_dim=sequence_length, output_dim=output_dim
        )
        self.sequence_length = sequence_length
        self.output_dim = output_dim

    def call(self, inputs):
        # The inputs are of shape: `(batch_size, frames, num_features)`
        length = tf.shape(inputs)[1]
        positions = tf.range(start=0, limit=length, delta=1)
        embedded_positions = self.position_embeddings(positions)
        return inputs + embedded_positions

    def compute_mask(self, inputs, mask=None):
        mask = tf.reduce_any(tf.cast(inputs, "bool"), axis=-1)
        return mask

"""Now, we can create a subclassed layer for the Transformer."""

class TransformerEncoder(layers.Layer):
    def __init__(self, embed_dim, dense_dim, num_heads, **kwargs):
        super().__init__(**kwargs)
        self.embed_dim = embed_dim
        self.dense_dim = dense_dim
        self.num_heads = num_heads
        self.attention = layers.MultiHeadAttention(
            num_heads=num_heads, key_dim=embed_dim, dropout=0.3
        )
        self.dense_proj = keras.Sequential(
            [layers.Dense(dense_dim, activation=tf.nn.gelu), layers.Dense(embed_dim),]
        )
        self.layernorm_1 = layers.LayerNormalization()
        self.layernorm_2 = layers.LayerNormalization()

    def call(self, inputs, mask=None):
        if mask is not None:
            mask = mask[:, tf.newaxis, :]

        attention_output = self.attention(inputs, inputs, attention_mask=mask)
        proj_input = self.layernorm_1(inputs + attention_output)
        proj_output = self.dense_proj(proj_input)
        return self.layernorm_2(proj_input + proj_output)

"""## Utility functions for training"""

def get_compiled_model():
    sequence_length = MAX_SEQ_LENGTH
    embed_dim = NUM_FEATURES
    dense_dim = 4
    num_heads = 1
    classes = len(label_processor.get_vocabulary())

    inputs = keras.Input(shape=(None, None))
    x = PositionalEmbedding(
        sequence_length, embed_dim, name="frame_position_embedding"
    )(inputs)
    x = TransformerEncoder(embed_dim, dense_dim, num_heads, name="transformer_layer")(x)
    x = layers.GlobalMaxPooling1D()(x)
    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(1, activation="sigmoid")(x)
    model = keras.Model(inputs, outputs)

    model.compile(
        optimizer="adam", loss="binary_crossentropy", metrics=METRICS
    )
    return model


def run_experiment():
    filepath = "./model_30_percent_val_split/video_classifier"
    checkpoint = keras.callbacks.ModelCheckpoint(
        filepath, save_weights_only=True, save_best_only=True, verbose=1
    )

    callback_early_stopping = tf.keras.callbacks.EarlyStopping(monitor='val_prc', patience=10, mode='max', verbose=1, restore_best_weights=True)

    model = get_compiled_model()
    history = model.fit(
        train_data,
        train_labels,
        validation_data=(val_data, val_labels),
        class_weight=class_weights,
        epochs=EPOCHS,
        callbacks=[checkpoint, callback_early_stopping],
    )

    model.load_weights(filepath)
    #_, accuracy = model.evaluate(val_data, val_labels)
    #print(f"Validation accuracy: {round(accuracy * 100, 2)}%")

    return model, history

"""## Model training and inference"""

trained_model, history = run_experiment()
print('history: {}'.format(history.history["accuracy"]))
"""**Note**: This model has ~4.23 Million parameters, which is way more than the sequence
model (99918 parameters) we used in the prequel of this example.  This kind of
Transformer model works best with a larger dataset and a longer pre-training schedule.
"""
# Model summary
print(trained_model.summary())

predictions = trained_model.predict(val_data)
print('predictions', predictions)
y_pred = np.array([1.0 if x > 0.5 else 0.0 for x in predictions])

print('y_pred', y_pred)
y_true = val_labels

print('y_true', y_true)
print(tf.math.confusion_matrix(y_true, y_pred))

from sklearn.metrics import classification_report
print(classification_report(y_true, y_pred))

# Save the model
import time
time_saved = time.time()
trained_model.save('transformer_{}.h5'.format(time_saved))
print(f'time_saved : {time_saved}')

import matplotlib.pyplot as plt

plt.plot(history.history['accuracy'], label='training_accuracy')
plt.plot(history.history['val_accuracy'], label='validation_accuracy')
plt.plot(history.history['loss'], label='training_loss')
plt.plot(history.history['val_loss'], label='validation_loss')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.title('Loss and Accuracy')
plt.legend()
plt.savefig('./plt.png', dpi=300, bbox_inches='tight')




def prepare_single_video(frames):
    frame_features = np.zeros(shape=(1, MAX_SEQ_LENGTH, NUM_FEATURES), dtype="float32")

    # Pad shorter videos.
    if len(frames) < MAX_SEQ_LENGTH:
        diff = MAX_SEQ_LENGTH - len(frames)
        padding = np.zeros((diff, IMG_SIZE, IMG_SIZE, 3))
        frames = np.concatenate(frames, padding)

    frames = frames[None, ...]

    # Extract features from the frames of the current video.
    for i, batch in enumerate(frames):
        video_length = batch.shape[0]
        length = min(MAX_SEQ_LENGTH, video_length)
        for j in range(length):
            if np.mean(batch[j, :]) > 0.0:
                frame_features[i, j, :] = feature_extractor.predict(batch[None, j, :])
            else:
                frame_features[i, j, :] = 0.0

    return frame_features


def predict_action(path):
    class_vocab = label_processor.get_vocabulary()

    frames = load_video(os.path.join("test", path))
    frame_features = prepare_single_video(frames)
    probabilities = trained_model.predict(frame_features)[0]

    for i in np.argsort(probabilities)[::-1]:
        print(f"  {class_vocab[i]}: {probabilities[i] * 100:5.2f}%")
    return frames


# This utility is for visualization.
# Referenced from:
# https://www.tensorflow.org/hub/tutorials/action_recognition_with_tf_hub
def to_gif(images):
    converted_images = images.astype(np.uint8)
    imageio.mimsave("animation.gif", converted_images, fps=10)
    return embed.embed_file("animation.gif")


#test_video = np.random.choice(test_df["video_name"].values.tolist())
#print(f"Test video path: {test_video}")
#test_frames = predict_action(test_video)
#to_gif(test_frames[:MAX_SEQ_LENGTH])

"""The performance of our model is far from optimal, because it was trained on a
small dataset.
"""
