__author__ = 'github.com/wardsimon'
__version__ = '0.0.1'


class Borg:
    __log = []
    __debug = False
    __var_ident = 'var_'
    __ret_ident = 'ret_'

    # TODO These should be classed out
    __create_list = []
    __unique_args = []
    __unique_rets = []

    def __init__(self):
        self.log = self.__log
        self.debug = self.__debug
        self.create_list = self.__create_list
        self.unique_args = self.__unique_args
        self.unique_rets = self.__unique_rets
        self.var_ident = self.__var_ident
        self.ret_ident = self.__ret_ident
