#   Licensed under the GNU General Public License v3.0
#   Copyright (c) of the author (github.com/wardsimon)
#   Created: 5/3/2020.

__author__ = 'github.com/wardsimon'
__version__ = '0.0.4'

import inspect
import sys

from functools import wraps
from typing import Callable


class BaseHugger:
    def __init__(self, debug=False):
        self._count = 0
        self._history = []
        self._create_list = []
        self._unique_vars = []
        self._unique_rets = []
        self.debug = debug
        self._old_set_attr = None
        self._old_get_attr = None
        self.__var_ident = 'var_'
        self.__ret_ident = 'obj_'

    def _argument_checker(self, *args, **kwargs):
        for arg in args:
            if self.__ismutalbe(arg):
                if id(arg) not in self._unique_rets and \
                        id(arg) not in self._create_list and \
                        id(arg) not in self._unique_vars:
                    self._unique_vars.append(id(arg))
        for item in kwargs.values():
            if self.__ismutalbe(item):
                if id(item) not in self._unique_rets and \
                        id(item) not in self._create_list and \
                        id(item) not in self._unique_vars:
                    self._unique_vars.append(id(item))

    @staticmethod
    def __ismutalbe(arg):
        ret = True
        if isinstance(arg, (int, float, complex, str, tuple, frozenset, bytes)):
            ret = False
        return ret


    def _argout(self, result):
        if result is None:
            ret = 0
        else:
            if isinstance(result, tuple):
                for res in result:
                    if self.__ismutalbe(res):
                        if id(res) not in self._unique_rets and \
                                id(res) not in self._create_list and \
                                id(res) not in self._unique_vars:
                            self._unique_rets.append(id(res))
                ret = len(result)
            else:
                if self.__ismutalbe(result):
                    if id(result) not in self._unique_rets and \
                            id(result) not in self._create_list and \
                            id(result) not in self._unique_vars:
                        self._unique_rets.append(id(result))
                ret = 1
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

    @staticmethod
    def _makeScriptEntry(class_in, call_type, *args, index=None, returns=None, **kwargs):
        call_function = None
        call_obj = None
        create_index = index
        call_variables = None
        call_prop = None
        returns = returns
        if call_type == 'create_obj':
            call_variables = [args, kwargs]
            create_index = create_index
        elif call_type == 'fn_call':
            call_obj = args[0]
            call_function = args[1]
            call_variables = [args[2:], kwargs]
        elif call_type == 'prop_set':
            call_obj = args[0]
            call_prop = args[1]
            if BaseHugger.__ismutalbe(args[2]):
                call_variables = id(args[2])
            else:
                call_variables = args[2]
        elif call_type == 'prop_get':
            call_obj = args[0]
            call_prop = args[1]
        elif call_type == 'magic_method':
            call_function = args[0]
            call_variables = [args[1:], kwargs]
            create_index = create_index

        caller = dict(class_obj=class_in.__name__,
                      call_type=call_type,
                      call_obj=call_obj,
                      call_prop=call_prop,
                      create_index=create_index,
                      call_function=call_function,
                      call_variables=call_variables,
                      returns=returns)
        return caller

    def makeScript(self):
        def parseScriptEntry(entry):
            class_obj = entry['class_obj']
            call_type = entry['call_type']
            call_obj = entry['call_obj']
            call_prop = entry['call_prop']
            call_function = entry['call_function']
            call_variables = entry['call_variables']
            create_index = entry['create_index']
            returns = entry['returns']

            class_obj_name = class_obj.lower()

            if call_type == 'create_obj':
                # No need for name checking on creator.
                temp = f'{class_obj_name}_{create_index} = {class_obj}('
                for var in call_variables[0]:
                    if var in self._unique_vars:
                        index = self._unique_vars.index(var)
                        temp += f'{self.__var_ident}{index}, '
                    elif var in self._unique_rets:
                        index = self._unique_rets.index(var)
                        temp += f'{self.__ret_ident}{index}, '
                    else:
                        if isinstance(var, str):
                            var = '"' + var + '"'
                        temp += f'{var}, '
                if call_variables[0]:
                    temp = temp[:-2]
                temp_i = 0
                for key, item in call_variables[1].items():
                    if temp_i == 0 & len(call_variables[0]) > 0:
                        temp += ', '
                    if item in self._unique_vars:
                        index = self._unique_vars.index(item)
                        temp += f'{key}={self.__var_ident}{index}, '
                    elif item in self._unique_rets:
                        index = self._unique_rets.index(item)
                        temp += f'{key}={self.__ret_ident}{index}, '
                    else:
                        if isinstance(item, str):
                            item = '"' + item + '"'
                        temp += f'{key}={item}, '
                    temp_i += 1
                if call_variables[1]:
                    temp = temp[:-2]
                temp += ')\n'
                return temp

            if call_type == 'magic_method':
                temp = f'{class_obj_name}_{create_index} = {class_obj}.{call_function}('
                for var in call_variables[0]:
                    if var in self._unique_vars:
                        index = self._unique_vars.index(var)
                        temp += f'{self.__var_ident}{index}, '
                    elif var in self._unique_rets:
                        index = self._unique_rets.index(var)
                        temp += f'{self.__ret_ident}{index}, '
                    else:
                        if isinstance(var, str):
                            var = '"' + var + '"'
                        temp += f'{var}, '
                if call_variables[0]:
                    temp = temp[:-2]
                temp_i = 0
                for key, item in call_variables[1].items():
                    if temp_i == 0 & len(call_variables[0]) > 0:
                        temp += ', '
                    if item in self._unique_vars:
                        index = self._unique_vars.index(item)
                        temp += f'{key}={self.__var_ident}{index}, '
                    elif item in self._unique_rets:
                        index = self._unique_rets.index(item)
                        temp += f'{key}={self.__ret_ident}{index}, '
                    else:
                        if isinstance(item, str):
                            item = '"' + item + '"'
                        temp += f'{key}={item}, '
                    temp_i += 1
                if call_variables[1]:
                    temp = temp[:-2]
                temp += ')\n'
                return temp

            idx = self._create_list.index(id(call_obj))
            if call_type == 'fn_call':
                temp = ''
                for i in range(returns):
                    temp += f'{self.__ret_ident}{i}, '
                if returns > 0:
                    temp = temp[:-2]
                    temp += ' = '
                temp += f'{class_obj_name}_{idx}.{call_function}('
                for var in call_variables[0]:
                    if var in self._unique_vars:
                        index = self._unique_vars.index(var)
                        temp += f'{self.__var_ident}{index}, '
                    elif var in self._unique_rets:
                        index = self._unique_rets.index(var)
                        temp += f'{self.__ret_ident}{index}, '
                    else:
                        if isinstance(var, str):
                            var = '"' + var + '"'
                        temp += f'{var}, '
                if call_variables[0]:
                    temp = temp[:-2]
                temp_i = 0
                for key, item in call_variables[1].items():
                    if temp_i == 0 & len(call_variables[0]) > 0:
                        temp += ', '
                    if item in self._unique_vars:
                        index = self._unique_vars.index(item)
                        temp += f'{key}={self.__var_ident}{index}, '
                    elif item in self._unique_rets:
                        index = self._unique_rets.index(item)
                        temp += f'{key}={self.__ret_ident}{index}, '
                    else:
                        if isinstance(item, str):
                            item = '"' + item + '"'
                        temp += f'{key}={item}, '
                    temp_i += 1
                if call_variables[1]:
                    temp = temp[:-2]
                temp += ')\n'
                return temp
            elif call_type == 'prop_set':
                temp = f'{class_obj_name}_{idx}.{call_prop} = '
                if call_variables in self._create_list:
                    index = self._create_list.index(call_variables)
                    temp += f'{class_obj_name}_{index}'
                else:
                    if call_variables in self._unique_vars:
                        index = self._unique_vars.index(call_variables)
                        temp += f'{self.__var_ident}{index}'
                    elif call_variables in self._unique_rets:
                        index = self._unique_rets.index(call_variables)
                        temp += f'{self.__ret_ident}{index}'
                    else:
                        if isinstance(call_variables, str):
                            call_variables = '"' + call_variables + '"'
                        temp += f'{call_variables}'
                temp += '\n'
                return temp
            elif call_type == 'prop_get':
                temp = ''
                for i in range(returns):
                    temp += f'{self.__ret_ident}{i}, '
                if returns > 0:
                    temp = temp[:-2]
                    temp += ' = '
                temp += f'{class_obj_name}_{idx}.{call_prop}\n'
                return temp

        text = '# Auto generated script\n\n'
        for call in self._history:
            text += parseScriptEntry(call)
        return text



