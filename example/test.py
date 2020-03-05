__author__ = 'github.com/wardsimon'
__version__ = '0.0.1'

from ClassHugger import ClassHugger


class Foo:

    def __init__(self):
        self._a = 0
        self.b = 0
        setattr(self.__class__, 'c', property(lambda obj: print('Monkey')))

    def bar(self):
        pass

    @property
    def bam(self):
        print('Bam!')
        return self._a

    @bam.setter
    def bam(self, value):
        self._a = value

    def wham(self, value):
        return value

    def man(self, value):
        return value, value

    def ran(self, name='ban'):
        return name


if __name__ == '__main__':

    print('# Run file\n')

    hugger = ClassHugger()
    Foo = hugger.hug(Foo)
    boo = Foo()
    boo.bar()
    value = boo.bam
    boo.bam = 2
    boo.b = 5
    boo.c
    value = boo.wham(3)
    value = boo.man(2)
    value = boo.ran()
    value = boo.ran(name='fan')

    script = hugger.makeScript()

    print('\n')
    print(script)
