__author__ = 'github.com/wardsimon'
__version__ = '0.0.1'

from hugger.Huggit import *


class ClassHugger(Hugger):

    __entries = [ClassInitHugger, PropertyHugger, AttributeHugger, ClassFunctionHugger]

    def __init__(self, klass: classmethod, auto_patch: bool = False):
        super().__init__()

        self.__results =

        self.patch_entries =
        self.patch_results = []

        self.klass = klass
        if auto_patch:
            self.patch()


    def patch(self):
        if len(self.patch_results) == 0:
            return
        for patch in self.patch_entries:
            self.patch_results.append(patch(self.klass))

    def restore(self):
        for patch in self.patch_results:
            patch.restore()

    def printLog(self):
        for log_line in self.log:
            print(log_line)
