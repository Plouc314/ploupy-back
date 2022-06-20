class CachedDict(dict):
    '''
    Not finished...
    '''

    def __init__(self, size: int, *args, **kwargs):
        super(*args, **kwargs)
        self._size = size
        self._keys = []

    def __getitem__(self, key):
        if key in self._keys:
            self._keys.remove(key)
            self._keys.append(key)
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        if key in self._keys:
            self._keys.remove(key)
            self._keys.append(key)
            super().__setitem__(key, value)
            return    
        
        if len(self._keys) == self._size:
            self.pop(self._keys.pop(0))
        self._keys.append(key)
        
        super().__setitem__(key, value)