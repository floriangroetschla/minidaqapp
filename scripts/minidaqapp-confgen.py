#!/usr/bin/env python3


# Add -h as default help option
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

import click

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-n', '--number-of-data-producers', default=2)
@click.option('-s', '--data-rate-slowdown-factor', default=10)
@click.option('-r', '--run-number', default=333)
@click.option('-t', '--trigger-rate-hz', default=1.0)
@click.option('-d', '--data-file', type=click.Path(), default='./frames.bin')
@click.option('-o', '--output-path', type=click.Path(), default='.')
@click.argument('json_file', type=click.Path(), default='minidaq-app-fake-readout.json')
def cli(number_of_data_producers, data_rate_slowdown_factor, run_number, trigger_rate_hz, data_file, output_path, json_file):
    """
      JSON_FILE: Input raw data file.
      JSON_FILE: Output json configuration file.
    """
    import minidaqapp.confgen

    with open(json_file, 'w') as f:
        f.write(minidaqapp.confgen.generate(
                NUMBER_OF_DATA_PRODUCERS = number_of_data_producers,
                DATA_RATE_SLOWDOWN_FACTOR = data_rate_slowdown_factor,
                RUN_NUMBER = run_number, 
                TRIGGER_RATE_HZ = trigger_rate_hz,
                DATA_FILE = data_file,
                OUTPUT_PATH = output_path
            ))

    print(f"'{json_file}' generation completed.")


if __name__ == '__main__':
    cli()