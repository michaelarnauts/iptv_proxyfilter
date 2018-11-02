import os
import re

import requests
from flask import Flask, make_response, redirect, url_for
from werkzeug.contrib.cache import SimpleCache
from parse_channels import parse_channels

app = Flask(__name__)
app.debug = os.getenv('DEBUG', True)
cache = SimpleCache()


@app.route('/')
def index():
    return redirect(url_for('filtered_m3u'))


@app.route('/filtered.m3u')
def filtered_m3u():
    url = os.getenv('IPTV_PROXYFILTER_URL', None)
    if url is None:
        return 'Error: Please set IPTV_PROXYFILTER_URL env variable.'

    raw_data = cache.get('raw_data')
    if raw_data is None:
        raw_data = requests.get(url).text
        cache.set('raw_data', raw_data, timeout=5*60)

    channels = parse_channels(raw_data)

    # id filter
    id_filter = os.getenv('IPTV_PROXYFILTER_ID', None)
    if id_filter is not None:
        app.logger.info('Using id filter: %s', id_filter)
        regex = re.compile(id_filter)
        channels = [x for x in channels if regex.match(x.tvg_id)]

    # name filter
    name_filter = os.getenv('IPTV_PROXYFILTER_NAME', None)
    if name_filter is not None:
        app.logger.info('Using name filter: %s', name_filter)
        regex = re.compile(name_filter)
        channels = [x for x in channels if regex.match(x.tvg_name)]

    # group filter
    group_filter = os.getenv('IPTV_PROXYFILTER_GROUP', None)
    if group_filter is not None:
        app.logger.info('Using group filter: %s', group_filter)
        regex = re.compile(group_filter)
        channels = [x for x in channels if regex.match(x.group_title)]

    # +1 filter
    plus1_disable = os.getenv('IPTV_PROXYFILTER_PLUS1_DISABLE', False)
    if plus1_disable:
        channels = [x for x in channels if '+1' not in x.tvg_name.replace(' ', '')]

    # id notnull filter
    id_notnull_filter = os.getenv('IPTV_PROXYFILTER_ID_NOTNULL', False)
    if id_notnull_filter:
        channels = [x for x in channels if len(x.tvg_id) > 0]

    # uniq id filter
    id_uniq_filter = os.getenv('IPTV_PROXYFILTER_ID_UNIQ', False)
    if id_notnull_filter and id_uniq_filter:
        uniq_channels = dict()
        for channel in channels:
            if channel.tvg_id not in uniq_channels:
                uniq_channels[channel.tvg_id] = channel
            elif channel > uniq_channels[channel.tvg_id]:
                uniq_channels[channel.tvg_id] = channel
        channels = uniq_channels.values()

    response_content = '#EXTM3U\r\n'
    for channel in channels:
        response_content += str(channel)

    response = make_response(response_content)
    response.headers.set('Content-Type', 'audio/x-mpegurl')
    response.headers.set('Content-Disposition', 'attachment', filename='filtered.m3u')
    return response


if __name__ == '__main__':
    app.run()
