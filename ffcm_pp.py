#!/Library/Frameworks/Python.framework/Versions/3.6/bin/python3
#
# NOTE: Change the above line to point to your systems python3 interpreter
# Requires Python3.5 minimum.
#
# MPS ElectroLab
# Description:  Generating xgcode from gcode for FlashForge Creator MAX
# License:  GPLv3

import sys
import os
import struct

'''
The FlashForge Creator Max does not use M126, 127 fan codes and does not read X3G files
directly. It puts a binary header on the gcode file and provides the GX extension. This is
despite that they advertise it will read x3g files and the open source standard stuff.

This post processor corrects those fan codes in the input gcode then converts the gcode into
a GX file suitable to be read by the MAX.

NOTE: You still need to use appropriate begin and end Gcode and proper settings in Slic3r.

Here is some begin, end and tool change code that I use:

Begin GCODE:

M140 S[first_layer_bed_temperature];   Heat bed up to first layer temperature
M104 S[first_layer_temperature_0] T0;   Set nozzle temperature of Right extruder to first layer temperature
M104 S[first_layer_temperature_0] T1;   Set nozzle temperature of Left extruder to first layer temperature
M107;   Fan off
G90;   Absolute Programming
G28;   Move to Home position 
M132 X Y Z A B;   Load current home position from EEPROM
G1 Z50 F600;   Move bed down to allow safe movement of nozzles lo left front
G1 X-110.5 Y-74 F6000;   Move nozzles to left front
M7;   Wait For Platform to reach target temperature
M6 T0;   Wait For Right nozzle to reach target temperature
M6 T1;   Wait For Left nozzle to reach target temperature
; M106 enable cooling fan
M907 X100 Y100 Z40 A100 B100;   Set digital potentiometer value. A and B typically 100 for tough filament like ABS and 80 for brittle like PLA. A is Right B is Left.
G1 Z0.6 F3300; Go to start height
G4 P2000;   Dwell time
G1 Z[first_layer_height] F7200.000;   Move to first layer height
M108 T[current_extruder];   Tool change to current extruder

End GCODE:

;End Gcode
M107;   Disable cooling fan
M104 S0 T0;  Set Nozzle temperature of Right nozzle to zero
M104 S0 T1;  Set Nozzle temperature of Left nozzle to zero
M140 S0;   Turn bed heating off
G162 Z;    Home positive for Z axis
G28 X0 Y0;   Return X and Y to home position
M132 X Y Z A B
G91;   Set to relative positioning
M18;   Disable stepper motors for all axes

Tools Change GCODE:

M108 T[next_extruder]

On your filament settings, use 100% fan after layer 1 for PLA.

'''

class GXProcessor(object):
    '''
    Generates xgcode 1.0 standard with the BMP at the front of the file for FlashForge Creator MAX.
    Using a default BMP (My logo), but this is usually the BMP of the part being printed.
    You can point to a generated BMP of the part or your own.
    '''
    BMP_SIZE = 13594
    BMP_START_OFFSET = 58
    GCODE_START_OFFSET = BMP_SIZE + BMP_START_OFFSET

    def __init__(self):
        self.version = b"xgcode 1.0\n\0"
        self.print_time = 0
        self.filament_usage = 0
        self.filament_usage_left = 0
        self.multi_extruder_type = 11
        self.layer_height = 0
        self.shells = 0
        self.print_speed = 0
        self.bed_temp = 0
        self.print_temp = 0
        self.print_temp_left = 0
        self.gcode = b""

    def _bmp(self):
        with open('{}/mps_logo.bmp'.format(os.path.dirname(os.path.realpath(__file__))), 'rb') as fd:
            return fd.read()


    def encode(self):
        '''
        You should set the variables on the GXProcessor object before calling encode. Otherwise the defaults are used.
        If you use default, it may show up on your printer as 0 print time, etc.
        If you build a plugin for your slicer, you can easily derive these and set them.
        You will see the main for this module is lazy, and I don't bother setting these for the printer to show. THey
        are not necessary for the function of the printer, at least not that I have found.
        '''
        buff = (self.version)
        buff += struct.pack("<4i",
                            0,
                            self.BMP_START_OFFSET,
                            self.GCODE_START_OFFSET,
                            self.GCODE_START_OFFSET
                            )
        buff += struct.pack("<iiih",
                            self.print_time,
                            self.filament_usage,
                            self.filament_usage_left,
                            self.multi_extruder_type,
                            )
        buff += struct.pack("<8h",
                            self.layer_height,
                            0,
                            self.shells,
                            self.print_speed,
                            self.bed_temp,
                            self.print_temp,
                            self.print_temp_left,
                            1,
                            )
        buff += self._bmp()
        buff += self.gcode
        return buff


    def decode(self, data):
        self._data = bytes(data)
        # First line must be "xgcode 1.0\n"
        rows = self._data.split(b'\n')
        if len(rows) < 2:
            print("gx.py: less than 2 rows")
            return
        if rows[0] != b"xgcode 1.0":
            print("invalid header")
            return
        # Header is first line + \n + second line
        header = rows[0] + b'\n' + rows[1] + b'\n'
        self._header = header
        # Version information
        offset = 0
        self.version = struct.unpack_from("<12s", header, offset)[0]
        offset = len(self.version)
        # Header constants
        cons = struct.unpack_from("<4l", header, offset)
        self.bitmap_start = cons[1]
        self.gcode_start = cons[2]
        # Metadata
        offset = 0x1C
        t, f1, f2, met = struct.unpack_from("<lllh", header, offset)
        self.print_time = t
        self.filament_usage, self.filament_usage_left = f1, f2
        self.multi_extruder_type = met
        offset = 0x2A
        lh, _, sh, spd, bt, et1, et2 = struct.unpack_from("<7h", header, offset)
        self.layer_height = lh
        self.shells = sh
        self.print_speed = spd
        self.bed_temperature = bt
        self.print_temperature = et1
        self.print_temperature_left = et2
        # Bitmap
        self.bmp = self._data[58:14512]
        if len(self.bmp) != 14454:
            raise "BMP length is invalid: %d" % len(self.bmp)
        self.gcode = self._data[self.gcode_start:]

    def print_info(self):
        print('BMP Start = {}, GCODE_START = {}, PRINT_TIME = {}, ME_TYPE = {}, PRINT_SPEED = {}, BED_TEMP = {}, PRINT_TEMP = {}, PRINT_TEMP_LEFT = {}'.format(
            self.bitmap_start,self.gcode_start, self.print_time, self.multi_extruder_type, self.print_speed, self.bed_temp, self.print_temp, self.print_temp_left
        ))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        '''
        Pass in the input *.gcode file. Output file will have '.gx' appended to end of file.
        Example: If input file named abc.gcode then output file will be named abc.gcode.gx
        '''
        print('Usage: ffcm_pp.py <gcode_input_file>')
        sys.exit()

    with open(sys.argv[1]) as fr:
        with open('{}.ffcm'.format(sys.argv[1]), 'w') as fw:
            gcode = []
            for line in fr:
                ''' Replacing the codes that FlashForge Creator MAX does not understand '''
                fw.write(line.replace('M126', 'M106').replace('M127', 'M107'))
            fw.close()
            fr.close()
            with open('{}.ffcm'.format(sys.argv[1]), 'rb') as fd:
                g = GXProcessor()
                g.gcode = fd.read()
                with open('{}.gx'.format(sys.argv[1]),'wb') as fw:
                    ''' Encoding the gcode into xgcode, with the BMP and xgcode header at the front of the gcode '''
                    fw.write(g.encode())
            os.remove('{}.ffcm'.format(sys.argv[1]))

