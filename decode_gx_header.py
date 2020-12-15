import sys
import ffcm_pp

if __name__ == '__main__':
    if len(sys.argv) != 2:
        '''
        Pass in the input *.gx file. Decodes the header portion that is in binary.
        For debugging a gx file you generate.
        '''
        print('Usage: decode_gx_header.py <gx_input_file>')
        sys.exit()

    with open('{}.ffcm'.format(sys.argv[1]), 'rb') as fd:
        g = ffcm_pp.GXProcessor()
        g.decode(fd.read())
        g.print_info()