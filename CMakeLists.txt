cmake_minimum_required(VERSION 3.12)
project(minidaqapp VERSION 1.0.0)

find_package(daq-cmake REQUIRED )

daq_setup_environment()

# Test configurations
file(COPY test/minidaq-app-fake-readout.json DESTINATION test)

daq_install()
