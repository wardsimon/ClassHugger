__author__ = 'github.com/wardsimon'
__version__ = '0.0.1'

#   Licensed under the GNU General Public License v3.0
#   Copyright (c) of the author (github.com/wardsimon)
#   Created: 6/3/2020.

from hugger import ClassHugger

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

    @classmethod
    def default(cls, value):
        obj = cls()
        obj._a = value
        return obj

    @staticmethod
    def can():
        return 'TEXT'

    def maker(self):
        self.bar()
        return dict()


if __name__ == '__main__':

    print('# Run file\n')

    hugger = ClassHugger(debug=False)
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

    boo2 = Foo.default(3)
    can = boo2.can()

    d = dict()
    boo2.bam = boo

    boo2.maker()

    script = hugger.makeScript()

    print('\n')
    print(script)
