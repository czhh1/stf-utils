import os
import argparse
import logging
import asyncio
import signal
from common.stfapi import api
from stf_record.protocol import STFRecordProtocol
from autobahn.asyncio.websocket import WebSocketClientFactory

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('stf-record')


def gracefully_exit(*args):
    log.info('Disconnecting...')
    exit(0)


def wsfactory(address, directory, resolution, no_clean_old_data):
    signal.signal(signal.SIGTERM, gracefully_exit)
    signal.signal(signal.SIGINT, gracefully_exit)
    log.info('Connecting to {0} ...'.format(address))

    directory = create_directory_if_not_exists(directory)
    if not no_clean_old_data:
        remove_all_data(directory)

    factory = WebSocketClientFactory("ws://{0}".format(address))
    factory.protocol = STFRecordProtocol
    factory.protocol.img_directory = directory
    factory.protocol.address = address
    factory.protocol.resolution = resolution

    loop = asyncio.get_event_loop()
    coro = loop.create_connection(
        factory, address.split(':')[0], address.split(':')[1]
    )
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()


def create_directory_if_not_exists(directory):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if not directory:
        directory = 'images'
        log.debug(
            'Directory not set. '
            'Default directory is {0}'.format(directory)
        )

    if not os.path.exists(directory):
        os.mkdir(directory)

    if directory[0] == ".":
        directory = "{0}/{1}".format(current_dir, directory[2:])
    elif directory[0] == "/":
        directory = "{0}".format(directory)
    else:
        directory = "{0}/{1}".format(current_dir, directory)

    return directory


def remove_all_data(directory):
    if directory and os.path.exists(directory):
        for file in os.listdir(directory):
            if file.endswith(".txt") or file.endswith(".jpg"):
                try:
                    os.remove("{0}/{1}".format(directory, file))
                    log.debug("File {0}/{1} was deleted".format(directory, file))
                except Exception as e:
                    log.debug("Error during deleting file {0}/{1}: {2}".format(directory, file, str(e)))


def get_ws_url(args):
    if not args["ws"] and not args["serial"]:
        log.info("Require -serial or -ws for starting...")
        exit(0)

    if not args['ws'] and args["serial"]:
        device_props = api.get_device(args["serial"])
        json = device_props.json()
        args["ws"] = json.get("device").get("display").get("url")
        log.debug("Got websocket url {0} by device serial {1} from stf API".format(args["ws"], args["serial"]))

    address = args['ws']
    if args['ws'].find('ws://') >= 0:
        address = address.split('ws://')[1]
    return address


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Utility for saving screenshots '
                    'from devices with openstf minicap'
    )
    parser.add_argument(
        '-serial', help='Device serial'
    )
    parser.add_argument(
        '-ws', help='WebSocket URL'
    )
    parser.add_argument(
        '-dir', help='Directory for images'
    )
    parser.add_argument(
        '-resolution', help='Resolution of images'
    )
    parser.add_argument(
        '-log-level', help='Log level'
    )
    parser.add_argument(
        '-no-clean-old-data', help='Clean old data from directory', action='store_true'
    )

    args = vars(parser.parse_args())

    if args['log_level']:
        log.info('Changed log level to {0}'.format(args['log_level'].upper()))
        log.setLevel(args['log_level'].upper())

    wsfactory(
        directory=args["dir"],
        resolution=args["resolution"],
        address=get_ws_url(args),
        no_clean_old_data=args["no_clean_old_data"]
    )