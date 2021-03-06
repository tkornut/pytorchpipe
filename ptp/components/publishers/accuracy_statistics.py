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
import math
import numpy as np

from ptp.components.component import Component
from ptp.data_types.data_definition import DataDefinition


class AccuracyStatistics(Component):
    """
    Class collecting statistics: batch size.

    """

    def __init__(self, name, config):
        """
        Initializes object.

        :param name: Loss name.
        :type name: str

        :param config: Dictionary of parameters (read from the configuration ``.yaml`` file).
        :type config: :py:class:`ptp.configuration.ConfigInterface`

        """
        # Call constructors of parent classes.
        Component.__init__(self, name, AccuracyStatistics, config)

        # Set key mappings.
        self.key_targets = self.stream_keys["targets"]
        self.key_predictions = self.stream_keys["predictions"]

        self.key_accuracy = self.statistics_keys["accuracy"]


    def input_data_definitions(self):
        """ 
        Function returns a dictionary with definitions of input data that are required by the component.

        :return: dictionary containing input data definitions (each of type :py:class:`ptp.utils.DataDefinition`).
        """
        return {
            self.key_targets: DataDefinition([-1], [torch.Tensor], "Batch of targets, each being a single index [BATCH_SIZE]"),
            self.key_predictions: DataDefinition([-1, -1], [torch.Tensor], "Batch of predictions, represented as tensor with probability distribution over classes [BATCH_SIZE x NUM_CLASSES]")
            }

    def output_data_definitions(self):
        """ 
        Function returns a empty dictionary with definitions of output data produced the component.

        :return: Empty dictionary.
        """
        return {}


    def __call__(self, data_dict):
        """
        Call method - empty for all statistics.
        """
        pass


    def calculate_accuracy(self, data_dict):
        """
        Calculates accuracy equal to mean number of correct classification in a given batch.

        :param data_dict: DataDict containing the targets.
        :type data_dict: DataDict

        :return: Accuracy.

        """
        # Get indices of the max log-probability.
        #pred = data_dict[self.key_predictions].max(1, keepdim=True)[1]
        preds = data_dict[self.key_predictions].max(1)[1]
        #print("Max: {} ".format(data_dict[self.key_predictions].max(1)[1]))

        # Calculate the number of correct predictinos.
        correct = preds.eq(data_dict[self.key_targets]).sum().item()
        #print ("TARGETS = ",data_dict[self.key_targets])
        #print ("PREDICTIONS = ",data_dict[self.key_predictions])
        #print ("MAX PREDICTIONS = ", preds)
        #print("CORRECTS = ", correct)

        #print(" Target: {}\n Prediction: {}\n Correct: {} ".format(data_dict[self.key_targets], preds, preds.eq(data_dict[self.key_targets])))

        # Normalize.
        batch_size = data_dict[self.key_predictions].shape[0]       
        accuracy = correct / batch_size
        #print("ACCURACY = ", accuracy)

        return accuracy


    def add_statistics(self, stat_col):
        """
        Adds 'accuracy' statistics to ``StatisticsCollector``.

        :param stat_col: ``StatisticsCollector``.

        """
        stat_col.add_statistics(self.key_accuracy, '{:6.4f}')

    def collect_statistics(self, stat_col, data_dict):
        """
        Collects statistics (batch_size) for given episode.

        :param stat_col: ``StatisticsCollector``.

        """
        stat_col[self.key_accuracy] = self.calculate_accuracy(data_dict)

    def add_aggregators(self, stat_agg):
        """
        Adds aggregator summing samples from all collected batches.

        :param stat_agg: ``StatisticsAggregator``.

        """
        stat_agg.add_aggregator(self.key_accuracy, '{:7.5f}')  # represents the average accuracy
        stat_agg.add_aggregator(self.key_accuracy+'_min', '{:7.5f}')
        stat_agg.add_aggregator(self.key_accuracy+'_max', '{:7.5f}')
        stat_agg.add_aggregator(self.key_accuracy+'_std', '{:7.5f}')


    def aggregate_statistics(self, stat_col, stat_agg):
        """
        Aggregates samples from all collected batches.

        :param stat_col: ``StatisticsCollector``

        :param stat_agg: ``StatisticsAggregator``

        """
        accuracies = stat_col[self.key_accuracy]

        # Check if batch size was collected.
        if "batch_size" in stat_col.keys():
            batch_sizes = stat_col['batch_size']

            # Calculate weighted precision.
            accuracies_avg = np.average(accuracies, weights=batch_sizes)
            accuracies_var = np.average((accuracies-accuracies_avg)**2, weights=batch_sizes)

            stat_agg[self.key_accuracy] = accuracies_avg
            stat_agg[self.key_accuracy+'_min'] = np.min(accuracies)
            stat_agg[self.key_accuracy+'_max'] = np.max(accuracies)
            stat_agg[self.key_accuracy+'_std'] = math.sqrt(accuracies_var)
        else:
            # Else: use simple mean.
            stat_agg[self.key_accuracy] = np.mean(accuracies)
            stat_agg[self.key_accuracy+'_min'] = np.min(accuracies)
            stat_agg[self.key_accuracy+'_max'] = np.max(accuracies)
            stat_agg[self.key_accuracy+'_std'] = np.std(accuracies)
            # But inform user about that!
            self.logger.warning("Aggregated statistics might contain errors due to the lack of information about sizes of aggregated batches")
