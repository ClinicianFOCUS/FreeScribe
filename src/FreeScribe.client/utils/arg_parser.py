import argparse
import utils.log_config

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file-debug", help="Enable the file logger", action="store_true")
    args = parser.parse_args()

    if args.file_debug:
        utils.log_config.add_file_handler(utils.log_config.logger, utils.log_config.formatter)