class ClassHugger(BaseHugger):

    def __init__(self, debug=False):
        super().__init__(debug=debug)
        self._auto_props = None

    def hug(self, klass):
        old_init = klass.__init__
        self._old_set_attr = klass.__setattr__
        self._old_get_attr = klass.__getattribute__

        def patch_init(obj, *args, **kwargs):
            if self.debug:
                print(f"{klass.__name__} is created with {args}, {kwargs}")
            self._history.append(self._makeScriptEntry(klass, 'create_obj', *args, index=self._count, **kwargs))
            old_init(obj, *args, **kwargs)
            self._create_list.append(id(obj))
            self._count += 1
            new_props = self._auto_props.symmetric_difference(set(klass.__dict__.keys()))
            if new_props:
                prop_dict = {}
                for prop in list(new_props):
                    prop_dict[prop] = klass.__dict__[prop]
                patch_methods_properties(prop_dict)

        def patch_methods_properties(this_dict):
            for key in this_dict.keys():
                if isinstance(this_dict[key], Callable):
                    setattr(klass, key, fun_wrap(this_dict[key]))
                elif isinstance(this_dict[key], property):
                    if this_dict[key].fget.__name__ != key:
                        setattr(klass, key,
                                property(fun_get_wrap(this_dict[key].fget, name=key),
                                         fun_set_wrap(this_dict[key].fset, name=key),
                                         this_dict[key].fdel))
                    else:
                        setattr(klass, key,
                                property(fun_get_wrap(this_dict[key].fget), fun_set_wrap(this_dict[key].fset),
                                         this_dict[key].fdel))
                elif isinstance(this_dict[key], (classmethod, staticmethod)):
                    setattr(klass, key, fun_wrap(this_dict[key], name=key))

        def patch_getter_setter(obj):
            obj.__getattribute__ = get_wrapper(self._old_get_attr)
            obj.__setattr__ = set_wrapper(self._old_set_attr)

        def fun_get_wrap(fun, name=None):
            if name is None:
                name = fun.__name__

            @wraps(fun)
            def inner(*args, **kwargs):
                self._argument_checker(*args, **kwargs)
                if self.debug:
                    print(f"I''m {args[0]} and getting {name}")
                res = fun(*args, **kwargs)
                ret = self._argout(res)
                self._history.append(self._makeScriptEntry(klass, 'prop_get', *[args[0], name, *args[1:]], returns=ret,
                                                           **kwargs))
                return res

            return inner

        def fun_set_wrap(fun, name=None):
            if name is None:
                name = fun.__name__

            def inner(*args, **kwargs):
                self._argument_checker(*args, **kwargs)
                self._history.append(self._makeScriptEntry(klass, 'prop_set', *[args[0], name, *args[1:]], **kwargs))
                if self.debug:
                    print(f"I''m {args[0]} and getting {name}")
                return fun(*args, **kwargs)

            return inner

        def fun_wrap(fun, name=None):
            if name is None:
                name = fun.__name__

            if self.debug:
                print(f"I''ve wrapped {klass.__name__}.{name}")

            @wraps(fun)
            def inner(*args, **kwargs):
                self._argument_checker(*args, **kwargs)
                caller = self._caller_name(skip=1)
                skip = False
                if klass.__name__ in caller:
                    if self.debug:
                        print(f"I've been called from {caller}")
                    skip = True

                if name != 'patch_init':
                    if self.debug:
                        print(f"I''m {args[0]}.{name} and have been called with {args[1:]}, {kwargs}")
                    if isinstance(fun, (classmethod, staticmethod)):
                        if isinstance(fun, classmethod):
                            res = getattr(fun, '__func__')(klass, *args, **kwargs)
                            if skip:
                                return res
                            self._count -= 1
                            ret = self._argout(res)
                            self._history[-1] = self._makeScriptEntry(klass, 'magic_method', *[name, *args[1:]],
                                                                      returns=ret, index=self._count, **kwargs)
                        else:
                            res = getattr(fun, '__func__')(*args[1:], **kwargs)
                            if skip:
                                return res
                            ret = self._argout(res)
                            self._history.append(self._makeScriptEntry(klass, 'magic_method', *[name, *args[1:]],
                                                                       returns=ret, index=self._count, **kwargs))
                    else:
                        res = fun(*args, **kwargs)
                        if skip:
                            return res
                        ret = self._argout(res)
                        self._history.append(self._makeScriptEntry(klass, 'fn_call', *[args[0], name, *args[1:]],
                                                                   returns=ret, **kwargs))
                    return res
                return fun(*args, **kwargs)
            return inner

        def get_wrapper(fun):
            def checker(this_fun, thisitem):
                return thisitem in this_fun.__dict__.keys()

            @wraps(fun)
            def inner(*args, **kwargs):
                if args[1] == '__dict__':
                    return fun(*args, **kwargs)
                if not checker(args[0], args[1]):
                    return fun(*args, **kwargs)
                if isinstance(args[0].__dict__[args[1]], Callable):
                    return fun(*args, **kwargs)
                if args[1][0] != '_':
                    if self.debug:
                        print(f"I''m getting {args[0]}.{args[1]}")
                    self._history.append(
                        self._makeScriptEntry(klass, 'prop_get', *[args[0], fun.__name__, *args[1:]], **kwargs))

                return fun(*args, **kwargs)

            return inner

        def set_wrapper(fun):
            def checker(this_fun, thisitem):
                return thisitem in this_fun.__dict__.keys()

            @wraps(fun)
            def inner(*args, **kwargs):
                if args[1] == '__dict__':
                    return fun(*args, **kwargs)
                if not checker(args[0], args[1]):
                    return fun(*args, **kwargs)
                if isinstance(args[0].__dict__[args[1]], Callable):
                    return fun(*args, **kwargs)
                if args[1][0] != '_':
                    if self.debug:
                        print(f"I''m setting {args[0]}.{args[1]} to {args[2]}")
                    self._history.append(
                        self._makeScriptEntry(klass, 'prop_set', *args, **kwargs))
                return fun(*args, **kwargs)

            return inner

        klass.__init__ = patch_init
        patch_methods_properties(klass.__dict__)
        self._auto_props = {'__getattribute__', '__setattr__', *list(klass.__dict__.keys())}
        patch_getter_setter(klass)
        return klass


class FunctionHugger(BaseHugger):
    pass
