# -*- coding: utf-8 -*-
"""flask-chatterbot-simple.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1kCQkP7eEvxrpkp79sfdkAVyIKw9jSugC
"""

#!pip install flask-ngrok

#from flask_ngrok import run_with_ngrok
from flask import Flask, render_template, request
import re
import os
from time import time

import numpy as np
import pandas as pd
from keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from keras.layers import Dense, Input, LSTM, Embedding, RepeatVector, concatenate, TimeDistributed
from keras.models import Model
from keras.models import load_model
from tensorflow.keras.optimizers import Adam
from keras.utils import np_utils
from nltk.tokenize import casual_tokenize
import joblib
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences

import nltk
nltk.download('punkt')
nltk.download('wordnet')
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
import pickle
import numpy as np
from keras.models import load_model

import json
import random

# text clean up imports
import textwrap
import nltk.data

# fold paths when using Colab
#TEMPLATE = '/content/drive/MyDrive/Colab Notebooks/chatbot-flask-simple/templates'
#STATIC = '/content/drive/MyDrive/Colab Notebooks/chatbot-flask-simple/static'

TEMPLATE = os.path.join(os.getcwd(), 'templates')
STATIC = os.path.join(os.getcwd(), 'static')

#create flask app 
app = Flask(__name__,
            template_folder=TEMPLATE,
            static_folder=STATIC)

# run with ngrok when using Colab
#run_with_ngrok(app)

# model paths when using Colab
seq2seq_path = os.path.join(os.getcwd(), 'data/seq2seq')
intents_path = os.path.join(os.getcwd(), 'data/intents')

