# -*- coding: utf-8 -*-
"""intents_train.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1wCci9CoVykMZnk1n1GzNTZjoWMx3Ijv4
"""

import matplotlib.pyplot as plt
import seaborn as sns

#save default font settings
IPython_default = plt.rcParams.copy()

# set fonts / set text size
#@title matplotlib font settings
small_text = 15 #@param {type:"integer"}
medium_text = 26 #@param {type:"integer"}
large_text = 28 #@param {type:"integer"}
line_marker_size = 7 #@param {type:"slider", min:0, max:10, step:0.5}
legend_shadow = True #@param {type:"boolean"}
fig_width =  8 #@param {type:"number"}
fig_height =  6 #@param {type:"number"}
sns_style = "ticks" #@param ["darkgrid", "whitegrid", "dark", "white", "ticks"]
axis_grid = True #@param {type:"boolean"}
sns_palette = "deep" #@param ["pastel", "muted", "bright", "deep", "colorblind", "dark"]


# restore defaults
plt.rcdefaults()

#run configuration parameters
plt.rcParams['axes.labelsize']   = small_text
plt.rcParams['axes.titlesize']   = small_text
plt.rcParams['xtick.labelsize']  = small_text
plt.rcParams['ytick.labelsize']  = small_text
plt.rcParams['legend.fontsize']  = small_text
plt.rcParams['legend.shadow']    = legend_shadow
plt.rcParams['lines.markersize'] = line_marker_size
plt.rcParams['figure.figsize']   = (fig_width, fig_height)
plt.rcParams['font.size']        = small_text

# seaborn settings
sns.set_style(sns_style, {"axes.grid": axis_grid})
sns.set_palette(sns_palette)

"""# Download Embeddings"""

import os
import tqdm
import requests
import zipfile

URL = 'http://nlp.stanford.edu/data/glove.840B.300d.zip'

def fetch_data(url=URL,target_file='/content/drive/MyDrive/Colab Notebooks/chatbot-flask-simple/embeddings/glove.zip', delete_zip=False):
    # if dataset exists exit
    if os.path.isfile(target_file):
        print('datasets already downloaded')
        return

        #download (large) zip file
    #for large https request on stream mode to avoid out of memory issues
    #see : http://masnun.com/2016/09/18/python-using-the-requests-module-to-download-large-files-efficiently.html
    print("**************************")
    print("  Downloading zip file")
    print("  >_<  Please wait >_< ")
    print("**************************")
    response = requests.get(url, stream=True)
    #read chunk by chunk
    handle = open(target_file, "wb")
    for chunk in tqdm.tqdm(response.iter_content(chunk_size=512)):
        if chunk:  
            handle.write(chunk)
    handle.close()  
    print("  Download completed ;) :") 
    #extract zip_file
    zf = zipfile.ZipFile(target_file)
    print("1. Extracting {} file".format(target_file))
    zf.extractall(path='/content/drive/MyDrive/Colab Notebooks/chatbot-flask-simple/embeddings')
    if delete_zip:
        print("2. Deleting {} file".format(dataset_name+".zip"))
        os.remove(path=zip_file)

fetch_data()

"""# Imports"""

import os
import nltk
nltk.download('punkt')
nltk.download('wordnet')
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
import json
import pickle

import numpy as np
from keras.models import Sequential
from keras.layers import Dense, Activation, Dropout
from tensorflow.keras.optimizers import SGD
import random
from sklearn import preprocessing

"""# Set Variables"""

MODEL_NAME1 = 'best_model_scratch.h5'
MODEL_NAME2 = 'best_model_pretrained.h5'
model_path = '/content/drive/MyDrive/Colab Notebooks/chatbot-flask-simple/models'

model_path_scratch = os.path.join(model_path, MODEL_NAME1)
model_path_pretrained = os.path.join(model_path, MODEL_NAME2)

