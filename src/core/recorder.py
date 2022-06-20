import time
from typing import Any


class Recorder:
    def __init__(
        self,
        time_unit: float = 1.0,
        parent: Any | None = None,
    ):
        # time duration of a data chunk (in seconds)
        self.time_unit = time_unit

        # where the data is stored
        self._data: dict[int, dict] = {}

        # parent recorder
        self._parent = parent

        self._children: dict[str, Recorder] = {}

        # last tid
        self._max_tid = 0

        # all keys that have been stored
        self._keys = set()

        # start time of the recording
        self._st = time.time()

    def _get_tid(self) -> int:
        """
        Return the time id of now
        """
        t = time.time()
        return int((t - self._st) / self.time_unit)

    def dispatch(self, name: str) -> "Recorder":
        """
        Dispatch a recorder instance to record under `name` key
        for `self` instance
        """
        recorder = Recorder(time_unit=self.time_unit, parent=self)
        # sync start time with parent
        recorder._st = self._st
        
        self._children[name] = recorder
        return recorder

    def start(self):
        """
        Reset the start time of the recording
        """
        self._st = time.time()

    def record(self, **kwargs):
        """
        Record the given data
        """
        if len(kwargs) == 0:
            return

        tid = self._get_tid()

        # update max tid
        if tid > self._max_tid:
            self._max_tid = tid

        # assert create data chunk
        if not tid in self._data.keys():
            self._data[tid] = {}

        # update keys
        self._keys |= kwargs.keys()

        # udpate data
        self._data[tid] |= kwargs

    def compile(self) -> dict:
        """
        Compile the recorded data as a list of dict,
        one for each time chunk (of duration `time_unit`)
        """
        data = {k: [] for k in self._keys}

        # build first values
        chunk = {k: None for k in self._keys}
        for key in self._keys:
            tid = 0
            while tid <= self._max_tid:
                v = self._data.get(tid, {}).get(key, None)
                if v is not None:
                    chunk[key] = v
                    break
                tid += 1
            else:
                raise ValueError(f"No value found for '{key}'")

        # build sequential data
        for tid in range(self._max_tid + 1):
            chunk |= self._data.get(tid, {})
            for key in self._keys:
                data[key].append(chunk[key])

        # add children
        for key, recorder in self._children.items():
            data[key] = recorder.compile()

        return data
