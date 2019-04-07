"""
Description: This module is the base class for our Tutti Salesman application.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2019-04-02
"""

from sertl_analytics.pyurl.url_process import MyUrlBrowser
from sertl_analytics.pyurl.url_username_passwords import WebPasswords
from tutti_offer import TuttiOffer
from tutti_constants import OCLS, SCLS
from time import sleep


class MyUrlBrowser4Tutti(MyUrlBrowser):
    def __init__(self, nlp):
        self._url_login = 'https://www.tutti.ch/de/start/login'
        self._url_search = 'https://www.tutti.ch/de/li'
        self._nlp = nlp
        MyUrlBrowser.__init__(self,  self._url_login, WebPasswords.TUTTI[0],  WebPasswords.TUTTI[1])

    def enter_and_submit_credentials(self):
        self.__enter_and_submit_credentials__()

    def __get_credential_values__(self) -> dict:
        return {'email': self._user_name, 'password': self._password}

    @staticmethod
    def get_url_for_offer_editing(offer_id: int):
        return 'https://www.tutti.ch/de/ai/start?load={}'.format(offer_id)

    def get_my_offers_from_tutti(self):
        return self.__get_offers_from_tutti__(OCLS.OFFERS)

    def get_my_nth_offer_from_tutti(self, number: int) -> TuttiOffer:
        return self.__get_nth_offer_from_tutti__(OCLS.OFFERS, number)

    def get_similar_offer_dict_from_tutti(self, offers: list):  # key is the ID of my_offer
        return {offer.id: self.__get_similar_offers_for_offer__(offer) for offer in offers}

    def __get_similar_offers_for_offer__(self, offer: TuttiOffer) -> list:
        similar_offer_dict = {}
        self.__open_search_site__()
        search_field = self.driver.find_element_by_name('search')
        start_search_label_lists = offer.get_start_search_label_lists()
        print('start_search_label_lists={}'.format(start_search_label_lists))
        for start_search_label_list in start_search_label_lists:
            self.__get_offers_from_tutti_for_next_search_level__(
                similar_offer_dict, start_search_label_list, offer, search_field)
        similar_offers_summary = [offer for offer in similar_offer_dict.values()]
        self.__print_similar_offers__(offer, similar_offers_summary)
        return similar_offers_summary

    def __get_offers_from_tutti_for_next_search_level__(
            self, similar_offer_dict: dict, parent_search_label_list: list, offer: TuttiOffer, search_field):
        search_string = ' '.join(parent_search_label_list)
        # print('search_string={}, parent_search_label_list={}'.format(search_string, parent_search_label_list))
        search_field.clear()
        search_field.send_keys(search_string)
        self.__click_search__()
        sleep(2)
        similar_offers = self.__get_offers_from_tutti__(SCLS.OFFERS, parent_search_label_list)
        added_flag = False
        for similar_offer in similar_offers:
            if self.__can_similar_offer_be_added_to_dict__(similar_offer_dict, offer, similar_offer):
                similar_offer_dict[similar_offer.id] = similar_offer
                added_flag = True
        if added_flag:  # recursive call !!!
            next_parent_search_label_list = offer.get_label_list_with_child_labels(parent_search_label_list)
            for search_label_list in next_parent_search_label_list:
                self.__get_offers_from_tutti_for_next_search_level__(
                    similar_offer_dict, search_label_list, offer, search_field)

    @staticmethod
    def __can_similar_offer_be_added_to_dict__(similar_offer_dict: dict, offer: TuttiOffer, similar_offer: TuttiOffer):
        if similar_offer.id == offer.id:
            return False
        if similar_offer.id not in similar_offer_dict:
            return True
        return len(similar_offer.found_by_labels) > len(similar_offer_dict[similar_offer.id].found_by_labels)

    @staticmethod
    def __print_similar_offers__(offer, similar_offers: list):
        offer.print_offer_in_original_structure()
        if len(similar_offers) == 0:
            print('\nNO SIMILAR OFFERS AVAILABLE for {}'.format(offer.key))
        for similar_offer in similar_offers:
            similar_offer.print_offer_in_original_structure()

    def check_current_offers_against_similar_offers(self):
        offers = self.__get_offers_from_tutti__(OCLS.OFFERS)
        # self.__open_search_site__()
        # self.__search_similar_offers__(offers)
        offer = offers[0]
        offer.price_new = 21
        self.__change_price_for_offer__(offer)

    def __click_submit__(self):
        xpath = '//*[@id="pageContainer"]/div[2]/div/div/div/div[3]/div/div/form/div[3]/button'
        link_einloggen = self.driver.find_element_by_xpath(xpath=xpath)
        link_einloggen.click()

    def __change_price_for_my_offers__(self, my_offers: list):
        for offer in my_offers:
            self.__change_price_for_offer__(offer)

    def __change_price_for_offer__(self, offer: TuttiOffer):
        if not offer.is_price_ready_for_update_in_tutti():
            return
        self.__open_site_for_editing__(offer.id)
        self.__click_next_page__()      # click "Nächste Seite"
        self.__enter_price_new__(offer.price_new)
        self.__click_next_page__()      # click "Nächste Seite"
        self.__click_next_page__()      # click "Vorschau"
        self.__click_next_page__()      # click "Nächste Seite"
        self.__publish_without_conditions__()  # click "Ohne Hervorhebung veröffentlichen"

    def __open_site_for_editing__(self, offer_id: int):
        self.driver.get(self.get_url_for_offer_editing(offer_id))

    def __enter_price_new__(self, price_new: float):
        price_field = self.driver.find_element_by_name('price')
        price_field.clear()
        price_field.send_keys(str(price_new))

    def __click_search__(self):
        xpath = '//*[@id="pageContainer"]/div[1]/div/div/header/div/div/div/div/div[2]/div/form/div/button'
        self.__find_button_by_xpath_and_press_click__(xpath)

    def __click_next_page__(self):
        xpath = '//*[@id="pageContainer"]/div[2]/div/div/div/div/form/div/div/button'
        self.__find_button_by_xpath_and_press_click__(xpath)

    def __publish_without_conditions__(self):
        xpath = '//*[@id="aiSubmitFree"]'
        self.__find_button_by_xpath_and_press_click__(xpath)

    def __get_offers_from_tutti__(self, class_name: str, search_labels=None) -> list:
        tutti_offers = []
        offer_elements = self.__get_offer_elements_by_class_name__(class_name)
        for offer_element in offer_elements:
            tutti_offer = self.__get_tutti_offer_from_offer_element__(offer_element, search_labels)
            tutti_offers.append(tutti_offer)
        return tutti_offers

    def __get_nth_offer_from_tutti__(self, class_name: str, number: int) -> TuttiOffer:
        offer_elements = self.__get_offer_elements_by_class_name__(class_name)
        if number - 1 < len(offer_elements):
            return self.__get_tutti_offer_from_offer_element__(offer_elements[number-1], None)

    def __get_tutti_offer_from_offer_element__(self, offer_element, search_labels):
        offer = TuttiOffer(self._nlp, search_labels)
        offer.init_by_offer_element(offer_element)
        return offer

    def __get_offer_elements_by_class_name__(self, class_name: str):
        return self.driver.find_elements_by_class_name(class_name)

    def __get_current_offer_elements_by_x_path__(self):
        xpath = '//*[@id="pageContainer"]/div[2]/div/div/div/div[2]/div/div[2]'
        return self.driver.find_element_by_xpath(xpath=xpath)

    def __open_search_site__(self):
        self.driver.get(self._url_search)
