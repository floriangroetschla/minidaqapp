#!/usr/bin/env python3

import click
import minidaqapp.confgen

with open('minidaq-app-fake-readout-slim.json', 'w') as f:
    f.write(minidaqapp.confgen.generate())