__author__ = 'github.com/wardsimon'
__version__ = '0.0.1'

import abc
import inspect
import sys
from collections import deque
from typing import NoReturn
from collections import Callable
from functools import wraps


class HuggerEntries:
    def __init__(self, obj, entries):
        self.type = None
        self.object = obj
        self.entries = entries
        if inspect.isclass(obj):
            self.type = 'class'
        elif inspect.isfunction(obj):
            self.type = 'function'

    def unpatch(self):
        for patch in self.entries:
            patch.restore()

    def patch(self):
        for patch in self.entries:
            patch.patch()


class HuggerStack:
    def __init__(self, debug=False):
        self.hugged = []
        self.debug = debug
        self.history = []
        self._create_list = []
        self._unique_args = []
        self._unique_rets = []
        self._var_ident = 'var_'
        self.__ret_ident = 'obj_'

    def patch_class(self, klass):
        # patcher_methods_pre = HugMethods(self, klass)
        patcher_init = HugInit(self, klass)
        patcher_getter_setter = HugGetSet(self, klass)
        self.hugged.append(HuggerEntries(klass, [patcher_init, patcher_getter_setter]))
        if self.debug:
            print(f'Class "{klass.__name__}" has been hugged.')

    def create_script(self):
        text = '# Auto generated script\n\n'
        for entry in self.history:
            text += entry
        return text

    def _append_args(self, *args, **kwargs):

        def check(res):
            return id(res) not in self._unique_rets and \
                   id(res) not in self._create_list and \
                   id(res) not in self._unique_args

        for arg in args:
            if self.__is_mutable(arg) and check(arg):
                self._unique_args.append(id(arg))
        for item in kwargs.values():
            if self.__is_mutable(item) and check(item):
                self._unique_args.append(id(item))

    def _append_create(self, obj):
        this_id = id(obj)
        if this_id not in self._create_list:
            self._create_list.append(this_id)

    def _append_result(self, result):
        ret = 0

        def check(res):
            return id(res) not in self._unique_rets and \
                   id(res) not in self._create_list and \
                   id(res) not in self._unique_args

        if isinstance(result, type(None)):
            return ret
        elif isinstance(result, tuple):
            for res in result:
                if self.__is_mutable(res) and check(res):
                    self._unique_rets.append(id(res))
            ret = len(result)
        else:
            if self.__is_mutable(result) and check(result):
                self._unique_rets.append(id(result))
            ret = 1
        return ret

    @staticmethod
    def __is_mutable(arg):
        ret = True
        if isinstance(arg, (int, float, complex, str, tuple, frozenset, bytes)):
            ret = False
        return ret

    @staticmethod
    def _caller_name(skip=2):
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


class HuggerCommand(metaclass=abc.ABCMeta):
    """
    The Command interface pattern
    """

    def __init__(self, parent, obj) -> NoReturn:
        self.parent = parent
        self._obj = obj
        self.calls = 0

    @abc.abstractmethod
    def patch(self) -> NoReturn:
        pass

    @abc.abstractmethod
    def restore(self) -> NoReturn:
        pass


