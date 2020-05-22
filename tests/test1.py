__author__ = 'github.com/wardsimon'
__version__ = '0.0.1'

from hugger import ClassHugger, FunctionHugger


class A:
    def __init__(self, a=1):
        self.a = a

    def hello(self):
        print(self.a)

    @property
    def boo(self):
        return 'scared'


def boo():
    return 1, 2


if __name__ == "__main__":

    f = ClassHugger(A, auto_patch=False)
    f.debug = True
    f.patch()

    a = A(a=1)
    a.hello()
    aa = A()

    ff2 = FunctionHugger(boo)
    ff2.patch()

    a_, b_ = boo()
    ff2.restore()
    a_, b_ = boo()
    v = a.boo

    f.restore()

    f.printLog()
