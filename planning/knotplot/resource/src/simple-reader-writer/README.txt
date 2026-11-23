For the simplest reading and writing of KnotPlot 1.0 file format, look in the 
driver files kpfread2.cpp, kpfwrite.cpp and kpfwritef.cpp.  If all you need to
do is read and write single component, closed knots, than this should be 
all you need.  Just copy the kpf_io.cpp and kpf_io.h files into your project.

Note that in the code, the terms "chunk" and "section" are both used.  
Any function with "chunk" in the function name does the same thing
as the function with "section" replacing the string "chunk".

For more information on KnotPlot 1.0 file format, see http://knotplot.com/manual/FileFormats.html

--- rob scharein, 6 february 2011