intents_path = '/content/drive/MyDrive/Colab Notebooks/chatbot-flask-simple/data/intents'

# inference model variables
inference_load_intents_from = os.path.join(intents_path, 'intents_job_intents.json')

words = []
tags = []
classes = []
documents = []
all_patterns = []
all_tags = []
label_encoded_Y = []
x_tr_seq = []
x_val_seq = []
y_tr = []
y_val = []
ignore_words = ['?', '!']

"""# Load JSON"""

data_file = open(inference_load_intents_from, encoding='cp1252').read()
intents = json.loads(data_file)

"""## Read in patterns and tags

Patterns are the user input (i.e., 'Hi,' 'How are you?').

Nothing is tokenized here.
"""

# print classes
for intent in intents['intents']:
    all_patterns.extend(intent['patterns'])
    for pattern in intent['patterns']:
        all_tags.append(intent['tag'])
        w = nltk.word_tokenize(pattern)
        words.extend(w)
        documents.append((w, intent['tag']))

        if intent['tag'] not in classes:
            classes.append(intent['tag'])

words = [lemmatizer.lemmatize(w.lower()) for w in words if w not in ignore_words]
words = sorted(list(set(words)))
classes = sorted(list(set(classes)))

print(len(documents), 'documents')
print(len(classes), 'classes', classes)
print(len(words), 'unique lemmatized words', words)

print(all_tags)
print(all_patterns)

"""## Encode Tags

### Fit
"""

# create label encoder
from sklearn import preprocessing
le = preprocessing.LabelEncoder()
# fit on all tags from JSON file
le.fit(all_tags)
print(f'Number of classes: {len(list(le.classes_))}')

"""### Transform"""

label_encoded_Y = le.transform(all_tags)
print(f'Label_encoded_Y: {label_encoded_Y}')
print(f'Label_encoded_Y bincount: {np.bincount(label_encoded_Y)}')

"""## Create x_all, y_all"""

X_all = np.asarray(all_patterns)
y_all = np.asarray(label_encoded_Y)
print(f'X all shape: {X_all.shape}')
print(f'Y all shape: {y_all.shape}')
print(f'y_all: {y_all}')

"""# Tokenize

# Save tokenization file
"""

from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences

tokenizer = Tokenizer()
tokenizer.fit_on_texts(list(X_all))
print(tokenizer.word_index)
with open('/content/drive/MyDrive/Colab Notebooks/chatbot-flask-simple/data/intents/tokenizer.pickle', 'wb') as handle:
    pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)

X_all_seq = tokenizer.texts_to_sequences(X_all)
print(X_all_seq)

"""### Pad"""

# padding to prepare sequences of same length
X_all_seq = pad_sequences(X_all_seq, maxlen=25)
print(X_all_seq)
#type is now a numpy.ndarray
print(type(X_all_seq))
print(f'Shape (X_all): {X_all_seq.shape}')

"""# Vocab Size"""

size_of_vocabulary = len(tokenizer.word_index) + 1 #+1 for padding
print(tokenizer.word_index)
print(f'Size of vocab: {size_of_vocabulary}')

"""# Load the Whole Embedding into Memory

## DOES NOT NEED TO BE RE-RUN!
"""

# load the whole embedding into memory
path_to_glove_file = '/content/drive/MyDrive/Colab Notebooks/chatbot-flask-simple/embeddings/glove.840B.300d.txt'

embeddings_index = {}
with open(path_to_glove_file) as f:
    for line in f:
        word, coefs = line.split(maxsplit=1)
        coefs = np.fromstring(coefs, "f", sep=" ")
        embeddings_index[word] = coefs

print("Found %s word vectors." % len(embeddings_index))

"""# Create the weight matrix"""

