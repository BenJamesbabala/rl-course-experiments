#!/usr/bin/python3

import tensorflow as tf
from agents.agent_states import LinearHiddenState
from rstools.tf.optimization import build_model_optimization

from agents.agent_networks import FeatureNet, QvalueNet, ValueNet


class DqnAgent(object):
    def __init__(self, state_shape, n_actions, network, special=None):
        self.special = special or {}
        self.state_shape = state_shape
        self.n_actions = n_actions
        self.special = special

        self.scope = tf.get_variable_scope().name + "/" + special.get("scope", "dqn") \
            if tf.get_variable_scope().name else special.get("scope", "dqn")

        with tf.variable_scope(self.scope):
            self._build_graph(network)

    def _build_graph(self, network):
        self.feature_net = FeatureNet(
            self.state_shape, network,
            self.special.get("feature_net", {}))

        self.hidden_state = LinearHiddenState(
            self.feature_net.feature_state,
            self.special.get("hidden_size", 512),
            self.special.get("hidden_activation", tf.nn.elu))

        if self.special.get("dueling_network", False):
            self.qvalue_net = QvalueNet(
                self.hidden_state.state, self.n_actions,
                dict(**self.special.get("qvalue_net", {}), **{"advantage": True}))
            self.value_net = ValueNet(
                self.hidden_state.state,
                self.special.get("value_net", {}))

            # a bit hacky way
            self.predicted_qvalues = self.value_net.predicted_values + \
                                     self.qvalue_net.predicted_qvalues
            self.predicted_qvalues_for_action = self.value_net.predicted_values_for_actions + \
                                                self.qvalue_net.predicted_qvalues_for_actions
            self.agent_loss = tf.losses.mean_squared_error(
                labels=self.qvalue_net.td_target,
                predictions=self.predicted_qvalues_for_action)

            build_model_optimization(
                self.value_net,
                self.special.get("value_net_optimization", None),
                loss=self.agent_loss)
        else:
            self.qvalue_net = QvalueNet(
                self.hidden_state.state, self.n_actions,
                self.special.get("qvalue_net", {}))
            self.predicted_qvalues = self.qvalue_net.predicted_qvalues
            self.predicted_qvalues_for_action = self.qvalue_net.predicted_qvalues_for_actions
            self.agent_loss = self.qvalue_net.loss

        build_model_optimization(
            self.qvalue_net,
            self.special.get("qvalue_net_optimization", None))

        build_model_optimization(
            self.hidden_state,
            self.special.get("hidden_state_optimization", None),
            loss=self.agent_loss)
        build_model_optimization(
            self.feature_net,
            self.special.get("feature_net_optimization", None),
            loss=self.agent_loss)

    def predict_qvalues(self, sess, state_batch):
        return sess.run(
            self.predicted_qvalues,
            feed_dict={
                self.feature_net.states: state_batch,
                self.feature_net.is_training: False})
