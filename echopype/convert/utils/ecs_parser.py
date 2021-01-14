import pandas as pd
import json
from collections import defaultdict
import os


class CalibrationParser():
    def __init__(self, input_file=None):
        if files is not None:
            self.input_files = input_file
        self.output_data = {}
        self._output_path = None

    @property
    def input_files(self):
        return self._input_files

    @input_files.setter
    def input_files(self, file):
        if not os.path.isfile(f):
            raise ValueError(f"Input file {f} does not exist")
        self._input_files = file

    def _parse(self, fid):
        pass

    def parse_files(self):
        self._output_path = []
