# CSC525-Principles-of-ML-Chatbot

A repository containing all the files submitted for the student's portfolio project in CSC525 Principles of Machine Learning

## Files

The `colab/` directory contains .ipynb and .py versions of the colab notebooks.

The `data/` directory contains two subfolders, "intents/" and "seq2seq/," along with the "twcs.csv" (too large to push to GitHub) file.

* `intents/`
	* `BOW_embeddings.h5`
	* `intents_classes.pkl`
	* `intents_job_intents.json`
	* `intents_words.pkl`
	* `pretrained_embeddings.h5`
	* `tokenizer.pickle`
* `seq2seq/`
	* `count_vectorizer.pkl`
	* `reverse_vocabulary.pkl`
	* `s2s_model_v1_.h5` (too large to push to GitHub)
	* `vocabulary.pkl`

## Instructions

### Training

The models most likely need to be trained using the distributed, GPU-accelerated hardeware available through Google Colab Notebooks Pro.

To train the seq2seq (generative) model, the chatbot's mode needs to be updated in the `app.py` (for local implementations) or the `flask_chatterbot_simple.ipynb` file (when training using Colab Notebooks).

The retrieval-based model is trained through the `intents_train.py` file (locally) or the `intents_train.ipynb` file (using Colab Notebooks).

### Generating Responses

For the model to generate responses, the `app.py` (local) can be run as is, with the chatbot's mode set to `inference`.

If using Colab Notebooks, the `flask_chatterbot_simple.ipynb` file can be run as is, with the chatbot's mode set to `inference`.
