#!/usr/bin/env python
# -*- coding: utf-8 -*-

from json import loads
from random import random, randrange
import base64
import hashlib
from urllib import urlencode
import urllib2
import time
import re
from urlparse import urlparse
from common import get_html, match1


#@DEPRECATED
def get_timestamp():
    tn = random()
    url = 'http://api.letv.com/time?tn={}'.format(tn)
    result = get_content(url)
    return loads(result)['stime']


#@DEPRECATED
def get_key(t):
    for s in xrange(8):
        e = 1 & t
        t >>= 1
        e <<= 31
        t += e
    return t ^ 185025305


class LeTV():
    # --- decrypt m3u8 data --------- ##
    def m3u8decode(self, data):
        version = data[0:5]
        if version.lower() == b'vc_01':
            # get real m3u8
            loc2 = bytearray(data[5:])
            length = len(loc2)
            loc4 = [0] * (2 * length)
            for i in xrange(length):
                loc4[2 * i] = loc2[i] >> 4
                loc4[2 * i + 1] = loc2[i] & 15
            loc6 = loc4[len(loc4) - 11:] + loc4[:len(loc4) - 11]
            loc7 = [0] * length
            for i in xrange(length):
                loc7[i] = (loc6[2 * i] << 4) + loc6[2 * i + 1]
            return ''.join([chr(i) for i in loc7])
        else:
            # directly return
            return data

    def calcTimeKey(self, t):
        ror = lambda val, r_bits, : ((val & (2**32-1)) >> r_bits % 32) | (val << (32 - (r_bits % 32)) & (2**32-1))
        magic = 185025305
        return ror(t, magic % 17) ^ magic

    def video_from_vid(self, vid, **kwargs):
        vparamap = {0: '1300', 1: '720p', 2: '1080p'}

        url = 'http://player-pc.le.com/mms/out/video/playJson'
        req = {
            'id': vid,
            'platid': 1,
            'splatid': 105,
            'format': 1,
            'tkey': self.calcTimeKey(int(time.time())),
            'domain': 'www.le.com',
            'region': 'cn',
            'source': 1000,
            'accessyx': 1
        }
        r = get_html(url + '?' + urlencode(req))
        info = loads(r)
        playurl = info['msgs']['playurl']

        stream_level = kwargs.get('level', 0)
        support_stream_id = playurl["dispatch"].keys()
        stype = len(support_stream_id)
        stream_level = min(stream_level, stype-1)
        stream_id = support_stream_id[stream_level]

        # pick a random domain 
        index = randrange(len(playurl['domain']))

        url = playurl["domain"][index] + playurl["dispatch"][stream_id][0]
        uuid = hashlib.sha1(url.encode('utf8')).hexdigest() + '_0'
        url = url.replace('tss=0', 'tss=ios')
        url += '&m3v=1&termid=1&format=1&hwtype=un&ostype=MacOS10.12.4&p1=1&p2=10&p3=-&expect=3&tn={}&vid={}&uuid={}&sign=letv'.format(random(), vid, uuid)

        r2 = get_html(url.encode('utf-8'))
        info2 = loads(r2)

        # hold on ! more things to do
        # to decode m3u8 (encoded)
        suffix = '&r=%d&appid=500' % (int(time.time() * 1000))

        m3u8 = get_html(info2['location'] + suffix, decoded=False)
        if m3u8 is None:
            return None

        m3u8_list = self.m3u8decode(m3u8)
        m3u8_file = kwargs.get('m3u8')
        with open(m3u8_file, "wb") as m3u8File:
            m3u8File.write(m3u8_list)
        m3u8File.close()
        urls = re.findall(r'^[^#][^\r]*', m3u8_list, re.MULTILINE)
        return urls

    def letvcloud_download_by_vu(self, vu, uu):
        #ran = float('0.' + str(random.randint(0, 9999999999999999))) # For ver 2.1
        #str2Hash = 'cfflashformatjsonran{ran}uu{uu}ver2.2vu{vu}bie^#@(%27eib58'.format(vu = vu, uu = uu, ran = ran)  #Magic!/ In ver 2.1
        argumet_dict = {'cf': 'flash', 'format': 'json', 'ran': str(int(time.time())), 'uu': str(uu), 'ver': '2.2', 'vu': str(vu), }
        sign_key = '2f9d6924b33a165a6d8b5d3d42f4f987'  #ALL YOUR BASE ARE BELONG TO US
        str2Hash = ''.join([i + argumet_dict[i] for i in sorted(argumet_dict)]) + sign_key
        sign = hashlib.md5(str2Hash.encode('utf-8')).hexdigest()
        request_info = urllib2.Request('http://api.letvcloud.com/gpc.php?' + '&'.join([i + '=' + argumet_dict[i] for i in argumet_dict]) + '&sign={sign}'.format(sign=sign))
        response = urllib2.urlopen(request_info)
        data = response.read()
        info = loads(data.decode('utf-8'))
        type_available = []
        for video_type in info['data']['video_info']['media']:
            type_available.append({'video_url': info['data']['video_info']['media'][video_type]['play_url']['main_url'], 'video_quality': int(info['data']['video_info']['media'][video_type]['play_url']['vtype'])})
        urls = [base64.b64decode(sorted(type_available, key=lambda x:x['video_quality'])[-1]['video_url']).decode("utf-8")]

    def letvcloud_download(self, url):
        qs = urlparse(url).query
        vu = match1(qs, r'vu=([\w]+)')
        uu = match1(qs, r'uu=([\w]+)')
        title = "LETV-" + vu
        self.letvcloud_download_by_vu(vu, uu)

    def video_from_url(self, url, **kwargs):
        if re.match(r'http://yuntv.letv.com/', url):
            self.letvcloud_download(url)
        else:
            html = get_html(url)
            vid = match1(url, r'http://www.letv.com/ptv/vplay/(\d+).html') or \
                    match1(url, r'http://www.le.com/ptv/vplay/(\d+).html') or \
                    match1(html, r'vid="(\d+)"')
        # title = match1(html,r'name="irTitle" content="(.*?)"')

        return self.video_from_vid(vid, **kwargs)


site = LeTV()
video_from_url = site.video_from_url
video_from_vid = site.video_from_vid
