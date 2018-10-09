import os, pdb

from colorama import init as colorama_init, Fore, Style, Back

__colors_on__ = True
# Initialize colorama for windows platforms
if os.sys.platform.lower().startswith("win"):
    colorama_init()

class __ColorBase__():
    """
    Base class for __styles__, __backgrounds__ and colors

    args:
        value: the escaped string for a colored effect
        added: additional espaced color strings
    """
    value = ''
    def __init__(self, value='', added=''):
        self.value = added + value
    def __str__(self):
        return self.value
    def __call__(self, string=None):
        # pdb.set_trace()
        global __colors_on__
        if not __colors_on__:
            return string
        if string and self.value:
            return "{}{}{}".format(self.value, string, '\x1b[0m')
        # if self.value:
        #     return self.value
        elif self.value:
            return '\x1b[39m'
        return string



class __background__(__ColorBase__):
    """ returns a string formatted with the instance of the defined
    background """
    def __getattr__(self, attr):
        return __style__(getattr(__styles__, attr).value, self.value)
    def __setattr__(self, attr, value):
        if attr == 'value':
            self.__dict__[attr] = value
        else:
            setattr(__styles__, attr, value)

class __style__(__ColorBase__):
    """ returns a string formatted with the instance of the defined style """
    def __getattr__(self, attr):
        return None
    def __setattr__(self, attr, value):
        if attr == 'value':
            self.__dict__[attr] = value
        else:
            setattr(self.__class__, attr, value)

class __color__(__ColorBase__):
    """ returns a string formatted for the instance of the defined color """

    def __getattr__(self, attr):
        return __background__(getattr(__backgrounds__, attr).value, self.value)

    def __setattr__(self, attr, value):
        if attr == 'value':
            self.__dict__[attr] = value
        else:
            setattr(__backgrounds__, attr, value)


class __ColorsBaseMeta__(type):
    """ base meta for color calls """
    def __call__(cls, *args, **kwargs):
        return getattr(cls, args[0])

class __StylesMeta__(__ColorsBaseMeta__):
    """ addes styles to the __styles__ clasee """
    def __new__(mcs, name, bases, clsdict, **kwargs):
        # add the __styles__ from colorama
        new_dict = {key.lower(): __style__(value)
                    for key, value in Style.__dict__.items()}
        # add single letter abbreviation
        new_dict.update({key.lower()[0]: __style__(value)
                         for key, value in Style.__dict__.items()})
        # add __styles__ from the class definition
        new_dict.update({key: __style__(value)
                         for key, value in clsdict.items()
                         if not key.startswith("_")})
        # add single letter abbreviation
        new_dict.update({key[0]: __style__(value)
                         for key, value in clsdict.items()
                         if not key.startswith("_")})

        clsdict.update(new_dict)
        return super().__new__(mcs, name, bases, clsdict)
    def __getattr__(cls, attr):
        return cls.__dict__.get(attr.lower(), __background__())
    def __setattr__(cls, attr, value):
        if value in dir(cls):
            super().__setattr__(attr, getattr(cls, value))
        else:
            super().__setattr__(attr, __style__(value))

class __BackgroundsMeta__(__ColorsBaseMeta__):
    """ adds backgrounds to the __backgrounds__ class """
    def __new__(mcs, name, bases, clsdict, **kwargs):
        # pdb.set_trace()
        new_dict = {key.lower(): __background__(value)
                    for key, value in Back.__dict__.items()}
        new_dict.update({key: __background__(value)
                         for key, value in clsdict.items()
                         if not key.startswith("_")})
        clsdict.update(new_dict)
        return super().__new__(mcs, name, bases, clsdict)
    def __getattr__(cls, attr):
        return cls.__dict__.get(attr.lower(), __background__())

    def __setattr__(cls, attr, value):
        if value in dir(cls):
            super().__setattr__(attr, getattr(cls, value))
        else:
            super().__setattr__(attr, __background__(value))

class __ColorsMeta__(__ColorsBaseMeta__):
    """ adds colors to the colors class """
    def __new__(mcs, name, bases, clsdict, **kwargs):
        new_dict = {key.lower(): __color__(value)
                    for key, value in Fore.__dict__.items()}
        new_dict.update({key: __color__(value)
                         for key, value in clsdict.items()
                         if not key.startswith("_")})
        clsdict.update(new_dict)
        return super().__new__(mcs, name, bases, clsdict)
    def __getattr__(cls, attr):
        return cls.__dict__.get(attr.lower(), __color__())

    def __setattr__(cls, attr, value):
        if value in dir(cls):
            super().__setattr__(attr, getattr(cls, value))
        else:
            super().__setattr__(attr, __color__(value))
    @property
    def print_help(cls):
        """prints the documentation for the cls """
        def print_colors(color_cls):

            for attr, value in sorted(color_cls.__dict__.items()):
                if not attr.startswith("_"):
                    print(value(attr))

        print(cls.__doc__)
        print("                    ***** FORE COLORS ****\n")
        # pdb.set_trace()
        print_colors(cls)
        print("\n               **** BACKGROUND COLORS ****\n")
        print_colors(__backgrounds__)
        print("\n                     **** STYLES ****\n")
        print_colors(__styles__)

    @property
    def turn_on(cls):
        global __colors_on__
        __colors_on__ = True

    @property
    def turn_off(cls):
        global __colors_on__
        __colors_on__ = False


class colors(metaclass=__ColorsMeta__):
    """
    Main class for interacting with the module. Use class attribute
    notation with a call to return a formated color string

    colors.'fore color'.'background color'.'text style'("string to format")

    Examples:
        colors.red("string")
        colors.red.white("string")
        colors.red.white.bright("string")
    """

    # metaclass prevents this class from being instantiated

    # add addtional colors attributes below
    header = '\033[95m'
    blue = '\033[94m'
    green = '\033[92m'
    warning = '\033[93m'
    fail = '\033[91m'
    endc = '\033[0m'
    error = fail
    red = fail
    rd = red
    gr = green
    bl = blue
    wn = warning
    hd = header
    underline = '\033[4m'
    bold = '\033[1m'
    lcyan = Fore.LIGHTCYAN_EX


class __backgrounds__(metaclass=__BackgroundsMeta__):
    pass

class __styles__(metaclass=__StylesMeta__):
    underline = '\033[4m'
    bold = '\033[1m'
