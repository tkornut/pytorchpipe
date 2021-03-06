#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) tkornuta, IBM Corporation 2019
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = "Tomasz Kornuta"


import torch

from ptp.components.models.model import Model
from ptp.components.mixins.word_mappings import WordMappings
from ptp.data_types.data_definition import DataDefinition

import ptp.components.utils.embeddings as emb


class SentenceEmbeddings(Model, WordMappings):
    """
    Model responsible of embedding of whole sentences.

    For this purpose it:
        - creates its own vocabulary,
        - splits sentences into tokens (using NLTK tokenizer),
        - uses vocabulary to first transform tokens (one by one) to indices (first) and dense vectors (next).

    Optionally, it can load pretrained word embeddings (currently GloVe).

    """ 
    def __init__(self, name, config):
        """
        Initializes the ``SentenceEmbeddings`` layer.

        :param name: Name of the model (taken from the configuration file).

        :param config: Parameters read from configuration file.
        :type config: ``ptp.configuration.ConfigInterface``
        """
        # Call base class constructors.
        Model.__init__(self, name, SentenceEmbeddings, config)
        WordMappings.__init__(self, name, SentenceEmbeddings, config)

        # Set key mappings.
        self.key_inputs = self.stream_keys["inputs"]
        self.key_outputs = self.stream_keys["outputs"]

        # Retrieve embeddings size from configuration and export it to globals.
        self.embeddings_size = self.config['embeddings_size']
        self.globals["embeddings_size"] = self.embeddings_size

        # Create the embeddings layer.
        self.logger.info("Initializing embeddings layer with vocabulary size = {} and embeddings size = {}".format(len(self.word_to_ix), self.embeddings_size))
        self.embeddings = torch.nn.Embedding(len(self.word_to_ix), self.embeddings_size, padding_idx=0) # Index of self.word_to_ix['<PAD>']

        # Load the embeddings first.
        if self.config["pretrained_embeddings_file"] != '':
            emb_vectors = emb.load_pretrained_glove_vectors(self.logger, self.data_folder, self.config["pretrained_embeddings_file"], self.word_to_ix, self.embeddings_size)
            self.embeddings.weight = torch.nn.Parameter(emb_vectors)


    def input_data_definitions(self):
        """ 
        Function returns a dictionary with definitions of input data that are required by the component.

        :return: dictionary containing input data definitions (each of type :py:class:`ptp.utils.DataDefinition`).
        """
        return {
            self.key_inputs: DataDefinition([-1, -1, 1], [list, list, str], "Batch of sentences, each represented as a list of words [BATCH_SIZE] x [SEQ_LENGTH] x [string]")
            }


    def output_data_definitions(self):
        """ 
        Function returns a dictionary with definitions of output data produced the component.

        :return: dictionary containing output data definitions (each of type :py:class:`ptp.utils.DataDefinition`).
        """
        return {
            self.key_outputs: DataDefinition([-1, -1, self.embeddings_size], [torch.Tensor], "Batch of embedded sentences [BATCH_SIZE x SENTENCE_LENGTH x EMBEDDING_SIZE]")
            }


    def forward(self, data_dict):
        """
        Forward pass  - performs embedding.

        :param data_dict: DataDict({'images',**}), where:

            - inputs: expected tokenized sentences [BATCH_SIZE x SENTENCE_LENGTH] x [string]
            - outputs: added embedded sentences [BATCH_SIZE x SENTENCE_LENGTH x EMBEDDING_SIZE]

        :type data_dict: ``miprometheus.utils.DataDict``
        """

        # Unpack DataDict.
        inputs = data_dict[self.key_inputs]

        indices_list = []
        # Process samples 1 by one.
        for sample in inputs:
            assert isinstance(sample, (list,)), 'This embedder requires input sample to contain a list of words'
            # Process list.
            output_sample = []
            # Encode sample (list of words)
            for token in sample:
                # Get index.
                output_index = self.word_to_ix[token]
                # Add index to outputs.
                output_sample.append( output_index )

            #indices_list.append(self.app_state.FloatTensor(output_sample))
            indices_list.append(self.app_state.LongTensor(output_sample))

        # Create list of (index,len) tuples.
        #order_len = [(i, len(indices_list[i])) for i in range(len(indices_list))]

        # Sort by seq_length.
        #sorted_order_len = sorted(order_len, key=lambda x: x[1], reverse=True)

        # Now sort indices list.
        #sorted_indices_list = [indices_list[sorted_order_len[i][0]] for i in range(len(indices_list))]

        # Pad the indices list.
        #padded_indices = torch.nn.utils.rnn.pad_sequence(sorted_indices_list, batch_first=True)

        # Revert to the original batch order!!!
        #new_old_order = [(i, sorted_order_len[i][0]) for i in range(len(indices_list))]
        #sorted_new_old_order = sorted(new_old_order, key=lambda x: x[1])
        #unsorted_padded_indices = [padded_indices[sorted_new_old_order[i][0]] for i in range(len(indices_list))]
        
        # Change to tensor.
        #unsorted_padded_indices_tensor = torch.stack( [self.app_state.FloatTensor(lst) for lst in unsorted_padded_indices] )

        # Embedd indices.
        #embedds = self.embeddings(unsorted_padded_indices_tensor)

        padded_indices = torch.nn.utils.rnn.pad_sequence(indices_list, batch_first=True)
        embedds = self.embeddings(padded_indices)
        

        # Add embeddings to datadict.
        data_dict.extend({self.key_outputs: embedds})
