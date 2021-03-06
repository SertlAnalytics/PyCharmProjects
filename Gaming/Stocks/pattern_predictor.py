"""
Description: This module is the central modul for prediction pattern detection application.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-08-22
"""

from sertl_analytics.constants.pattern_constants import FT, STBL, PRED, DC
from sertl_analytics.models.nn_collector import NearestNeighborCollector
import numpy as np
import pandas as pd
from pattern_database.stock_database import StockDatabase, PatternTable, TradeTable
from pattern_database.stock_access_layer_prediction import AccessLayerPrediction
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.model_selection import train_test_split
from pattern_configuration import PatternConfiguration
from pattern_predictor_optimizer import PatternPredictorOptimizer
from sertl_analytics.mymath import EntropyHandler


class PatternPredictorApi:
    def __init__(self, config: PatternConfiguration, db_stock: StockDatabase,
                 pattern_table: PatternTable, trade_table: TradeTable):
        self.config = config
        self.db_stock = db_stock
        self.pattern_table = pattern_table
        self.trade_table = trade_table
        self.predictor_optimizer = None  # will be set in the script where api is initiated


class PatternFeaturesSelector:
    def __init__(self, _df_features_with_label: pd.DataFrame, label_columns: list, features_columns_orig: list):
        self._df_features_with_label = _df_features_with_label
        self._label_columns = label_columns
        self._features_columns_orig = features_columns_orig
        self._features_columns = self._features_columns_orig  # default
        self._label_feature_information_gain_dict = {}
        self._entropy_handler = EntropyHandler(
            self._df_features_with_label, self._label_columns, self._features_columns_orig)

    @property
    def features_columns(self) -> list:
        return self._features_columns

    def calculate_information_gain_for_feature_columns(self):
        if self._df_features_with_label.shape[0] == 0:
            return
        for label in self._label_columns:
            for feature in self._features_columns_orig:
                information_gain = self._entropy_handler.calculate_information_gain_for_label_and_feature(label, feature)
                print('label={}, feature={}: information_gain={}'.format(label, feature, information_gain))