class chatbot:
    def __init__(self):
        self.max_vocab_size = 50000
        self.max_seq_len = 30
        self.embedding_dim = 100
        self.hidden_state_dim = 100
        self.epochs = 80
        self.batch_size = 128
        self.learning_rate = 1e-4
        self.dropout = 0.3
        self.data_path = r'G:\My Drive\chatbot\twcs.csv'
        self.outpath = seq2seq_path
        self.version = 'v1'
        self.mode = 'inference'
        self.num_train_records = 50000
        self.load_model_from = os.path.join(seq2seq_path, 's2s_model_v1_.h5')
        self.vocabulary_path = os.path.join(seq2seq_path, 'vocabulary.pkl')
        self.reverse_vocabulary_path = os.path.join(seq2seq_path, 'reverse_vocabulary.pkl')
        self.count_vectorizer_path = os.path.join(seq2seq_path, 'count_vectorizer.pkl')
        self.t_path = os.path.join(intents_path, 'tokenizer.pickle')
        self.UNK = 0
        self.PAD = 1
        self.START = 2

        # intent model variables
        #update method of predict call when updating model
        self.intent_load_model_from = os.path.join(intents_path, 'pretrained_embeddings.h5')
        self.intent_load_intents_from = os.path.join(intents_path, 'intents_job_intents.json')
        self.intent_load_classes = os.path.join(intents_path, 'intents_classes.pkl')
        self.intent_load_words = os.path.join(intents_path, 'intents_words.pkl')

    def process_data(self, path):
        data = pd.read_csv(path)
        if self.mode =='train':
            data = pd.read_csv(path)
            data['in_response_to_tweet_id'].fillna(-12345, inplace=True)
            tweets_in = data[data['in_response_to_tweet_id'] == -12345]
            tweets_in_out = tweets_in.merge(data, left_on=['tweet_id'], right_on=['in_response_to_tweet_id'])
            return tweets_in_out[:self.num_train_records]
        elif self.mode == 'inference':
            return data

    def replace_anonymized_names(self, data):

        def replace_name(match):
            cname = match.group(2).lower()
            if not cname.isnumeric():
                return match.group(1) + match.group(2)
            return '@__cname__'

            re_pattern = re.compile('(@|Y@)([a-zA-Z0-9_]+)')
            if self.mode == 'train':
                in_text = data['text_x'].apply(lambda txt: re_pattern.sub(replace_name, txt))
                out_text = data['text_y'].apply(lambda txt: re_pattern.sub(replace_name, txt))
                return list(in_text.values), list(out_text.values)
            else:
                return list(map(lambda x: re_pattern.sub(replace_name, x), data))

    def tokenize_text(self, in_text, out_text):
        count_vectorizer = CountVectorizer(tokenizer=casual_tokenize, max_features=self.max_vocab_size - 3)
        count_vectorizer.fit(in_text + out_text)
        self.analyzer = count_vectorizer.build_analyzer()
        self.vocabulary = {key_: value_ + 3 for key_, value_ in count_vectorizer.vocabulary_.items()}
        self.vocabulary['UNK'] = self.UNK
        self.vocabulary['PAD'] = self.PAD
        self.vocabulary['START'] = self.START
        self.reverse_vocabulary = {value_: key_ for key_, value_ in self.vocabulary.items()}
        joblib.dump(self.vocabulary, self.outpath + 'vocabulary.pkl')
        joblib.dump(self.reverse_vocabulary, self.outpath + 'reverse_vocabulary.pkl')
        joblib.dump(count_vectorizer, self.outpath + 'count_vectorizer.pkl')

    def words_to_indices(self, sent):
        word_indices = [self.vocabulary.get(token, self.UNK) for token in self.analyzer(sent)] + [self.PAD] * self.max_seq_len
        word_indices = word_indices[:self.max_seq_len]
        return word_indices

    def indices_to_words(self, indices):
        return ' '.join(self.reverse_vocabulary[id] for id in indices if id != self.PAD).strip()

    def data_transform(self, in_text, out_text):
        X = [self.words_to_indices(s) for s in in_text]
        Y = [self.words_to_indices(s) for s in out_text]
        return np.array(X), np.array(Y)

    def train_test_split_(self, X, Y):
        X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.25, random_state=0)
        y_train = y_train[:, :, np.newaxis]
        y_test = y_test[:, :, np.newaxis]
        return X_train, X_test, y_train, y_test

    def data_creation(self):
        data = self.process_data(self.data_path)
        in_text, out_text = self.replace_anonymized_names(data)
        test_sentences = []
        test_indexes = np.random.randint(1, self.num_train_records, 10)
        for ind in test_indexes:
            sent = in_text[ind]
            test_sentences.append(sent)
        self.tokenize_text(in_text, out_text)
        X, Y = self.data_transform(in_text, out_text)
        X_train, X_test, y_train, y_test = self.train_test_split_(X, Y)
        return X_train, X_test, y_train, y_test, test_sentences

    def define_model(self):

        # Embedding Layer
        embedding = Embedding(
            output_dim=self.embedding_dim,
            input_dim=self.max_vocab_size,
            input_length=self.max_seq_len,
            name='embedding',
        )
        # Encoder input
        encoder_input = Input(
            shape=(self.max_seq_len,),
            dtype='int32',
            name='encoder_input',
        )
        embedded_input = embedding(encoder_input)

        encoder_rnn = LSTM(
            self.hidden_state_dim,
            name='encoder',
            dropout=self.dropout
        )

        # Context is repeated to the max sequence length so that the same context
        # can be feed at each step of decoder
        context = RepeatVector(self.max_seq_len)(encoder_rnn(embedded_input))

        # Decoder
        last_word_input = Input(
            shape=(self.max_seq_len,),
            dtype='int32',
            name='last_word_input',
        )

        embedded_last_word = embedding(last_word_input)
        # Combines the context produced by the encoder and the last word uttered as inputs
        # to the decoder.

        decoder_input = concatenate([embedded_last_word, context], axis=2)

        # return_sequences causes LSTM to produce one output per timestep instead of one at the
        # end of the input, which is important for sequence producing models.
        decoder_rnn = LSTM(
            self.hidden_state_dim,
            name='decoder',
            return_sequences=True,
            dropout=self.dropout
        )

        decoder_output = decoder_rnn(decoder_input)

        #TimeDistributed allows the dense layer to be applied to each decoder output per timestep
        next_word_dense = TimeDistributed(
            Dense(int(self.max_vocab_size / 20), activation='relu'),
            name='next_word_dense',
        )(decoder_output)

        next_word = TimeDistributed(
            Dense(self.max_vocab_size, activation='softmax'),
            name='next_word_softmax'
        )(next_word_dense)

        return Model(inputs=[encoder_input, last_word_input], outputs=[next_word])

    def create_model(self):
        _model_ = self.define_model()
        adam = Adam(learning_rate=self.learning_rate, clipvalue=5.0)
        _model_.compile(optimizer=adam, loss='sparse_categorical_crossentropy')
        return _model_

    # Function to append the START indext to the response Y
    def include_start_token(self, Y):
        print(Y.shape)
        Y = Y.reshape((Y.shape[0], Y.shape[1]))
        Y = np.hstack((self.START * np.ones((Y.shape[0], 1)), Y[:, :-1]))
        # Y = Y[:,:,np.newaxis]
        return Y

    def binarize_output_response(self, Y):
        return np.array([np_utils.to_categorical(row, num_classes=self.max_vocab_size)
                        for row in Y])

    def respond_to_input(self, model, input_sent):
        input_y = self.include_start_token(self.PAD *np.ones((1, self.max_seq_len)))
        ids = np.array(self.words_to_indices(input_sent)).reshape((1, self.max_seq_len))
        for pos in range(self.max_seq_len - 1):
            pred = model.predict([ids, input_y]).argmax(axis=2)[0]
            # pred = model.predict([ids, input_y])[0]
            input_y[:, pos + 1] = pred[pos]
        return self.indices_to_words(model.predict([ids, input_y]).argmax(axis=2)[0])

    def train_model(self, model, X_train, X_test, y_train, y_test):
        input_y_train = self.include_start_token(y_train)
        print(input_y_train.shape)
        input_y_test = self.include_start_token(y_test)
        print(input_y_test.shape)
        early = EarlyStopping(monitor='val_loss', patience=10, mode='auto')

        checkpoint = ModelCheckpoint(self.outpath + 's2s_model_' + str(self.version) + '_.h5', monitor='val_loss',
                                     verbose=1, save_best_only=True, mode='auto')

        lr_reduce = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2, verbose=0, mode='auto')

        model.fit([X_train, input_y_train], y_train,
                   epochs=self.epochs,
                   batch_size=self.batch_size,
                   validation_data=([X_test, input_y_test], y_test),
                   callbacks=[early, checkpoint, lr_reduce],
                   shuffle=True)

        return model

    def generate_response(self, model, sentences):
        output_responses = []
        print(sentences)
        for sent in sentences:
            response = self.respond_to_input(model, sent)
            output_responses.append(response)
        out_df = pd.DataFrame()
        out_df['Tweet in'] = sentences
        out_df['Tweet out'] = output_responses
        return out_df

    def convert_to_sequence(self, sentence):
        print(f'Sentence 2: {sentence}')
        print(f'Sentence list: {[sentence]}')
        sequence = self.tkizer.texts_to_sequences([sentence])
        
        print(f'Initial Tokenization: {sequence}')
        sequence = pad_sequences(sequence, maxlen=25)
        print
        #sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
        return sequence

    # return bag of words array: 0 or 1 for each word in the bag that exists in the sentence
    def word_embedding(self, sentence, intent_words, show_details=True):
        # tokenize the pattern
        # intent words = all words
        print(f'Sentence 1: {sentence}')
        sequence = self.convert_to_sequence(sentence)
        # bag of words - matrix of N words, vocabulary matrix

        return(sequence)
    
    def clean_up_sentence(self, sentence):
        sentence_words = nltk.word_tokenize(sentence)
        sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
        return sentence_words

    # return bag of words array: 0 or 1 for each word in the bag that exists in the sentence
    def bow(self, sentence, intent_words, show_details=True):
        # tokenize the pattern
        sentence_words = self.clean_up_sentence(sentence)
        # bag of words - matrix of N words, vocabulary matrix
        bag = [0]*len(intent_words)
        for s in sentence_words:
            for i,w in enumerate(intent_words):
                if w == s:
                    # assign 1 if current word is in the vocabulary position
                    bag[i] = 1
                    if show_details:
                        print('found in bag: %s' % w)
        return(np.array(bag))

    def predict_class(self, sentence, model, method):
        if method == 'WE':
            # filter predictions below a threshold
            # sentence is usertext
            # intent words are all the words
            print(f'sentence: {sentence}')
            sequence = self.word_embedding(sentence, self.intent_words, show_details=False)
            print(f'final sequence: {sequence}')
            res = model.predict(np.array(sequence))[0]
            print(f'res: {res}')
            ERROR_THRESHOLD = 0.25
            results = [[i,r] for i,r in enumerate(res) if r>ERROR_THRESHOLD]
            print(f'results: {results}')
            # sort by strength of probability
            results.sort(key=lambda x: x[1], reverse=True)
            return_list = []
            print(f'return_list: {return_list}')
            for r in results:
                return_list.append({'intent': self.intent_classes[r[0]], 'probability': str(r[1])})
            print(f'return_list: {return_list}')
            return return_list
        
        if method == 'BOW':
            # filter predictions below a threshold
            p = self.bow(sentence, self.intent_words, show_details=False)
            res = model.predict(np.array([p]))[0]
            ERROR_THRESHOLD = 0.25
            results = [[i,r] for i,r in enumerate(res) if r>ERROR_THRESHOLD]
            # sort by strength of probability
            results.sort(key=lambda x: x[1], reverse=True)
            return_list = []
            for r in results:
                return_list.append({'intent': self.intent_classes[r[0]], 'probability': str(r[1])})
            return return_list


    def getResponse(self, ints, intents_json):
        tag = ints[0]['intent']
        list_of_intents = intents_json['intents']
        for i in list_of_intents:
            if(i['tag'] == tag):
                result = random.choice(i['responses'])
                break
            else:
                result = 'I do not understand. Please input a different message.'
        return result

    def string_clean(self, response_orig):

        def upper_repl(match):
            punctuated_inits = \
                '-' + match.group(1).upper() + '.' \
                     + match.group(2).upper() + '.'
            return punctuated_inits

        response = response_orig
        sent_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
        # remove '@__cname__'
        response = response.replace('@__cname__ ', '')
        
        # remove spaces before punctuation
        response = re.sub(r'\s([,?.!"](?:\s|$))', r'\1', response)
        # tokenize sentences
        sentences = sent_tokenizer.tokenize(response)
        # captialize senteces
        sentences = [sent.capitalize() for sent in sentences]

        # add html formatting
        sentences = '</span><br><span>'.join(sentences)
        sentences += '</span>'
        # capitalize DM
        sentences = sentences.replace('dm', 'dm'.upper())

        # replace '^' with '-'
        sentences = sentences.replace('^', '-')
        pattern = re.compile(r'- \b([a-z])([a-z])\b')

        sentences = re.sub(pattern, upper_repl, sentences)
        return sentences

    def main(self):
        if self.mode == 'train':
            X_train, X_test, y_train, y_test, test_sentences = self.data_creation()
            print(X_train.shape, y_train.shape, X_test.shape, y_test.shape)
            print('Data Creation completed')
            model = self.create_model()
            print('Model creation completed')
            model = self.train_model(model, X_train, X_test, y_train, y_test)
            test_responses = self.generate_response(model, test_sentences)
            print(test_sentences)
            print(test_responses)
            pd.DataFrame(test_responses).to_csv(self.outpath + 'output_response.csv', index=False)
     
        elif self.mode == 'inference':
            #seq2seq model
            model = load_model(self.load_model_from)
            self.vocabulary = joblib.load(os.path.join(self.outpath, 'vocabulary.pkl'))
            self.reverse_vocabulary = joblib.load(os.path.join(self.outpath, 'reverse_vocabulary.pkl'))
            count_vectorizer = joblib.load(os.path.join(self.outpath, 'count_vectorizer.pkl'))
            self.analyzer = count_vectorizer.build_analyzer()

            #load intent model
            intent_model = load_model(self.intent_load_model_from)
            self.intent_intents = json.loads(open(self.intent_load_intents_from, encoding='cp1252').read())
            self.intent_words = pickle.load(open(self.intent_load_words,'rb'))
            self.intent_classes = pickle.load(open(self.intent_load_classes,'rb'))
            self.tkizer = pickle.load(open(self.t_path,'rb'))

            while True:
                try:
                    userText = request.args.get('msg')
                    ints = self.predict_class(userText, intent_model, method='WE')
                    intent_response = self.getResponse(ints, self.intent_intents)
                    if (intent_response != 'help'):
                        return str(intent_response)
                    elif (intent_response == 'help'):
                        response = self.respond_to_input(model, userText)
                        response = self.string_clean(response)
                        return str(response)

                except(KeyboardInterrupt, EOFError, SystemExit):
                    break

        

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get")
def get_bot_response():
    obj = chatbot()
    obj.mode = 'inference'
    response = obj.main()
    return response

if __name__ == "__main__":
    app.run()
