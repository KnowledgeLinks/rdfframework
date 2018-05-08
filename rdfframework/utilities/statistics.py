"""
Dictionary statics calculator
"""
import json
import pdb

_PATH_SEP = "|"

class DictionaryCounter(object):
    """
    Class will create a statics summary of all dictionaries in a passed.
    Pass in dictionary objects with the __call__ method

    Args:
        method["simple"]: does a simple count on wether the item exists in the
                passed in dictionary. "complex" will return aggreated counts
                of the items for the dictionary, i.e.
                Example for {'x': [1,2,3]}
                    simple: {'x': 1}
                    complex: {'x': 3}
        sub_total: the sting path to use for aggregateing subtotals
                Example for {'x': {'y': 'hello'} and {'x': {'y': 'bye'} the
                    path 'x|y' would create subtotal value for 'hello' and
                    'bye'
        list_blank: records dictionarys that are missing a value for the path
                assigned in this attribute. use the same path format as
                'sub_total'

    Attributes:
        counts: dictionary of summary counts
        sub_counts: dictionary of the subtotals
        blank: list of dictinaries with missing properties as specified with
                'list_blank'

    """

    def __init__(self, method="simple", sub_total=None, list_blank={}):
        self.counts = {}
        self.sub_counts = {}
        self.method = method
        self.sub_total = sub_total
        self.list_blank = list_blank
        self.blank = []

    def __call__(self, dict_obj):
        kwargs = {'current': {}}
        counts = self._count_objs(dict_obj, **{'current': {}})
        if self.method == "simple":
            self.update_counts(counts['current'])
        if self.sub_total:
            self.update_subtotals(counts['current'], counts['sub_val'])
        self._record_blank(counts['current'], dict_obj)

    def _record_blank(self, current, dict_obj):
        """
        records the dictionay in the the 'blank' attribute based on the
        'list_blank' path

        args:
        -----
            current: the current dictionay counts
            dict_obj: the original dictionary object
        """
        if not self.list_blank:
            return
        if self.list_blank not in current:
            self.blank.append(dict_obj)

    def _count_objs(self, obj, path=None, **kwargs):
        """
        cycles through the object and adds in count values

        Args:
        -----
            obj: the object to parse
            path: the current path

        kwargs:
        -------
            current: a dictionary of counts for current call
            sub_val: the value to use for subtotal aggregation

        """
        sub_val = None
        # pdb.set_trace()
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (list, dict)):
                    kwargs = self._count_objs(value,
                                              self.make_path(key, path),
                                              **kwargs)
                else:
                    if self.make_path(key, path) == self.sub_total:
                        # pdb.set_trace()
                        sub_val = value
                    kwargs['current'] = self._increment_prop(key,
                                                             path,
                                                             **kwargs)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (list, dict)):
                    kwargs = self._count_objs(item, path, **kwargs)
                else:
                    if path == self.sub_total:
                        pdb.set_trace()
                        sub_val = item
                    kwargs['current'] = self._increment_prop(path, **kwargs)
        else:
            kwargs['current'] = self._increment_prop(path, **kwargs)
            if path == self.sub_total:
                pdb.set_trace()
                sub_val = item
        if kwargs.get('sub_val') is None:
            kwargs['sub_val'] = sub_val
        return kwargs




    def _increment_prop(self, prop, path=None, **kwargs):
        """
        increments the property path count

        args:
        -----
            prop: the key for the prop
            path: the path to the prop

        kwargs:
        -------
            current: dictionary count for the current dictionay
        """
        new_path = self.make_path(prop, path)
        if self.method == 'simple':
            counter = kwargs['current']
        else:
            counter = self.counts
        try:
            counter[new_path] += 1
        except KeyError:
            counter[new_path] = 1
        return counter

    def update_counts(self, current):
        """
        updates counts for the class instance based on the current dictionary
        counts

        args:
        -----
            current: current dictionary counts
        """
        for item in current:
            try:
                self.counts[item] += 1
            except KeyError:
                self.counts[item] = 1

    def update_subtotals(self, current, sub_key):
        """
        updates sub_total counts for the class instance based on the
            current dictionary counts

        args:
        -----
            current: current dictionary counts
            sub_key: the key/value to use for the subtotals
        """

        if not self.sub_counts.get(sub_key):
            self.sub_counts[sub_key] = {}
        for item in current:
            try:
                self.sub_counts[sub_key][item] += 1
            except KeyError:
                self.sub_counts[sub_key][item] = 1

    def print(self):
        """
        prints to terminal the summray statistics
        """
        print("TOTALS -------------------------------------------")
        print(json.dumps(self.counts, indent=4, sort_keys=True))
        if self.sub_total:
            print("\nSUB TOTALS --- based on '%s' ---------" % self.sub_total)
            print(json.dumps(self.sub_counts, indent=4, sort_keys=True))
        if self.list_blank:
            print("\nMISSING nodes for '%s':" % self.list_blank,
                  len(self.blank))



    @staticmethod
    def make_path(prop, path):
        """
        makes the path string

        agrs:
        -----
            prop: the key for the current object
            path: the previous path to the prop
        """
        if path:
            return _PATH_SEP.join([path, prop])
        return prop

    @staticmethod
    def parse_path(path):
        """
        splits the path back to its parts

        args:
        -----
            path: the string path to parse
        """
        return path.split(_PATH_SEP)
