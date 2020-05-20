#   Licensed under the GNU General Public License v3.0
#   Copyright (c) of the author (github.com/wardsimon)
#   Created: 18/5/2020.

__author__ = 'github.com/wardsimon'
__version__ = 'v0.0.1'

import inspect
import sys
from typing import Tuple
from collections.abc import Callable
from abc import ABCMeta, abstractmethod
from functools import wraps
from types import MethodType


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


class PatcherFactory(metaclass=ABCMeta):

    def __init__(self):
        self._store = Borg()

    @property
    def log(self) -> list:
        return self._store.log

    @property
    def debug(self) -> bool:
        return self._store.debug

    @debug.setter
    def debug(self, value: bool):
        self._store.debug = value

    @abstractmethod
    def patch(self):
        pass

    @abstractmethod
    def restore(self):
        pass

    @abstractmethod
    def makeEntry(self, obj, *args, **kwargs) -> str:
        pass

    @staticmethod
    def is_mutable(arg) -> bool:
        ret = True
        if isinstance(arg, (int, float, complex, str, tuple, frozenset, bytes, property)):
            ret = False
        return ret

    @staticmethod
    def _caller_name(skip: int = 2):
        """Get a name of a caller in the format module.class.method

           `skip` specifies how many levels of stack to skip while getting caller
           name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

           An empty string is returned if skipped levels exceed stack height

           https://gist.github.com/techtonik/2151727#gistcomment-2333747
        """

        def stack_(frame):
            framelist = []
            while frame:
                framelist.append(frame)
                frame = frame.f_back
            return framelist

        stack = stack_(sys._getframe(1))
        start = 0 + skip
        if len(stack) < start + 1:
            return ''
        parentframe = stack[start]

        name = []
        module = inspect.getmodule(parentframe)
        # `modname` can be None when frame is executed directly in console
        # TODO(techtonik): consider using __main__
        if module:
            name.append(module.__name__)
        # detect classname
        if 'self' in parentframe.f_locals:
            # I don't know any way to detect call from the object method
            # XXX: there seems to be no way to detect static method call - it will
            #      be just a function call
            name.append(parentframe.f_locals['self'].__class__.__name__)
        codename = parentframe.f_code.co_name
        if codename != '<module>':  # top level usually
            name.append(codename)  # function or a method
        del parentframe
        return ".".join(name)

    def _append_args(self, *args, **kwargs):

        def check(res):
            return id(res) not in self._store.unique_rets and \
                   id(res) not in self._store.create_list and \
                   id(res) not in self._store.unique_args

        for arg in args:
            if self.is_mutable(arg) and check(arg):
                self._store.unique_args.append(id(arg))
        for item in kwargs.values():
            if self.is_mutable(item) and check(item):
                self._store.unique_args.append(id(item))

    def _append_create(self, obj):
        this_id = id(obj)
        if this_id not in self._store.create_list:
            self._store.create_list.append(this_id)

    def _append_result(self, result) -> int:
        ret = 0

        def check(res):
            return id(res) not in self._store.unique_rets and \
                   id(res) not in self._store.create_list and \
                   id(res) not in self._store.unique_args

        if isinstance(result, type(None)):
            return ret
        elif isinstance(result, tuple):
            for res in result:
                # if self.is_mutable(res) and check(res):
                if check(res):
                    self._store.unique_rets.append(id(res))
            ret = len(result)
        else:
            # if self.is_mutable(result) and check(result):
            if check(result):
                self._store.unique_rets.append(id(result))
            ret = 1
        return ret

    def _append_log(self, log_entry: str):
        self._store.log.append(log_entry)

    def __options(self, item) -> Tuple[int, dict]:
        this_id = id(item)
        option = {
            'create_list': self._store.create_list,
            'return_list': self._store.unique_rets,
            'input_list': self._store.unique_args
        }
        return this_id, option

    def _get_position(self, query: str, item) -> int:
        this_id, option = self.__options(item)
        in_list = self._in_list(query, item)
        index = None
        if in_list:
            index = option.get(query).index(this_id)
        return index

    def _in_list(self, query: str, item) -> bool:
        this_id, option = self.__options(item)
        return this_id in option.get(query, [])

    @staticmethod
    def _get_class_that_defined_method(method_in) -> classmethod:
        if inspect.ismethod(method_in):
            for cls in inspect.getmro(method_in.__self__.__class__):
                if cls.__dict__.get(method_in.__name__) is method_in:
                    return cls
            method_in = method_in.__func__  # fallback to __qualname__ parsing
        if inspect.isfunction(method_in):
            class_name = method_in.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
            try:
                cls = getattr(inspect.getmodule(method_in), class_name)
            except AttributeError:
                cls = method_in.__globals__.get(class_name)
            if isinstance(cls, type):
                return cls
        return None  # not required since None would have been implicitly returned anyway


