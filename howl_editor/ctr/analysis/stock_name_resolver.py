# coding: utf-8

from howl_editor.ctr import stock_names


class StockNameResolver:

    def bank_name(self, index: int) -> str:
        if index >= stock_names.FIRST_CUSTOM_BANK:
            return stock_names.CUSTOM_LABEL

        return stock_names.BANK_NAMES.get(index, "")

    def song_name(self, index: int) -> str:
        if index >= stock_names.FIRST_CUSTOM_SONG:
            return stock_names.CUSTOM_LABEL

        return stock_names.SONG_NAMES.get(index, "")