class PatternPredictor:
    """
    This class is not only one master_predictor but a collection of predictors for a dedicated pattern type and
    several labels. As a result: the method predict returns a value for each of this labels.
    """
    def __init__(self, optimizer: PatternPredictorOptimizer, pattern_type: str, skip_condition_list=None):
        # print('Loading Predictor: {}'.format(self.__class__.__name__))
        self._use_optimizer = False
        self._predictor = self.__class__.__name__
        self._optimizer = optimizer
        self._db_stock = self._optimizer.db_stock
        self._access_layer_prediction = AccessLayerPrediction(self._db_stock)
        self._pattern_type = pattern_type
        self._skip_condition_list = skip_condition_list
        self._df_features_with_labels_and_id = self.__get_df_features_with_labels__()
        self._feature_table = self.__get_table_with_prediction_features__()
        self._features_columns_orig = self.__get_feature_columns_orig__()
        self._label_columns = self.__get_label_columns__()
        self._predictor_dict = self.__get_predictor_dict__()
        self._feature_columns = self.__get_feature_columns_by_information_gain__()
        self._neighbor_collector = None
        self._is_ready_for_prediction = True  # default
        if self._df_features_with_labels_and_id.shape[0] == 0:
            self._is_ready_for_prediction = False
        else:
            self.__train_models__(False)
        # print('self.x_data.shape={}'.format(self._x_data.shape))

    @property
    def predictor(self):
        return ''

    @property
    def pattern_type(self):
        return self._pattern_type

    @property
    def label_columns(self):
        return self._label_columns

    @property
    def feature_table_name(self):
        return ''

    @property
    def feature_columns(self):
        return self._feature_columns

    @property
    def is_ready_for_prediction(self):
        return self._is_ready_for_prediction

    def get_sorted_nearest_neighbor_entry_list_for_previous_prediction(self):
        return self._neighbor_collector.get_sorted_entry_list()

    def __get_df_features_with_labels__(self):
        return self._access_layer_prediction.get_df_features_and_labels_for_predictor(
            self.feature_table_name, self.predictor, self._pattern_type, self._skip_condition_list)

    def __get_feature_columns_by_information_gain__(self) -> list:
        if self._df_features_with_labels_and_id.shape[0] == 0 or True:
            return self._features_columns_orig
        entropy_handler = EntropyHandler(self._df_features_with_labels_and_id,
                                         self._label_columns, self._features_columns_orig)
        for label in self._label_columns:
            for feature in self._features_columns_orig:
                information_gain = entropy_handler.calculate_information_gain_for_label_and_feature(label, feature)
                if len(information_gain) > 1:
                    print('{}: label={}, feature={}: information_gain={}'.format(
                        self.__class__.__name__, label, feature, information_gain))
        return self._features_columns_orig

    def predict_for_label_columns(self, x_data: list):
        np_array = np.array(x_data)
        np_array = np_array.reshape(1, np_array.size)
        return_dict = {}
        collector_id = '{}_{}'.format(self.__class__.__name__, self._pattern_type)
        self._neighbor_collector = NearestNeighborCollector(self._df_features_with_labels_and_id, collector_id)
        for label in self._label_columns:
            # if label == DC.TICKS_FROM_BREAKOUT_TILL_POSITIVE_HALF:
            #     print(label)
            if self.is_ready_for_prediction:
                try:
                    prediction = self._predictor_dict[label].predict(np_array)[0]
                except ValueError:
                    print('ERROR: Prediction problem with label {} and array {} - set to 0...'.format(label, np_array))
                    prediction = 0
                dist, ind = self._predictor_dict[label].kneighbors(np_array)
                self._neighbor_collector.add_dist_ind_array(ind, dist)
                if self._use_optimizer:
                    prediction_optimal = self._optimizer.get_optimal_prediction(
                        self.feature_table_name, self.predictor, label, self._pattern_type, np_array)
                    if prediction_optimal != 0:
                        prediction = prediction_optimal
            else:
                prediction = 0
            if self._feature_table.is_label_column_for_regression(label):
                return_dict[label] = round(prediction, -1)
            else:
                return_dict[label] = int(prediction)
        return return_dict

    def __get_table_with_prediction_features__(self):
        pass

    def __get_feature_columns_orig__(self):
        return []

    def __get_label_columns__(self):
        return []

    def __get_predictor_dict__(self) -> dict:
        return {label: self.__get_predictor_for_label_column__(label) for label in self._label_columns}

    def __get_predictor_for_label_column__(self, label_column: str):
        if self._feature_table.is_label_column_for_regression(label_column):
            return KNeighborsRegressor(n_neighbors=7, weights='distance')
            # return RandomForestRegressor(n_estimators=3, random_state=42)
        else:
            return KNeighborsClassifier(n_neighbors=7, weights='distance')
            # return RandomForestClassifier(n_estimators=3, random_state=42)

    def __train_models__(self, perform_test=False):
        for label_columns in self._label_columns:
            self.__train_model__(label_columns, perform_test)

    def __train_model__(self, label_column: str, perform_test):
        x_train, y_train = self._access_layer_prediction.get_x_data_y_train_data_for_predictor(
            self.feature_table_name, self.predictor, label_column, self._pattern_type, self._skip_condition_list
        )
        if x_train.shape[0] < 10 or not self._is_ready_for_prediction:
            self._is_ready_for_prediction = False
            return
        predictor = self._predictor_dict[label_column]
        self.__train_predictor_for_label_column__(predictor, label_column, x_train, y_train, perform_test)

        if self._use_optimizer:
            self._optimizer.retrain_trained_models(
                self.feature_table_name, self.predictor, label_column, self._pattern_type, x_train, y_train)

    def __train_predictor_for_label_column__(self, predictor, label_column: str, x_train, y_train, perform_test: bool):
        if perform_test:
            self.__perform_test_on_training_data__(x_train, y_train, predictor, label_column)
        else:
            predictor.fit(x_train, y_train)
            self.__print_report__(x_train, y_train, predictor, label_column)

    def __perform_test_on_training_data__(self, x_input, y_input, predictor, label_column: str):
        X_train, X_test, y_train, y_test = train_test_split(x_input, y_input, test_size=0.3)
        predictor.fit(X_train, y_train)
        self.__print_report__(X_test, y_test, predictor, label_column)

    def __print_report__(self, x_input, y_input, predictor, label_column: str):
        rfc_pred = predictor.predict(x_input)
        if self._feature_table.is_label_column_for_regression(label_column):
            self.__print_prediction_details__(y_input, rfc_pred, True)
        else:
            self.__print_prediction_details__(y_input, rfc_pred, False)

    @staticmethod
    def __print_prediction_details__(y_input, v_predict, for_regression: bool):
        return
        for k in range(0, len(y_input)):
            if for_regression:
                print('{:6.2f} / {:6.2f}: diff = {:6.2f}'.format(y_input[k], v_predict[k], y_input[k]-v_predict[k]))
            else:
                print('{:2d} / {:2d}: diff = {:2d}'.format(y_input[k], v_predict[k], y_input[k] - v_predict[k]))