class ClassInitHugger(PatcherFactory):

    def __init__(self, klass: classmethod):
        super().__init__()
        self.klass = klass
        self.old_init = klass.__init__

    def patch(self):
        if self.debug:
            print(f"Class '{self.klass}' has been patched")
        self.klass.__init__ = self.patched_init()
        setattr(self.klass, 'hugger', self)

    def restore(self):
        if not hasattr(self.klass, 'hugger'):
            if self.debug:
                print(f"Class '{self.klass}'  has not been patched")
            return
        if self.debug:
            print(f"Class '{self.klass}'  has been un-patched")
        self.klass.__init__ = self.old_init
        delattr(self.klass, 'hugger')

    def patched_init(self):
        def inner(obj, *args, **kwargs):
            if self.debug:
                print(f"{self.klass.__name__} is created with {args}, {kwargs}")
            self.old_init(obj, *args, **kwargs)
            self._append_create(obj)
            self._append_args(*args, **kwargs)
            self._append_log(self.makeEntry(obj, *args, **kwargs))

        return inner

    def makeEntry(self, obj, *args, **kwargs) -> str:
        # No need for name checking on creator.
        temp = f'{self.klass.__name__.lower()}_{self._get_position("create_list", obj)} = {self.klass.__name__}('

        for var in args:
            if self._in_list('input_list', var):
                index = self._get_position("input_list", var)
                temp += f'{self._store.var_ident}{index}, '
            elif self._in_list('return_list', var):
                index = self._get_position("return_list", var)
                temp += f'{self._store.var_ident}{index}, '
            elif self._in_list('create_list', var):
                index = self._get_position("create_list", var)
                temp += f'{self.klass.__name__.lower()}_{index}, '
            else:
                if isinstance(var, str):
                    var = '"' + var + '"'
                temp += f'{var}, '
        if not kwargs and args:
            temp = temp[:-2]
        temp_i = 0
        for key, item in kwargs.items():
            if temp_i == 0 & len(args) > 0:
                temp += ', '
            if self._in_list('input_list', item):
                index = self._get_position("input_list", item)
                temp += f'{key}={self._store.var_ident}{index}, '
            elif self._in_list('return_list', item):
                index = self._get_position("return_list", item)
                temp += f'{key}={self._store.var_ident}{index}, '
            elif self._in_list('create_list', item):
                index = self._get_position("create_list", item)
                temp += f'{key}={self.klass.__name__.lower()}_{index}, '
            else:
                if isinstance(item, str):
                    item = '"' + item + '"'
                temp += f'{key}={item}, '
            temp_i += 1
        if kwargs:
            temp = temp[:-2]
        temp += ')'
        return temp


class FunctionHugger(PatcherFactory):

    def __init__(self, func: callable):
        super().__init__()
        self.func = func
        self.func_name = func.__name__
        self.klass = self._get_class_that_defined_method(func)

    def patch(self):
        if self.klass is None:
            self.func.__globals__[self.func_name] = self.patch_function()
        else:
            setattr(self.klass, self.func_name, self.patch_function())

    def restore(self):
        if self.klass is None:
            self.func.__globals__[self.func_name] = self.func
        else:
            setattr(self.klass, self.func_name, self.func)

    def makeEntry(self, returns, *args, **kwargs) -> str:
        temp = ''
        if returns is None:
            returns = []
        for var in returns:
            index = self._get_position("return_list", var)
            temp += f'{self._store.var_ident}{index}, '
        if len(returns) > 0:
            temp = temp[:-2]
            temp += ' = '
        if self.klass is None:
            temp += f'{self.func_name}('
        else:
            index = self._get_position("create_list", args[0])
            temp += f'{self.klass.__name__.lower()}_{index}.{self.func_name}('
            args = args[1:]
        for var in args:
            if self._in_list('input_list', var):
                index = self._get_position("input_list", var)
                temp += f'{self._store.var_ident}{index}, '
            elif self._in_list('return_list', var):
                index = self._get_position("return_list", var)
                temp += f'{self._store.var_ident}{index}, '
            elif self._in_list('create_list', var):
                index = self._get_position("create_list", var)
                temp += f'{self.klass.__name__.lower()}_{index}, '
            else:
                if isinstance(var, str):
                    var = '"' + var + '"'
                temp += f'{var}, '
        if len(args) > 0:
            temp = temp[:-2]
        first_item = True
        for key, item in kwargs.items():
            if first_item & len(args) > 0:
                temp += ', '
            if self._in_list('input_list', item):
                index = self._get_position("input_list", item)
                temp += f'{key}={self._store.var_ident}{index}, '
            elif self._in_list('return_list', item):
                index = self._get_position("return_list", item)
                temp += f'{key}={self._store.var_ident}{index}, '
            elif self._in_list('create_list', item):
                index = self._get_position("create_list", item)
                temp += f'{key}={self.klass.__name__.lower()}_{index}, '
            else:
                if isinstance(item, str):
                    item = '"' + item + '"'
                temp += f'{key}={item}, '
            first_item = False
        if kwargs:
            temp = temp[:-2]
        temp += ')'
        return temp

    def patch_function(self):
        @wraps(self.func)
        def inner(*args, **kwargs):
            caller = self._caller_name(skip=1)
            skip = False
            if self.klass is not None and self.klass.__name__ in caller:
                skip = True
            if self.debug:
                if len(args) > 0:
                    print(f"I'm {self.func.__qualname__} and have been called with {args[1:]}, {kwargs}")
                else:
                    print(f"I'm {self.func.__qualname__} and have been called")
            res = self.func(*args, **kwargs)
            if not skip:
                self._append_args(*args, **kwargs)
                self._append_result(res)
                self._append_log(self.makeEntry(res, *args, **kwargs))
            return res

        setattr(inner, 'hugger', self)
        return inner


