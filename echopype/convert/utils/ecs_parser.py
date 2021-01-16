import pandas as pd
import numpy as np
from .ev_parser import EvParserBase
import os


class CalibrationParser(EvParserBase):
    def __init__(self, input_files=None):
        self.format = 'ECS'
        super().__init__(input_files)

    def _parse_settings(self, fid):
        """Reads lines from an open file.
        The function expects the lines to be in the format <field> = <value>.
        There may be hash marks (#) before the field and after the value.
        Collects these fields and values into a dictionary until a blank line is encountered
        """
        settings = {}
        while True:
            line = self.read_line(fid, split=True)
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
            cal_name = self.read_line(fid, split=True)
            if cal_name[0] == 'SourceCal':
                sourcecal['_'.join(cal_name)] = self._parse_settings(fid)
            else:
                return sourcecal

    def parse_files(self, input_files=None):
        def advance_to_section(fid, section):
            # Function for skipping lines that do not contain the variables to save
            cont = True
            # Read lines
            while cont:
                line = fid.readline()
                if section in line:
                    cont = False
            fid.readline()          # Bottom of heading box
            fid.readline()          # Blank line

        if input_files is not None:
            self.input_files = input_files

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

    def to_csv(self, save_dir=None):
        """Convert an Echoview calibration .ecs file to a .csv file

        Parameters
        ----------
        save_dir : str
            directory to save the CSV file to
        """
        def get_row_from_source(row_dict, source_dict, **kwargs):
            source_dict.update(kwargs)
            for k, v in source_dict.items():
                row_dict[k] = v
            return pd.Series(row_dict)

        # Parse ECS file if it hasn't already been done
        if not self.output_data:
            self.parse_files()

        # Check if the save directory is safe
        save_dir = self._validate_path()

        for file, settings in self.output_data.items():
            df = pd.DataFrame()
            id_keys = ['value_source', 'channel']
            fileset_keys = list(self.output_data[file]['fileset_settings'].keys())
            sourcecal_keys = list(list(self.output_data[file]['sourcecal_settings'].values())[0].keys())
            localset_keys = list(self.output_data[file]['localcal_settings'].keys())

            # Combine keys from the different sections and remove duplicates
            row_dict = dict.fromkeys(id_keys + fileset_keys + sourcecal_keys + localset_keys, np.nan)

            for cal, cal_settings in self.output_data[file]['sourcecal_settings'].items():
                row_fileset = get_row_from_source(
                    row_dict=row_dict.copy(),
                    source_dict=self.output_data[file]['fileset_settings'],
                    value_source='FILESET',
                    channel=cal,
                )
                row_sourcecal = get_row_from_source(
                    row_dict=row_dict.copy(),
                    source_dict=cal_settings,
                    value_source='SOURCECAL',
                    channel=cal,
                )
                row_localset = get_row_from_source(
                    row_dict=row_dict.copy(),
                    source_dict=self.output_data[file]['localcal_settings'],
                    value_source='LOCALSET',
                    channel=cal,
                )
                df = df.append([row_fileset, row_sourcecal, row_localset], ignore_index=True)

            # Export to csv
            output_file_path = os.path.join(save_dir, file) + '.csv'
            df.to_csv(output_file_path, index=False)
            self._output_path.append(output_file_path)