# create a weight matrix for words in training docs
# create a weight matrix for words in training docs
embedding_matrix = np.zeros((size_of_vocabulary, 300))
hits = 0
misses = 0
missedWords = []
for word, i in tokenizer.word_index.items():
    embedding_vector = embeddings_index.get(word)
    if embedding_vector is not None and embedding_vector.shape[0] != 0:       
        embedding_matrix[i] = embedding_vector
        hits += 1
    else:
        misses += 1
        missedWords.append(word)
print(f'Converted {hits} words ({misses} misses)')
print(missedWords)

"""# Write Pickle and classes to file"""

pickle.dump(words,open(os.path.join(intents_path, 'intents_words.pkl'),'wb'))
pickle.dump(classes,open(os.path.join(intents_path, 'intents_classes.pkl'),'wb'))
training = []
output_empty = [0] * len(classes)
for seq, doc in zip(X_all_seq, documents):
    output_row = list(output_empty)
    output_row[classes.index(doc[1])] = 1
    training.append([seq, output_row])

print(training)

import random
random.seed(0)
random.shuffle(training)
training = np.array(training)
X_train_all = list(training[:,0])
y_train_all = list(training[:,1])
print(len(X_train_all))
print(len(y_train_all))

"""# Build Model

## Create model bag of words
"""

# init training data
training_bow = []
output_empty = [0] * len(classes)
for doc in documents:
    bag = []
    pattern_words = doc[0]
    pattern_words = [lemmatizer.lemmatize(word.lower()) for word in pattern_words]

    for w in words:
        bag.append(1) if w in pattern_words else bag.append(0)

    output_row = list(output_empty)
    output_row[classes.index(doc[1])] = 1

    training_bow.append([bag, output_row])

random.shuffle(training_bow)
training_bow = np.array(training_bow)
# create train and test lists.  X - patterns, y - intents
X_train_bag = list(training_bow[:,0])
y_train_bag = list(training_bow[:,1])
print('Training data created')
print(f'X train: {X_train_bag}')
print(f'y train: {y_train_bag}')