class PropertyHugger(PatcherFactory):
    # Properties are immutable, so need to be set at the parent level. However unlike `FunctionHugger` we can't traverse
    # the stack to get the parent. So, it and it's name has to be set at initialization. Boo!

    def __init__(self, klass, prop_name):
        super().__init__()
        self.klass = klass
        self.prop_name = prop_name
        self.property = klass.__dict__.get(prop_name)
        self.property_old = {
            'fget': self.property.fget,
            'fset': self.property.fset,
            'fdel': self.property.fdel
        }
        self.__patch_ref = {
            'fget': {'old': self.property.fget, 'patcher': self.patch_get},
            'fset': {'old': self.property.fset, 'patcher': self.patch_set},
            'fdel': {'old': self.property.fdel, 'patcher': self.patch_del}
        }

    def patch(self):
        option = {}
        for key, item in self.property_old.items():
            func = getattr(self.property, key)
            if func is not None:
                patcher_details = self.__patch_ref.get(key)
                patch_function = patcher_details.get('patcher')
                new_func = patch_function(func)
                option[key] = new_func
        setattr(self.klass, self.prop_name, property(**option))

    def restore(self):
        setattr(self.klass, self.prop_name, self.property)

    def patch_get(self, func: Callable) -> Callable:
        @wraps(func)
        def inner(*args, **kwargs):
            if self.debug:
                print("I'm getting something")
            return func(*args, **kwargs)

        return inner

    def patch_set(self, func: Callable) -> Callable:
        @wraps(func)
        def inner(*args, **kwargs):
            if self.debug:
                print("I'm setting something")
            return func(*args, **kwargs)

        return inner

    def patch_del(self, func: Callable) -> Callable:
        @wraps(func)
        def inner(*args, **kwargs):
            if self.debug:
                print("I'm deleting something")
            return func(*args, **kwargs)

        return inner

    def makeEntry(self, obj, *args, **kwargs) -> str:
        pass


class AttributeHugger(PatcherFactory):
    # An attribute is a associated to a class and as such, the class' __getattr__ and __setattr__ should be overridden
    # https://docs.python.org/3/reference/datamodel.html#object.__set_name__

    def __init__(self, klass, exclude: list = None):
        super().__init__()
        self.klass = klass
        if exclude is None:
            exclude = []
        self.blacklist = exclude
        self._old_get_attr = self.klass.__getattribute__
        self._old_set_attr = self.klass.__setattr__

    def patch(self):
        self.klass.__getattribute__ = self.patch_getattr()
        self.klass.__setattr__ = self.patch_setattr()

    def restore(self):
        self.klass.__getattribute__ = self._old_get_attr
        self.klass.__setattr__ = self._old_set_attr

    def patch_getattr(self):
        pass

    def patch_setattr(self):
        pass

    def makeEntry(self, obj, *args, **kwargs) -> str:
        pass


if __name__ == "__main__":

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


    f = ClassInitHugger(A)
    f.debug = True
    f.patch()

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
