@echo off
openocd\bin\openocd.exe -s openocd/share/openocd/scripts -f interface/ftdi/m-link.cfg -f target/mik32.cfg
timeout /t 300