class HugInit(HuggerCommand):
    def __init__(self, parent, klass: classmethod):
        super().__init__(parent, klass)
        self.old_init = klass.__init__
        self.patch()

    def patch(self) -> NoReturn:
        self._obj.__init__ = self.function()

    def restore(self) -> NoReturn:
        self._obj.__init__ = self.old_init

    def function(self):
        def inner(obj, *args, **kwargs):
            self.calls += 1
            self.parent._append_args(*args, **kwargs)
            if self.parent.debug:
                print(obj)
                print(f"{self._obj.__name__} is created with {args}, {kwargs}")
            self.old_init(obj, *args, **kwargs)
            self.parent._append_create(obj)
            self.parent.history.append(self.get_script_entry(obj, *args, **kwargs))

        return inner

    def get_script_entry(self, obj, *args, **kwargs) -> str:
        # No need for name checking on creator.
        temp = f'{self._obj.__name__.lower()}_{self.parent._create_list.index(id(obj))} = {self._obj.__name__}('
        for var in args:
            if id(var) in self.parent._unique_args:
                index = self.parent._unique_args.index(id(var))
                temp += f'{self.parent.__var_ident}{index}, '
            elif id(var) in self.parent._unique_rets:
                index = self.parent._unique_rets.index(id(var))
                temp += f'{self.parent.__var_ident}{index}, '
            elif id(var) in self.parent._create_list:
                index = self.parent._create_list.index(id(var))
                temp += f'{self._obj.__name__.lower()}_{index}, '
            else:
                if isinstance(var, str):
                    var = '"' + var + '"'
                temp += f'{var}, '
        if not kwargs:
            temp = temp[:-2]
        temp_i = 0
        for key, item in kwargs.items():
            if temp_i == 0 & len(args) > 0:
                temp += ', '
            if id(item) in self.parent._unique_args:
                index = self.parent._unique_args.index(id(item))
                temp += f'{key}={self.parent.__var_ident}{index}, '
            elif id(item) in self.parent._unique_rets:
                index = self.parent._unique_rets.index(id(item))
                temp += f'{key}={self.parent.__var_ident}{index}, '
            elif id(item) in self.parent._create_list:
                index = self.parent._create_list.index(id(item))
                temp += f'{key}={self._obj.__name__.lower()}_{index}, '
            else:
                if isinstance(item, str):
                    item = '"' + item + '"'
                temp += f'{key}={item}, '
            temp_i += 1
        if kwargs:
            temp = temp[:-2]
        temp += ')'
        return temp


class HugMethods(HuggerCommand):
    def __init__(self, parent, obj):
        super().__init__(parent, obj)

    def patch(self, this_dict=None) -> NoReturn:
        if this_dict is None:
            this_dict = self._obj.__dict__
        for key in this_dict.keys():
            if isinstance(this_dict[key], Callable):
                setattr(self._obj, key, self.fun_wrap(this_dict[key]))
            elif isinstance(this_dict[key], property):
                if this_dict[key].fget.__name__ != key:
                    setattr(self._obj, key,
                            property(self.fun_get_wrap(this_dict[key].fget, name=key),
                                     self.fun_set_wrap(this_dict[key].fset, name=key),
                                     this_dict[key].fdel))
                else:
                    setattr(self._obj, key,
                            property(self.fun_get_wrap(this_dict[key].fget), self.fun_set_wrap(this_dict[key].fset),
                                     this_dict[key].fdel))
            elif isinstance(this_dict[key], (classmethod, staticmethod)):
                setattr(self._obj, key, self.fun_wrap(this_dict[key], name=key))

    def fun_get_wrap(self, fun, name=None):
        if name is None:
            name = fun.__name__

        @wraps(fun)
        def inner(*args, **kwargs):
            self.parent._argument_checker(*args, **kwargs)
            if self.parent.debug:
                print(f"I''m {args[0]} and getting {name}")
            res = fun(*args, **kwargs)
            ret = self._argout(res)
            return res

        return inner

    def fun_set_wrap(self, fun, name=None):
        if name is None:
            name = fun.__name__

        def inner(*args, **kwargs):
            self.parent._argument_checker(*args, **kwargs)
            if self.parent.debug:
                print(f"I''m {args[0]} and getting {name}")
            return fun(*args, **kwargs)

        return inner

    def fun_wrap(self, fun, name=None):
        if name is None:
            name = fun.__name__

        if self.parent.debug:
            print(f"I''ve wrapped {self._obj.__name__}.{name}")

        @wraps(fun)
        def inner(*args, **kwargs):
            self.parent._argument_checker(*args, **kwargs)
            caller = self.parent._caller_name(skip=1)
            skip = False
            if self._obj.__name__ in caller:
                if self.parent.debug:
                    print(f"I've been called from {caller}")
                skip = True

            if name != 'patch_init':
                if self.parent.debug:
                    print(f"I''m {args[0]}.{name} and have been called with {args[1:]}, {kwargs}")
                if isinstance(fun, (classmethod, staticmethod)):
                    if isinstance(fun, classmethod):
                        res = getattr(fun, '__func__')(self._obj, *args, **kwargs)
                        if skip:
                            return res
                        self._count -= 1
                        ret = self._argout(res)
                        self._history[-1] = self._makeScriptEntry(self._obj, 'magic_method', *[name, *args[1:]],
                                                                  returns=ret, index=self._count, **kwargs)
                    else:
                        res = getattr(fun, '__func__')(*args[1:], **kwargs)
                        if skip:
                            return res
                        ret = self._argout(res)
                        self._history.append(self._makeScriptEntry(self._obj, 'magic_method', *[name, *args[1:]],
                                                                   returns=ret, index=self._count, **kwargs))
                else:
                    res = fun(*args, **kwargs)
                    if skip:
                        return res
                    ret = self._argout(res)
                    self._history.append(self._makeScriptEntry(self._obj, 'fn_call', *[args[0], name, *args[1:]],
                                                               returns=ret, **kwargs))
                return res
            return fun(*args, **kwargs)

        return inner


