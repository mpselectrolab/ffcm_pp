# ffcm_pp
 FlashForge Creator Max Post Processor for slicers. This post processor converts a *.gcode file into a *.gx 'xgcode v1' format file. The FF Max only reads this file format. At least that is all I could get it to read. The FlashPrint utility will generate them and that is what is loaded onto the printer. The code is easy to read and has comments. Simply hook it into your slicer as a post processor, passing in the input file name. An output file with the appended .gx is generated. Note the comments for some interesting caveats and ideas on using in a plugin, if your so inclined.

Clone this repo onto you machine with the slicer, then simply point to the ffcm_pp.py file to post process your gcode. You many need to change the source line at the top of the file to point to your python3 intepreter on the machine your running your slicer on. For slic3r, you will enter it in the post processor field, as seen in the screen shot below.

![Screenshot](slic3r_post_processor_example_image.png)