class PatternPredictorTouchPoints(PatternPredictor):
    @property
    def predictor(self):
        return PRED.TOUCH_POINT

    @property
    def feature_table_name(self):
        return STBL.PATTERN

    def __get_table_with_prediction_features__(self) -> PatternTable:
        return PatternTable()

    def __get_feature_columns_orig__(self):
        return self._feature_table.feature_columns_touch_points

    def __get_label_columns__(self):
        return self._feature_table.label_columns_touch_points


class PatternPredictorBeforeBreakout(PatternPredictor):
    @property
    def predictor(self):
        return PRED.BEFORE_BREAKOUT

    @property
    def feature_table_name(self):
        return STBL.PATTERN

    def __get_table_with_prediction_features__(self) -> PatternTable:
        return PatternTable()

    def __get_feature_columns_orig__(self):
        return self._feature_table.features_columns_before_breakout

    def __get_label_columns__(self):
        return self._feature_table.label_columns_before_breakout


class PatternPredictorAfterBreakout(PatternPredictor):
    @property
    def predictor(self):
        return PRED.AFTER_BREAKOUT

    @property
    def feature_table_name(self):
        return STBL.PATTERN

    def __get_table_with_prediction_features__(self) -> PatternTable:
        return PatternTable()

    def __get_feature_columns_orig__(self):
        return self._feature_table.features_columns_after_breakout

    def __get_label_columns__(self):
        return self._feature_table.label_columns_after_breakout


class PatternPredictorForTrades(PatternPredictor):
    @property
    def predictor(self):
        return PRED.FOR_TRADE

    @property
    def feature_table_name(self):
        return STBL.TRADE

    def __get_table_with_prediction_features__(self) -> TradeTable:
        return TradeTable()

    def __get_feature_columns_orig__(self):
        return self._feature_table.feature_columns_for_trades

    def __get_label_columns__(self):
        return self._feature_table.label_columns_for_trades


class PatternMasterPredictor:
    def __init__(self, api: PatternPredictorApi):
        self.config = api.config
        self.db_stock = api.db_stock
        self.pattern_table = api.pattern_table
        self.trade_table = api.trade_table
        self.predictor_optimizer = api.predictor_optimizer
        self._predictor_dict = {}
        self._skip_condition_list = None

    @property
    def table(self):
        return ''

    @property
    def predictor(self):
        return ''

    def get_feature_columns(self, pattern_type: str):
        predictor = self.__get_predictor_for_pattern_type__(pattern_type)
        return predictor.feature_columns

    def predict_for_label_columns(self, pattern_type: str, x_data: list):
        predictor = self.__get_predictor_for_pattern_type__(pattern_type)
        result_dict_for_one_predictor = predictor.predict_for_label_columns(x_data)
        if predictor.is_ready_for_prediction and False:  # ToDo any when....
            result_dict_for_optimal_predictor = self.predict_optimal_for_label_columns(
                pattern_type, x_data, predictor.label_columns)
            for labels in predictor.label_columns:
                print('Prediction-kNN={}, {}=optimal'.format(result_dict_for_one_predictor[labels],
                                                             result_dict_for_optimal_predictor[labels]))
        return result_dict_for_one_predictor

    def predict_optimal_for_label_columns(self, pattern_type: str, x_data: list, label_columns: list):
        return {label: self.predictor_optimizer.predict(self.table, self.predictor, label, pattern_type, x_data)
                for label in label_columns}

    def get_sorted_nearest_neighbor_entry_list(self, pattern_type: str):
        predictor = self.__get_predictor_for_pattern_type__(pattern_type)
        return predictor.get_sorted_nearest_neighbor_entry_list_for_previous_prediction()

    def init_without_condition_list(self, ticker_id: str, and_clause: str):
        self._skip_condition_list = self.__get_skip_condition_list__(ticker_id, and_clause)

    def __get_skip_condition_list__(self, ticker_id: str, and_clause: str) -> list:
        pass

    def __get_predictor_for_pattern_type__(self, pattern_type: str):
        if pattern_type not in self._predictor_dict:
            self._predictor_dict[pattern_type] = \
                self.__get_new_predictor_for_pattern_type__(pattern_type, self._skip_condition_list)
        return self._predictor_dict[pattern_type]

    def __get_new_predictor_for_pattern_type__(self, pattern_type: str, skip_condition_list: list):
        pass


