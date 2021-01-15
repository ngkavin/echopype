import pandas as pd
import numpy as np
import json
from collections import defaultdict
import os


class CalibrationParser():
    def __init__(self, input_files=None):
        self._input_files = None
        if input_files is not None:
            self.input_files = input_files
        self.output_data = {}
        self._output_path = None

    # TODO Properties identical to EVR parser. factor out
    @property
    def input_files(self):
        return self._input_files

    @input_files.setter
    def input_files(self, files):
        if isinstance(files, str):
            files = [files]
        elif not isinstance(files, list):
            raise ValueError(f"Input files must be a string or a list. Got {type(files)} instead")
        for f in files:
            if not os.path.isfile(f):
                raise ValueError(f"Input file {f} does not exist")
        self._input_files = files

    @property
    def output_path(self):
        if len(self._output_path) == 1:
            return self._output_path[0]
        else:
            return self._output_path

    def _parse_settings(self, fid):
        """Reads lines from an open file.
        The function expects the lines to be in the format <field> = <value>.
        There may be hash marks (#) before the field and after the value.
        Collects these fields and values into a dictionary until a blank line is encountered
        """
        settings = {}
        while True:
            line = fid.readline().strip().split(' ')
            # Exit loop if no more fields in section
            if len(line) == 1:
                break
            # Check if field is commented out
            idx = 0 if line[0] != '#' else 1
            field = line[idx]
            val = line[idx + 2]
            # If no value is recorded for the field, save a nan
            val = np.nan if val == '#' else val
            settings[field] = val
        return settings

    def _parse_sourcecal(self, fid):
        """Parses the 'SOURCECAL SETTTINGS' section.
        Returns a dictionary with keys being the name of the sourcecal
        and values being a key value dictionary parsed by _parse_settings
        """
        sourcecal = {}
        # Parse all 'SourceCal' sections. Return when all have been parsed
        while True:
            cal_name = fid.readline().strip().split(' ')
            if cal_name[0] == 'SourceCal':
                sourcecal['_'.join(cal_name)] = self._parse_settings(fid)
            else:
                return sourcecal

    def parse_files(self):
        def advance_to_section(fid, section):
            cont = True
            # Read lines
            while cont:
                line = fid.readline()
                if section in line:
                    cont = False
            fid.readline()          # Bottom of heading box
            fid.readline()          # Blank line

        self._output_path = []
        for file in self.input_files:
            fid = open(file, encoding='utf-8-sig')
            fname = os.path.splitext(os.path.basename(file))[0]

            advance_to_section(fid, 'FILESET SETTINGS')
            fileset_settings = self._parse_settings(fid)
            advance_to_section(fid, 'SOURCECAL SETTINGS')
            sourcecal_settings = self._parse_sourcecal(fid)
            advance_to_section(fid, 'LOCALCAL SETTINGS')
            localcal_settings = self._parse_settings(fid)

            self.output_data[fname] = {
                'fileset_settings': fileset_settings,
                'sourcecal_settings': sourcecal_settings,
                'localcal_settings': localcal_settings,
            }

    def _validate_path(self, save_dir=None):
        # Checks a path to see if it is a folder that exists.
        # Does not create the folder if it doesn't
        # TODO: replace with a general validate path
        if save_dir is None:
            save_dir = os.path.dirname(self.input_files[0])
        else:
            if not os.path.isdir(save_dir):
                raise ValueError(f"{save_dir} is not a valid save directory")
        return save_dir

    def to_json(self, save_dir=None):
        """Convert an Echoview calbration .ecs file to a .json file

        Parameters
        ----------
        save_dir : str
            directory to save the JSON file to
        """

        # Parse ECS file if it hasn't already been done
        if not self.output_data:
            self.parse_files()

        # Check if the save directory is safe
        save_dir = self._validate_path()

        # Save the entire parsed EVR dictionary as a JSON file
        for file, regions in self.output_data.items():
            output_file_path = os.path.join(save_dir, file) + '.json'
            with open(output_file_path, 'w') as f:
                f.write(json.dumps(regions))
            self._output_path.append(output_file_path)