def create_model_bag():

    model = Sequential()
    model.add(Dense(128, input_shape=(len(X_train_bag[0]),), activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(64, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(len(y_train_bag[0]), activation='softmax'))

    # Compile model.  Stochastic gradient descent with Nesterov accelerated
    # gradient gives good
    # results for this model
    sgd = SGD(learning_rate=0.01, decay=1e-6, momentum=0.9, nesterov=True)
    model.compile(loss='sparse_categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])
    print(model.summary())

    return model

"""# Create model scratch"""

from keras.models import Sequential
from keras.layers import Dense, Embedding, LSTM, GlobalMaxPooling1D
from keras.wrappers.scikit_learn import KerasClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.model_selection import cross_val_score
import numpy
from keras.callbacks import *
from keras.initializers import Constant

def create_model_scratch():
    model = Sequential()
    #embedding layer
    model.add(Embedding(size_of_vocabulary,300,
                        input_length=25,
                        trainable=True))
    #lstm layer
    model.add(LSTM(128,return_sequences=True,dropout=0.2))

    #Global Maxpooling
    model.add(GlobalMaxPooling1D())

    #Dense Layer
    model.add(Dense(64,activation='relu'))
    model.add(Dense(len(y_train_all[0]),activation='softmax'))

    #Add loss function, metrics, optimizer
    # Compile model.  Stochastic gradient descent with Nesterov accelerated
    # gradient gives good
    # results for this model
    sgd = SGD(learning_rate=0.01, decay=1e-6, momentum=0.9, nesterov=True)
    model.compile(loss='sparse_categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])

    #addingcallbacks
    #es = EarlyStopping(monitor='val_loss', mode='min', verbose=1, patience=1000)
    #mc = ModelCheckpoint(model_path_scratch, monitor='val_accuracy', mode='max', 
                         #save_best_only=True, verbose=1)
    
    print(model.summary())

    return model

"""## Create pretrained model"""

from keras.models import Sequential
from keras.layers import Dense, Embedding, LSTM, GlobalMaxPooling1D
from keras.wrappers.scikit_learn import KerasClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.model_selection import cross_val_score
import numpy
from keras.callbacks import *
from keras.initializers import Constant

def create_model_pretrained():
    model = Sequential()
    #embedding layer
    model.add(Embedding(size_of_vocabulary,300,
                        input_length=25,
                        embeddings_initializer=Constant(embedding_matrix),
                        trainable=True))
    #lstm layer
    model.add(LSTM(128,return_sequences=True,dropout=0.2))

    #Global Maxpooling
    model.add(GlobalMaxPooling1D())

    #Dense Layer
    model.add(Dense(64,activation='relu'))
    model.add(Dense(len(y_train_all[0]),activation='softmax'))

    #Add loss function, metrics, optimizer
    # Compile model.  Stochastic gradient descent with Nesterov accelerated
    # gradient gives good
    # results for this model
    sgd = SGD(learning_rate=0.01, decay=1e-6, momentum=0.9, nesterov=True)
    model.compile(loss='sparse_categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])

    #addingcallbacks
    es = EarlyStopping(monitor='val_loss', mode='min', verbose=2, patience=1000)
    mc = ModelCheckpoint(model_path_pretrained, monitor='val_accuracy', mode='max', 
                         save_best_only=True, verbose=2)
    
    print(model.summary())

    return model

np.argmax(y_train_all, axis=1).shape

"""# GRAPH"""

print(np.argmax(y_train_all, axis=1))

import matplotlib.pyplot as plt
from sklearn.model_selection import cross_val_score
from keras.wrappers.scikit_learn import KerasClassifier

pretrained = KerasClassifier(build_fn=create_model_pretrained, epochs=300,
                             batch_size=5, verbose=2)
scratch = KerasClassifier(build_fn=create_model_scratch, epochs=300, 
                          batch_size=5, verbose=2)
bag_of_words = KerasClassifier(build_fn=create_model_bag, epochs=300, 
                               batch_size=5, verbose=2)
classifiers = {'WordEmbeddings (pre-trained)': pretrained,
               'WordEmbeddings (from scratch)': scratch}

kfold = StratifiedKFold(n_splits=10, shuffle=True, random_state=1)

fig, ax = plt.subplots()
for name, model in classifiers.items():
    print(name, model)
    cv_scores = cross_val_score(model,
                                np.array(X_train_all), 
                                np.argmax(y_train_all, axis=1),
                                cv=kfold,
                                scoring='accuracy',
                                n_jobs=-1,
                                verbose=2)
    print(cv_scores.mean())
    my_lbl = f'{name} {cv_scores.mean():.3f}'
    ax.plot(cv_scores, '-o', label=my_lbl) 

cv_scores = cross_val_score(bag_of_words,
                           np.array(X_train_bag),
                           np.argmax(y_train_bag, axis=1),
                           cv=kfold,
                           scoring='accuracy',
                           n_jobs=-1,
                           verbose=2)

my_lbl = f'BOW {cv_scores.mean():.3f}'
ax.plot(cv_scores, '-o', label=my_lbl) 
ax.set_ylim(0.0, 1.1)
ax.set_xlabel('Fold')
ax.set_ylabel('Accuracy')
handles, labels = ax.get_legend_handles_labels()
# sort both labels and handles by accuracy
labels, handles = zip(*sorted(zip(labels, handles), key=lambda t: t[0]))   
print(f'label: {labels}, handle: {handles}')

ax.legend(handles, labels, ncol=1, bbox_to_anchor=(1.04,.5),loc='center left')

plt.show()

pretrained.fit(np.array(X_train_all), np.argmax(y_train_all, axis=1))
pretrained.model.save(os.path.join(intents_path, 'pretrained_embeddings.h5'))
bag_of_words.fit(np.array(X_train_bag),np.argmax(y_train_bag, axis=1))
bag_of_words.model.save(os.path.join(intents_path, 'BOW_embeddings.h5'))