class PatternMasterPredictorTouchPoints(PatternMasterPredictor):
    @property
    def table(self):
        return STBL.PATTERN

    @property
    def predictor(self):
        return PRED.TOUCH_POINT

    def __get_skip_condition_list__(self, ticker_id: str, and_clause: str) -> list:
        return ["Ticker_ID = '{}'".format(ticker_id), and_clause]

    def __get_new_predictor_for_pattern_type__(self, pattern_type: str, skip_condition_list: list):
        return PatternPredictorTouchPoints(self.predictor_optimizer, pattern_type, skip_condition_list)


class PatternMasterPredictorBeforeBreakout(PatternMasterPredictor):
    @property
    def table(self):
        return STBL.PATTERN

    @property
    def predictor(self):
        return PRED.BEFORE_BREAKOUT

    def __get_skip_condition_list__(self, ticker_id: str, and_clause: str) -> list:
        return ["Ticker_ID = '{}'".format(ticker_id), and_clause]

    def __get_new_predictor_for_pattern_type__(self, pattern_type: str, skip_condition_list: list):
        return PatternPredictorBeforeBreakout(self.predictor_optimizer, pattern_type, skip_condition_list)


class PatternMasterPredictorAfterBreakout(PatternMasterPredictor):
    @property
    def table(self):
        return STBL.PATTERN

    @property
    def predictor(self):
        return PRED.AFTER_BREAKOUT

    def __get_skip_condition_list__(self, ticker_id: str, and_clause: str) -> list:
        return ["Ticker_ID = '{}'".format(ticker_id), and_clause]

    def __get_new_predictor_for_pattern_type__(self, pattern_type: str, skip_condition_list: list):
        return PatternPredictorAfterBreakout(self.predictor_optimizer, pattern_type, skip_condition_list)


class PatternMasterPredictorForTrades(PatternMasterPredictor):
    @property
    def table(self):
        return STBL.TRADE

    @property
    def predictor(self):
        return PRED.FOR_TRADE

    def __get_skip_condition_list__(self, ticker_id: str, and_clause: str) -> list:
        return ["Ticker_ID = '{}'".format(ticker_id), and_clause]

    def __get_new_predictor_for_pattern_type__(self, pattern_type: str, skip_condition_list: list):
        return PatternPredictorForTrades(self.predictor_optimizer, pattern_type, skip_condition_list)


class PatternMasterPredictorHandler:
    def __init__(self, api: PatternPredictorApi):
        self.master_predictor_touch_points = PatternMasterPredictorTouchPoints(api)
        self.master_predictor_before_breakout = PatternMasterPredictorBeforeBreakout(api)
        self.master_predictor_after_breakout = PatternMasterPredictorAfterBreakout(api)
        self.master_predictor_for_trades = PatternMasterPredictorForTrades(api)

    def init_predictors_without_condition_list(self, ticker_id: str, and_clause_pattern: str, and_clause_trades: str):
        self.master_predictor_touch_points.init_without_condition_list(ticker_id, and_clause_pattern)
        self.master_predictor_before_breakout.init_without_condition_list(ticker_id, and_clause_pattern)
        self.master_predictor_after_breakout.init_without_condition_list(ticker_id, and_clause_pattern)
        self.master_predictor_for_trades.init_without_condition_list(ticker_id, and_clause_trades)

