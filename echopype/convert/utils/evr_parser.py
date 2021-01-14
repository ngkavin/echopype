import pandas
import os

class region_2D_parser():
    def __init__(self, files):
        if isinstance(files, str):
            files = [files]
        elif not isinstance(files, list):
            raise ValueError(f"Input files must be a string or a list. Got {type(files)} instead")

        self._input_files = files
        self.output_data = {}

    @property
    def input_files(self):
        return self._input_files

    @input_files.setter
    def input_files(self):
        self._input_files = self.input_files

    def _region_metadata_to_dict(self, line):
        return {
            'structure_version': line[0],                               # 13 currently
            'point_count': line[1],                                     # Number of points in the region
            'selected': line[3],                                        # Always 0
            'creation_type': line[4],                                   # Described here: https://support.echoview.com/WebHelp/Reference/File_formats/Export_file_formats/2D_Region_definition_file_format.htm#Data_formats
            'dummy': line[5],                                           # Always -1
            'bounding_rectangle_calculated': line[6],                   # 1 if next 4 fields valid. O otherwise
            # Date encoded as CCYYMMDD and times in HHmmSSssss
            # Where CC=Century, YY=Year, MM=Month, DD=Day, HH=Hour, mm=minute, SS=second, ssss=0.1 milliseconds
            'bounding_rectangle_left_x': f'D{line[7]}T{line[8]}',       # Time and date of bounding box left x
            'bounding_rectangle_top_y': line[10],                       # Top of bounding box
            'bounding_rectangle_right_x': f'D{line[11]}T{line[12]}',    # Time and date of bounding box right x
            'bounding_rectangle_bottom_y': line[14],                    # Bottom of bounding box
        }

    def _points_to_dict(self, line):
        points = {}
        for point_num, idx in enumerate(range(0, len(line), 3)):
            x = f'D{line[idx]}T{line[idx + 1]}'
            y = line[idx + 2]
            points[point_num] = (x, y)
        return points

    def parse(self):
        def read_line(open_file, split=False):
            """Remove the LF at the end of every line.
            Specify split = True to split the line on spaces"""
            if split:
                return open_file.readline().rstrip('\n').split(' ')
            else:
                return open_file.readline().rstrip('\n')

        # Loop over all specified files
        for file in self.input_files:
            f = open(file, encoding='utf-8-sig')
            # Read header containing metadata about the EVR file
            filetype, file_format_number, echoview_version = read_line(f, True)
            n_regions = int(read_line(f))
            fname = os.path.splitext(os.path.basename(file))[0]
            self.output_data[fname] = {
                'metadata': {'filetype': filetype,
                             'file_format_number': file_format_number,
                             'echoview_version': echoview_version},
                'regions': {}
            }
            # Loop over all regions in file
            for r in range(n_regions):
                f.readline()    # blank line separates each region
                region_metadata = read_line(f, True)
                self.output_data[fname]['regions'][region_metadata[2]] = {}
                # Alias to the region
                region = self.output_data[fname]['regions'][region_metadata[2]]
                # Add region metadata. 2nd index of region_metadata is the unique id of the region
                region['metadata'] = self._region_metadata_to_dict(region_metadata)
                # Add notes to region data
                n_note_lines = int(read_line(f))
                region['notes'] = [read_line(f) for l in range(n_note_lines)]
                # Add detection settings to region data
                n_detection_setting_lines = int(read_line(f))
                region['detection_settings'] = [read_line(f) for l in range(n_detection_setting_lines)]
                # Add classification to region data
                region['metadata']['region_classification'] = read_line(f)
                # Add point x and y
                points_line = read_line(f, True)
                points_line.pop()                                   # Remove trailing space
                # For type: 0=bad (No data), 1=analysis, 3=fishtracks, 4=bad (empty water)
                region['metadata']['type'] = points_line.pop()
                region['points'] = self._points_to_dict(points_line)
                region['metadata']['name'] = read_line(f)

    def to_csv(self):
        if not self.output_data:
           self.parse()

        df = 12

    def to_json(self, save_dir=None):
        import json

        # TODO: replace with a general validate path
        if save_dir is None:
            save_dir = os.path.dirname(self.input_files[0])
        else:
            if not os.path.isdir(save_dir):
                raise ValueError(f"{save_dir} is not a valid save directory")

        for file, regions in self.output_data.items():
            with open(os.path.join(save_dir, file) + '.json', 'w') as f:
                f.write(json.dumps(regions))


