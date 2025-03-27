#! /usr/bin/env python

import sys
import os.path as op
import logging as log

####################################
__author__      = 'Jordi Huguet'  ##
__dateCreated__ = '20221118'      ##
__version__     = '0.1.0'         ##
__versionDate__ = '20221118'      ##
####################################


def stats(container_id):
    import subprocess as sp
    import datetime as dt
    
    cmd = f'docker stats  --no-stream {container_id}'
    timepoint = dt.datetime.now()
    out = sp.check_output(cmd.split())
    
    data = out.decode('utf-8').splitlines()[1].split()
    
    data = [item for item in data if item != '/']
    data = [item.replace('%', '') for item in data]
    
    # Convert all byte-related measures to a common unit for comparability: Megabyte (MB)
    cleaned_data = [timepoint]
    for item in data:
        if item.endswith('GiB'):
            value = float(item.replace('GiB', '')) * 1073.74
        elif item.endswith('MiB'):
            value = float(item.replace('MiB', '')) * 1.04858
        elif item.endswith('KiB'):
            value = float(item.replace('KiB', '')) * 0.001024
        elif item.endswith('GB'):
            value = float(item.replace('GB', '')) * 1000
        elif item.endswith('MB'):
            value = float(item.replace('MB', ''))
        elif item.endswith('kB'):
            value = float(item.replace('kB', '')) * 0.001
        elif item.endswith('B'):
            value = float(item.replace('B', '')) * 1e-6
        else:
            value = item
        cleaned_data.append(value)
        
    return cleaned_data


def plot(dataframe, filename):
    import seaborn as sns
    import matplotlib.pyplot as plt
    import matplotlib.dates as dates

    sns.set("notebook", font_scale=1, rc={'lines.linewidth': 2})
    sns.set_theme()

    f, axes = plt.subplots(7, 1, figsize=(14, 14))
    color = sns.color_palette("hls", 7)

    for index, item in enumerate(['CPU_%', 'MEM_USAGE', 'NET_I', 'NET_O',
                                 'BLOCK_I', 'BLOCK_O', 'PIDS']):

        formatter = dates.ConciseDateFormatter(dates.AutoDateLocator())
        axes[index].xaxis.set_major_formatter(formatter)

        sns.lineplot(x=dataframe['timepoint'], y=item, data=dataframe,
                     ax=axes[index], color=color[index], dashes=False,
                     markers=True)

    axes[0].set_title('Docker container execution stats')
    #plt.show()
    f.savefig(filename)
    
    
def main(arguments):
    import docker
    from docker.errors import NotFound
    from time import sleep
    import csv
    import pandas as pd
    pd.set_option("display.max_colwidth", None)
    
    cid = arguments.container_id
    out = arguments.outdir
    
    # early dummy checks
    if not op.isdir(out):
        log.error('Not a valid output directory (%s)' % out)
        sys.exit(1)
    try:
        client = docker.from_env()
        c = client.containers.get(cid) 
    except NotFound as err:
        log.error('[{}] {}'.format(cid, err.explanation))
        sys.exit(1)
    
    sleep_time = 30
    cols = ['timepoint', 'CONTAINER_ID', 'NAME', 'CPU_%', 'MEM_USAGE', 'MEM_LIMIT', 
            'MEM_%', 'NET_I', 'NET_O', 'BLOCK_I', 'BLOCK_O', 'PIDS']
    fn = op.join(out, '{}.txt'.format(c.name))
    with open(fn, 'w') as f:
        csv_file = csv.writer(f)
        csv_file.writerow(cols)
    
    data = []
    while True:
        try:
            c = client.containers.get(cid)
        except NotFound as err:
            log.error('[{}] {}'.format(cid, err.explanation))
            break
        if c.status != 'running':
            break
        
        data.append(stats(c.id))
        
        with open(fn, 'a') as f:
            csv_file = csv.writer(f)
            csv_file.writerow(data)
            
        print(c.name, c.image.tags[0], c.status)
        sleep(sleep_time)
        
    df = pd.DataFrame(data, columns=cols)
    for header in cols[3:-1]:
        df[header] = df[header].astype(float)
    df['PIDS'] = df['PIDS'].astype(int)
    
    df.to_excel(fn.replace('.txt', '.xlsx'))
    if len(df) > 0:
        plot(df, fn.replace('.txt', '.png'))


def create_parser():
    import argparse
    from argparse import RawTextHelpFormatter

    arg_parser = argparse.ArgumentParser(
        description='Monitor Docker container execution stats',
        formatter_class=RawTextHelpFormatter)
    arg_parser.add_argument(
        '-c', '--container_id',
        help='Docker container ID', required=True)
    arg_parser.add_argument(
        '-o', '--outdir',
        help='Output directory', required=True)
    arg_parser.add_argument(
        '-v', '--verbose', dest='verbose',
        action='store_true', default=False,
        help='Display verbose information (optional)', required=False)
    arg_parser.add_argument(
        '-V', '--version', action='version',
        version='{} v{}'.format(op.basename(__file__), __version__))

    return arg_parser


if __name__ == "__main__":
    # script entry point
    parser = create_parser()
    args = parser.parse_args()

    if args.verbose:
        log.basicConfig(level=log.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)s:%(module)s:%(levelname)s:%(message)s')
    main(args)
    sys.exit(0)
