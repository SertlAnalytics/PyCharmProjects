"""
Description: This module contains the configuration tables for stock database
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-05-14
"""

from salesman_database.salesman_tables import SaleTable
from salesman_database.access_layer.access_layer_base import AccessLayer
from sertl_analytics.constants.salesman_constants import SLDC, SMVW, SLST


class AccessLayer4Sale(AccessLayer):
    @property
    def view_name(self):
        return SMVW.V_SALE

    def are_any_records_available_for_master_id(self, master_id: str):
        query = "SELECT * from {} WHERE {}='{}' and {}!='{}';".format(
            self.view_name, SLDC.MASTER_ID, master_id, SLDC.SALE_ID, master_id
        )
        df = self.__get_data_frame_with_row_id_by_query__(query)
        return df.shape[0] > 0

    def get_next_version_for_sale_id(self, sale_id: str) -> int:
        query = "SELECT {} FROM {} WHERE {}='{}';".format(
            SLDC.VERSION_MAX, SMVW.V_SALE_MAX_VERSION, SLDC.SALE_ID_MAX, sale_id
        )
        df = self.__get_data_frame_with_row_id_by_query__(query)
        if df.shape[0] == 0:
            return 1
        return int(df.iloc[0][SLDC.VERSION_MAX] + 1)

    def get_existing_sales_for_master_id(self, master_id: str):
        query = "SELECT * from {} WHERE {}='{}' AND {}!='{}';".format(
            self.view_name, SLDC.MASTER_ID, master_id, SLDC.SALE_ID, master_id
        )
        return self.select_data_by_query(query)

    def get_my_sales_as_data_frame(self):
        query = "SELECT * from {} WHERE {}={} ORDER BY {};".format(
            self.view_name, SLDC.MASTER_ID, SLDC.SALE_ID, SLDC.SALE_ID)
        return self.select_data_by_query(query)

    def get_my_sales_as_dd_options(self):
        df = self.get_my_sales_as_data_frame()
        option_list = []
        for idx, row in df.iterrows():
            label = '{}-{}'.format(row[SLDC.SALE_ID], row[SLDC.TITLE])
            option_list.append({'label': label, 'value': row[SLDC.ROW_ID]})
        return option_list

    def get_similar_sales_as_data_frame(self):
        query = "SELECT * from {} WHERE {}!={} ORDER BY {};".format(
            self.view_name, SLDC.MASTER_ID, SLDC.SALE_ID, SLDC.SALE_ID)
        return self.select_data_by_query(query)

    def is_sale_with_id_available(self, sale_id: str):
        query = "SELECT * from {} WHERE {}='{}';".format(self.view_name, SLDC.SALE_ID, sale_id)
        df = self.select_data_by_query(query)
        return df.shape[0] > 0

    def get_sale_by_id(self, sale_id: str):
        query = "SELECT * from {} WHERE {}='{}';".format(self.view_name, SLDC.SALE_ID, sale_id)
        return self.select_data_by_query(query)

    def get_sale_by_row_id(self, row_id: int):
        query = "SELECT * from {} WHERE {}='{}';".format(self.view_name, SLDC.ROW_ID, row_id)
        return self.select_data_by_query(query)

    def get_sales_df_by_sale_state(self, sale_state: str, only_own_sales: bool):
        only_own_part = " AND {}={}".format(SLDC.SALE_ID, SLDC.MASTER_ID) if only_own_sales else ''
        query = "SELECT * from {} WHERE {}='{}'{};".format(self.view_name, SLDC.SALE_STATE, sale_state, only_own_part)
        return self.select_data_by_query(query)

    def get_sales_df_by_master_sale_id(self, master_sale_id: str):
        query = "SELECT * from {} WHERE {}='{}' and {}='{}' and {}!={};".format(
            self.view_name, SLDC.MASTER_ID, master_sale_id, SLDC.SALE_STATE, SLST.OPEN, SLDC.SALE_ID, SLDC.MASTER_ID)
        return self.select_data_by_query(query)

    def delete_existing_sale_by_id(self, sale_id: str) -> int:
        query = "DELETE FROM {} WHERE {}='{}';".format(self._table.name, SLDC.SALE_ID, sale_id)
        print(query)
        return self._db.delete_records(query)

    def update_sale_last_check_date(self, sale_id: str, version: int, last_check_date: str) -> int:
        query = "UPDATE {} SET {} = '{}' WHERE {}='{}' and {}={};".format(
            self._table.name, SLDC.LAST_CHECK_DATE, last_check_date, SLDC.SALE_ID, sale_id, SLDC.VERSION, version)
        print(query)
        return self._db.update_table_by_statement(self._table.name, query)

    def change_sale_state_for_rowid_list(self, sale_state_new: str, row_id_list: list, last_check_date: str):
        row_ids = '({})'.format(','.join(row_id_list))
        query = "UPDATE {} SET {} = '{}', {} = '{}' WHERE {} in {};".format(
            self._table.name, SLDC.SALE_STATE, sale_state_new,
            SLDC.LAST_CHECK_DATE, last_check_date, SLDC.ROW_ID, row_ids)
        print(query)
        return self._db.update_table_by_statement(self._table.name, query)

    def change_sale_state(self, sale_id: str, version: int, sale_state: str, last_check_date: str):
        query = "UPDATE {} SET {} = '{}', {}='{}' WHERE {}='{}' and {}={};".format(
            self._table.name, SLDC.SALE_STATE, sale_state, SLDC.LAST_CHECK_DATE, last_check_date,
            SLDC.SALE_ID, sale_id, SLDC.VERSION, version)
        print(query)
        return self._db.update_table_by_statement(self._table.name, query)

    def __get_table__(self):
        return SaleTable()
