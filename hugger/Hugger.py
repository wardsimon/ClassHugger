__author__ = 'github.com/wardsimon'
__version__ = '0.0.1'

from hugger.Huggit import *
from collections.abc import Mapping


class EntryManager(Mapping):
    def __init__(self, klass, entries: list):
        self.klass = klass
        self._entries = entries
        self._results = []
        for entry in self._entries:
            res = self.__def_patch_res()
            res['name'] = entry.__name__
            res['hugger'] = entry
            self._results.append(res)

    def __getitem__(self, key): # given a key, return it's value
        if 0 <= key < len(self._entries):
            return self._results[key]
        else:
            raise KeyError('Invalid key')

    def __iter__(self): # iterate over all keys
        for x in range(len(self._entries)):
            yield self._results[x]

    def __len__(self):
        return len(self._entries)

    @staticmethod
    def __def_patch_res():
        return {
                'name': None,
                'hugger': None,
                'hugged': None,
                'patched': False
            }


class ClassHugger(Hugger):

    __entries = [ClassInitHugger, ClassPropertyHugger, AttributeHugger, ClassFunctionHugger]

    def __init__(self, klass: classmethod, auto_patch: bool = False):
        super().__init__()

        self.patches = EntryManager(klass, self.__entries)
        self.klass = klass
        if auto_patch:
            self.patch()

    def patch(self):
        if len(self.patches) == 0:
            return
        for patch in self.patches:
            if not patch['patched']:
                if patch['hugged'] is None:
                    patch['hugged'] = patch['hugger'](self.klass)
                patch['hugged'].patch()
                patch['patched'] = True

    def restore(self):
        for patch in self.patches:
            if patch['patched']:
                patch['hugged'].restore()
                patch['patched'] = False

    def printLog(self):
        for log_line in self.log:
            print(log_line)