class HugGetSet(HuggerCommand):
    def __init__(self, parent, obj):
        super().__init__(parent, obj)
        self._old_set_attr = obj.__setattr__
        self._old_get_attr = obj.__getattribute__
        self.patch()

    def patch(self) -> NoReturn:
        self._obj.__setattr__ = self.set_wrapper(self._old_set_attr)
        self._obj.__getattribute__ = self.get_wrapper(self._old_get_attr)

    def restore(self) -> NoReturn:
        self._obj.__setattr__ = self._old_set_attr
        self._obj.__getattribute__ = self._old_get_attr

    @staticmethod
    def checker(this_fun, thisitem):
        return thisitem in this_fun.__dict__.keys()

    def get_wrapper(self, fun):
        @wraps(fun)
        def inner(*args, **kwargs):
            if args[1] == '__dict__':
                return fun(*args, **kwargs)
            if not self.checker(args[0], args[1]):
                return fun(*args, **kwargs)
            if isinstance(args[0].__dict__[args[1]], Callable):
                return fun(*args, **kwargs)
            if args[1][0] != '_' and self.parent.debug:
                print(f"I''m getting {args[0]}.{args[1]}")
            res = fun(*args, **kwargs)
            if id(res) not in self.parent._unique_rets:
                self.parent._unique_rets.append(id(res))
            self.parent.history.append(self.get_script_entry(args[0], res, *args[1:]))
            return res

        return inner

    def set_wrapper(self, fun):
        @wraps(fun)
        def inner(*args, **kwargs):
            if args[1] == '__dict__':
                return fun(*args, **kwargs)
            if not self.checker(args[0], args[1]):
                return fun(*args, **kwargs)
            if isinstance(args[0].__dict__[args[1]], Callable):
                return fun(*args, **kwargs)
            if args[1][0] != '_' and self.parent.debug:
                print(f"I''m setting {args[0]}.{args[1]} to {args[2]}")
            self.parent._append_args(*args, **kwargs)
            self.parent.history.append(self.set_script_entry(args[0], *args[1:]))
            return fun(*args, **kwargs)

        return inner

    def set_script_entry(self, obj, *args):
        class_obj_name = self._obj.__name__.lower()
        idx = self.parent._create_list.index(id(obj))
        call_prop = args[0]
        call_variable = args[1]
        temp = f'{class_obj_name}_{idx}.{call_prop} = '
        if id(call_variable) in self.parent._create_list:
            index = self.parent._create_list.index(id(call_variable))
            temp += f'{class_obj_name}_{index}'
        else:
            if id(call_variable) in self.parent._unique_args:
                index = self.parent._unique_args.index(id(call_variable))
                temp += f'{self.parent._var_ident}{index}'
            elif id(call_variable) in self.parent._unique_rets:
                index = self.parent._unique_rets.index(id(call_variable))
                temp += f'{self.parent._var_ident}{index}'
            else:
                if isinstance(call_variable, str):
                    call_variable = '"' + call_variable + '"'
                temp += f'{call_variable}'
        return temp

    def get_script_entry(self, obj, returned, *args):
        temp = ''
        if isinstance(returned, type(None)):
            return temp
        elif not isinstance(returned, tuple):
            returned = [returned]
        class_obj_name = self._obj.__name__.lower()
        idx = self.parent._create_list.index(id(obj))
        call_prop = args[0]
        for idx in range(len(returned)):
            if id(returned[idx]) in self.parent._unique_rets:
                index = self.parent._unique_rets.index(id(returned[idx]))
                temp += f'{self.parent._var_ident}{index}, '
        temp = temp[:-2]
        temp += f' = {class_obj_name}_{idx}.{call_prop}'
        return temp
