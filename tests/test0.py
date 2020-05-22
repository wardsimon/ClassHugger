__author__ = 'github.com/wardsimon'
__version__ = '0.0.1'

from hugger import FunctionHugger, PropertyHugger, ClassInitHugger, AttributeHugger


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

    f = ClassInitHugger(A)
    f.debug = True
    f.patch()

    f0 = AttributeHugger(A)
    f0.patch()

    a = A(a=1)

    ff = FunctionHugger(A.hello)
    ff.patch()

    a.hello()
    aa = A()

    ff2 = FunctionHugger(boo)
    ff2.patch()

    a_, b_ = boo()
    ff2.restore()
    a_, b_ = boo()

    p = PropertyHugger(A, 'boo')
    p.patch()
    v = a.boo

    f.restore()

    for line in f.log:
        print(line)
