# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib2
import urllib
import time
import random
import socket
import re
import sys
import os
import gzip
import StringIO
import cookielib
import base64
import simplejson

try:
    from ChineseKeyboard import Keyboard as Apps
except:
    from xbmc import Keyboard as Apps

########################################################################
# 乐视网(LeTv) by cmeng
########################################################################
# Version 1.5.9 2016-05-25 (cmeng)
# Implement all possible fixes to handle slow network response (starve network data)
# Add video server selection option
# Stop last video from repeating playback
# Improve user UI feedback on slow network data fetching actual status (background)

# See changelog.txt for previous history
########################################################################

# Plugin constants
__addon__     = xbmcaddon.Addon()
__addonid__   = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__addonicon__ = os.path.join(__addon__.getAddonInfo('path'), 'icon.png')
__profile__   = xbmc.translatePath(__addon__.getAddonInfo('profile'))
cookieFile    = __profile__ + 'cookies.letv'

# # UserAgent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
UserAgent = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)'
VIDEO_LIST = {'电影': ('1', '&o=9'),
              '电视剧': ('2', '&o=51'),
              '动漫': ('5', '&o=9'),
              '综艺': ('11', '&o=9&s=3'),
              '明星': ('3', '&a=-1')}
UGC_LIST = {'体育': ('4', '&o=1'),
            '娱乐': ('3', '&o=9'),
            '音乐': ('9', '&o=17'),
            '风尚': ('20','&o=1'),
            '纪录片': ('16', '&o=1'),
            '财经': ('22', '&o=1'),
            '汽车': ('14', '&o=1'),
            '旅游': ('23', '&o=1'),
            '亲子': ('34', '&o=9'),
            '热点': ('30', '&o=1')}

SERIES_LIST = ['电视剧', '动漫']
MOVIE_LIST = ['电影', '综艺']
VIDEO_RES = [["标清", 'sd'], ["高清", 'hd'], ["普通", ''], ["未注", "null"]]
COLOR_LIST = ['[COLOR FFFF0000]', '[COLOR FF00FF00]', '[COLOR FFFFFF00]', '[COLOR FF00FFFF]', '[COLOR FFFF00FF]']

FLVCD_PARSER_PHP = 'http://www.flvcd.com/parse.php'
FLVCD_DIY_URL = 'http://www.flvcd.com/diy/diy00'

CFRAGMAX = [10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500]


##################################################################################
# LeTv player class
##################################################################################
class LetvPlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)

    def play(self, name, thumb, v_urls=None):
        self.name = name
        self.thumb = thumb
        self.v_urls_size = 0
        self.curpos = 0
        self.is_active = True
        self.load_url_sync = False
        self.xbmc_player_stop = False
        self.title = name
        self.mCheck = True
        self.LOVS = 0

        self.v_urls = v_urls
        if (v_urls):    # single video file playback
            self.curpos = int(__addon__.getSetting('video_fragmentstart')) * 10
            self.v_urls_size = len(v_urls)
        else:    # ugc playlist playback
            self.curpos = int(name.split('.')[0]) - 1
            # Get the number of video items in PlayList for ugc playback
            self.playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            self.psize = self.playlist.size()

        self.videoplaycont = __addon__.getSetting('video_vplaycont')
        self.maxfp = CFRAGMAX[int(__addon__.getSetting('video_cfragmentmax'))]

        # Start filling first buffer video and start playback
        self.geturl()

    def geturl(self):
        if (self.v_urls and (self.curpos < self.v_urls_size)):
            # Use double buffering for smooth playback
            x = (self.curpos / self.maxfp) % 2
            self.videourl = __profile__ + 'vfile-' + str(x) + '.ts'
            fs = open(self.videourl, 'wb')

            endIndex = min((self.curpos + self.maxfp), self.v_urls_size)
            self.title = "%s - 第(%s~%s)/%s节" % (self.name, str(self.curpos+1), str(endIndex), str(self.v_urls_size))
            # print "### Preparing: " + self.title
            self.listitem = xbmcgui.ListItem(self.title, thumbnailImage=self.thumb)
            self.listitem.setInfo(type="Video", infoLabels={"Title":self.title})

            for i in range(self.curpos, endIndex):
                # Stop further video loading and terminate if user stop playback
                if (self.xbmc_player_stop or pDialog.iscanceled()):
                    self.videourl = None
                    i = self.v_urls_size
                    break

                if (not self.isPlayingVideo()):
                    pDialog.create('视频缓冲', '请稍候。下载视频文件 ....')
                    pDialog.update(((i - self.curpos) * 100 / self.maxfp), line2="### " + self.title)
                else:
                    pDialog.close()

                v_url = self.v_urls[i]
                bfile = getHttpData(v_url, True, True)
                # give another trial if playback is active and bfile is invalid
                if ((len(bfile) < 30) and self.isPlayingVideo()):
                    bfile = getHttpData(v_url, True, True)
                fs.write(bfile)

                # Start playback after fetching 4th video files, restart every 4 fetches if playback aborted unless stop by user
                if (not self.isPlayingVideo() and (i < self.v_urls_size) and (((i - self.curpos) % 4) == 3)):
                    pDialog.close()
                    # Must stop sync loading to avoid overwritten current video when onPlayerStarted
                    self.load_url_sync = False
                    xbmc.Player.play(self, self.videourl, self.listitem)
                    # give some time to xmbc to upate its player status before continue
                    xbmc.sleep(100)
                    # Only reset fragment start after successful playback
                    __addon__.setSetting('video_fragmentstart', '0')

            fs.close()
            # print "### Last video file download fragment: " + str(i)
            # set self.curpos to the next loading video index
            self.curpos = i + 1

            # Last of video segment loaded, enable play once only
            if (self.curpos == self.v_urls_size):
                self.LOVS = 1
            else:    # reset
                self.LOVS = 0

            # Start next video segment loading if sync loading not enable
            if (not self.load_url_sync and (self.curpos < self.v_urls_size)):
                # Reset to sync loading on subsequent video segment
                self.load_url_sync = True
                self.playrun()

        # ugc auto playback
        elif ((self.v_urls is None) and (self.curpos < self.psize)):
            if (self.mCheck and not self.isPlayingVideo()):
                pDialog.create('匹配视频', '请耐心等候! 尝试匹配视频文件 ...')

            # find next not play item in ugc playlist
            for idx in range(self.curpos, self.psize):
                p_item = self.playlist.__getitem__(idx)
                p_url = p_item.getfilename(idx)
                # p_url auto replaced with self.videourl by xbmc after played. To refresh, back and re-enter
                if "http:" in p_url:
                    p_list = p_item.getdescription(idx)
                    self.listitem = p_item  # pass all li items including the embedded thumb image
                    self.listitem.setInfo(type="Video", infoLabels={"Title":p_list})
                    self.curpos = idx
                    break

            x = self.curpos % 2
            self.videourl = __profile__ + 'vfile-' + str(x) + '.ts'
            fs = open(self.videourl, 'wb')

            v_urls = decrypt_url(p_url, self.mCheck)
            self.v_urls_size = len(v_urls)
            self.title = "UGC list @ %s (size = %s): %s" % (str(self.curpos), str(self.v_urls_size), p_list)
            # print "### Preparing: " + self.title

            for i, v_url in enumerate(v_urls):
                if (self.xbmc_player_stop or pDialog.iscanceled()):
                    self.videourl = None
                    i = self.v_urls_size
                    break

                if (not self.isPlayingVideo()):
                    pDialog.create('视频缓冲', '请稍候。下载视频文件 ....')
                    pDialog.update((i * 100 / self.v_urls_size), line2=self.title)
                else:
                    pDialog.close()

                bfile = getHttpData(v_url, True, True)
                fs.write(bfile)

                # Start playback after fetching 4th video files, restart every 4 fetches if playback aborted unless stop by user
                if (not self.isPlayingVideo() and (i < self.v_urls_size) and ((i % 4) == 3)):
                    pDialog.close()
                    # Must stop sync loading to avoid overwritten current video when onPlayerStarted
                    self.load_url_sync = False
                    xbmc.Player.play(self, self.videourl, self.listitem)
                    # give some time to xmbc to upate its player status before continue
                    xbmc.sleep(100)
            fs.close()
            # print "### Last video file download total fragment: %s ==> %s" % (str(i), self.title)
            # set self.curpos to the next loading ugc index
            self.curpos += 1

            # Last of video segment loaded, enable play once only
            if (self.curpos == self.psize):
                self.LOVS = 1
            else:    # reset
                self.LOVS = 0

            # Start next video segment loading if sync loading not enable
            if (not self.load_url_sync and (self.curpos < self.psize)):
                # Do not display dialog on subsequent UGC list loading
                self.mCheck = False

                # Reset to sync loading on subsequent ugc item
                self.load_url_sync = True
                self.playrun()

        # close dialog on all mode when fetching end
        pDialog.close()

    def playrun(self):
        if (self.videourl and not self.isPlayingVideo()):
            # print "### Player resume: %s \n### %s" % (self.title, self.videourl)
            pDialog.close()
            # Next video segment loading must wait until player started to avoid race condition
            self.load_url_sync = True
            xbmc.Player.play(self, self.videourl, self.listitem)
            xbmc.sleep(100)
        elif ((self.curpos < self.v_urls_size) or self.videoplaycont):
           # print "### Async fetch next video segment @ " + str(self.curpos)
           self.geturl()

    def onPlayBackStarted(self):
        # may display next title to playback due to async
        # print "### onPlayBackStarted Callback: " + self.title
        pDialog.close()
        if (self.load_url_sync):
            if ((self.curpos < self.v_urls_size) or self.videoplaycont):
                # print "### Sync fetch next video segment @ " + str(self.curpos)
                self.geturl()
        xbmc.Player.onPlayBackStarted(self)

    def onPlayBackSeek(self, time, seekOffset):
        # print "### Player seek forward: %s / %s" % (str(time), str(seekOffset))
        xbmc.Player.onPlayBackSeek(self, time, seekOffset)

    def onPlayBackSeekChapter(self, chapter):
        # no effect, valid on playlist playback by xmbc
        self.curpos += 1
        # print "### Player seek next chapter: " + str(self.curpos)
        xbmc.Player.onPlayBackSeek(self, chapter)

    def onPlayBackEnded(self):
        # Do not restart resume playback if video aborted due to starve network data
        if (self.videourl and self.load_url_sync):
        # if (self.videourl):
            # print "### onPlayBackEnded callback: Continue next video playback !!! " + str(self.LOVS)
            if (self.LOVS < 2):
                self.playrun()
            else:   # reset
                self.LOVS = 0
            # set flag to play last video segment once only
            if (self.LOVS == 1):
                self.LOVS += 1
        else:
            # print "### onPlayBackEnded callback: Ended-Deleted !!!"
            ## self.delTsFile(10)
            xbmc.Player.onPlayBackEnded(self)

    def onPlayBackStopped(self):
        # print "### onPlayBackStopped callback - Ending playback!!!"
        self.is_active = False
        self.xbmc_player_stop = True

    def delTsFile(self, end_index):
        for k in range(end_index):
            tsfile = __profile__ + 'vfile-' + str(k) + '.ts'
            if os.path.isfile(tsfile):
                try:
                    os.remove(tsfile)
                except:
                    pass


##################################################################################
# Routine to fetech url site data using Mozilla browser
# - deletc '\r|\n|\t' for easy re.compile
# - do not delete ' ' i.e. <space> as some url include spaces
# - unicode with 'replace' option to avoid exception on some url
# - translate to utf8
##################################################################################
def getHttpData(url, binary=False, mCheck=False):
    # setup proxy support
    proxy = __addon__.getSetting('http_proxy')
    type = 'http'
    if proxy != '':
        ptype = re.split(':', proxy)
        if len(ptype) < 3:
            # full path requires by Python 2.4
            proxy = type + '://' + proxy
        else:
            type = ptype[0]
        httpProxy = {type: proxy}
    else:
        httpProxy = {}
    proxy_support = urllib2.ProxyHandler(httpProxy)

    # setup cookie support
    cj = cookielib.MozillaCookieJar(cookieFile)
    if os.path.isfile(cookieFile):
        cj.load(ignore_discard=True, ignore_expires=True)
    else:
        if not os.path.isdir(os.path.dirname(cookieFile)):
            os.makedirs(os.path.dirname(cookieFile))

    # create opener for both proxy and cookie
    opener = urllib2.build_opener(proxy_support, urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(url)
    req.add_header('User-Agent', UserAgent)
    # req.add_header('cookie', 'PHPSESSID=ruebtvftj69ervhpt24n1b86i3')

    for k in range(3):  # give 3 trails to fetch url data
        if (mCheck and pDialog.iscanceled()):  # exit if cancelled by user
            return None

        try:
            response = opener.open(req)
        except urllib2.HTTPError, e:
            httpdata = e.read()
        except urllib2.URLError, e:
            httpdata = "IO Timeout Error"
        except socket.timeout, e:
            httpdata = "IO Timeout Error"
        else:
            httpdata = response.read()
            response.close()
            # Retry if exception: {"exception":{....
            if not "exception" in httpdata:
                cj.save(cookieFile, ignore_discard=True, ignore_expires=True)
                # for cookie in cj:
                #     print('%s --> %s'%(cookie.name,cookie.value))
                break

    if (not binary):
        httpdata = re.sub('\r|\n|\t', '', httpdata)
        match = re.compile('<meta.+?charset=["]*(.+?)"').findall(httpdata)
        if len(match):
            charset = match[0].lower()
            if (charset != 'utf-8') and (charset != 'utf8'):
                httpdata = unicode(httpdata, charset, 'replace').encode('utf-8')

    return httpdata


##################################################################################
# Routine to fetch and build video filter list
# Common routine for all categories
##################################################################################
def getListSEL(listpage):
    titlelist = []
    catlist = []
    itemList = []

    # extract categories selection
    match = re.compile('<li>(.+?)</li>').findall(listpage)
    for k, list in enumerate(match):
        title = re.compile('<h2.+?>(.+?)</h2>').findall(list)
        itemLists = re.compile('href="(.+?)"><b.*?>(.+?)</b>').findall(list)
        if (len(itemLists) > 1):
            itemList = [[x[0], x[1].strip()] for x in itemLists]

            item1 = itemList[0][0].split('_')
            item2 = itemList[1][0].split('_')
            ilist1 = len(item1)
            ilist2 = len(item2)

            # get the index of the current item variables
            for j in range(ilist2):
                if not (item2[j] in item1):
                    break

            icnt = len(itemList)
            # no filter for first item selection i.e. "全部"
            for i in range(icnt):
                if (i == 0) and (ilist1 < ilist2):
                    itemList[i][0] = ''
                else:
                    itemx = itemList[i][0].split('_')
                    itemList[i][0] = itemx[j]

            titlelist.append(title[0])
            catlist.append(itemList)

    # extract order selection if any
    title = re.compile('<span>(.+?)</span>').findall(listpage)
    if len(title):
        titlelist.append(title[0])
        match = re.compile('<lo>(.+?)</lo>').findall(listpage)
        itemLists = re.compile('data-order="(.+?)".+?>(.+?)</a>').findall(listpage)
        itemList = [[x[0], x[1].strip()] for x in itemLists]

    catlist.append(itemList)
    return titlelist, catlist


##################################################################################
# Routine to update video list as per user selected filtrs
##################################################################################
def updateListSEL(name, url, cat, filtrs, page, listpage):
    titlelist, catlist = getListSEL(listpage)
    fltr = filtrs[1:].replace('=', '').split('&')

    cat = ''
    selection = ''
    for icat, title in enumerate(titlelist):
        fltrList = [x[0] for x in catlist[icat]]
        list = [x[1] for x in catlist[icat]]
        sel = -1
        if (page):  # 0: auto extract cat only
            sel = dialog.select(title, list)
        if sel == -1:
            # return last choice selected if ESC by user
            if len(fltr) == len(titlelist):
                sel = fltrList.index(fltr[icat])
            else:  # default for first time entry
                sel = 0
        selx = catlist[icat][sel][0]
        ctype = catlist[icat][sel][1]
        if (ctype == '全部'):
            ctype += title[1:]
        # filtrs.append([catlist[icat][sel][0], catlist[icat][sel][1]])
        cat += COLOR_LIST[icat % 5] + ctype + '[/COLOR]|'
        selcat = re.compile('([a-z]+)').findall(selx)[0]
        catlen = len(selcat)
        if (selx != ''):  # no need to add blank filter
            selection += '&' + selcat + '=' + selx[catlen:]
    filtrs = selection
    cat = cat[:-1]

    if not page:
        return cat
    elif name in ('电影', '电视剧', '动漫', '综艺'):
        progListMovie(name, url, cat, filtrs, page, listpage)
    elif (name == '明星'):
        progListStar(name, url, cat, filtrs, page, listpage)
    else:
        progListUgc(name, url, cat, filtrs, page, listpage)
    return ''


##################################################################################
# Routine to generate 'pages' list for selection
# Based on 30 items per page and total items count p_itemCount
# Pages exclude current selected page
##################################################################################
def getPages(p_itemCount, page):
    c_pageNum = int(page)
    p_pageSize = 30
    p_pageTotal = ((p_itemCount + p_pageSize - 1) / p_pageSize) + 1
    p_pageMid = int(p_pageTotal / 2)

    if (c_pageNum <= p_pageMid):
        p_pageEnd = min(8, p_pageTotal)
        pages = range(1, p_pageEnd)
        p_pageFromEnd = max((p_pageTotal - 2), (p_pageEnd + 1))
    else:
        pages = range(2)
        p_pageFromEnd = max((p_pageTotal - 8), 2)

    for x in range(p_pageFromEnd, p_pageTotal):
        pages.append(x)

    if c_pageNum in pages:
        pages.remove(c_pageNum)

    return pages


##################################################################################
# Routine to fetch & build LeTV 网络电视 main menu
# - video list as per [VIDEO_LIST]
# - ugc list as per [UGC_LIST]
# - movies, series, star & ugc require different sub-menu access methods
##################################################################################
def mainMenu():
    li = xbmcgui.ListItem(' LeTV 乐视网 - 搜索: 【点此进入】')
    u = sys.argv[0] + "?mode=31"
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    link = getHttpData('http://list.letv.com/listn/c1_t-1_a-1_y-1_s1_lg-1_ph-1_md_o9_d1_p.html')
    match = re.compile('<div class="channel_list.+?">(.+?)</div>').findall(link)[0]
    ugclist = re.compile('href="(.+?)".*?>(.+?)</a>').findall(match)

    totalItems = len(ugclist)
    listpage = ""
    cat = "全部"
    p_url = 'http://list.letv.com'
    i = 0

    # fetch the url from ugclist for video channels, for those in VIDEO_LIST
    for x_url, name in ugclist:
        try:
            filtrs = VIDEO_LIST.get(name)[1]
        except:
            continue
        i = i + 1
        if name == '明星':
            mode = '4'
        else:
            mode = '1'
        url = p_url + x_url

        ilist = "%s. %s" % (i, name)
        li = xbmcgui.ListItem(ilist)
        u = sys.argv[0] + "?mode=" + mode + "&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&cat=" + urllib.quote_plus(cat) + "&filtrs=" + urllib.quote_plus(filtrs) + "&page=1" + "&listpage=" + listpage
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True, totalItems)

    # fetch the url from ugclist for ugc channels, for those in UGC_LIST
    for x_url, name in ugclist:
        try:
            filtrs = UGC_LIST.get(name)[1]
        except:
            continue
        i = i + 1
        url = p_url + x_url
        ilist = "%s. %s" % (i, name)
        li = xbmcgui.ListItem(ilist)
        u = sys.argv[0] + "?mode=8" + "&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&cat=" + urllib.quote_plus(cat) + "&filtrs=" + urllib.quote_plus(filtrs) + "&page=1" + "&listpage=" + listpage
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True, totalItems)

    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


##################################################################################
# Routine to fetch and build the video selection menu
# - selected page & filters (user selectable)
# - video items list
# - user selectable pages
# http://list.letv.com/apin/chandata.json?c=1&d=1&md=&o=9&p=3&s=1
##################################################################################
def progListMovie(name, url, cat, filtrs, page, listpage):
    fltrCategory = VIDEO_LIST[name][0]
    if page is None:
        page = '1'
    p_url = "http://list.letv.com/apin/chandata.json?c=%s&d=2&md=&p=%s%s"

    if listpage is None:
        link = getHttpData(url)
        # print link
        listpage = re.compile('class="label_list.+?>(.+?)</ul>').findall(link)[0]
        match = re.compile('<div class="sort_navy.+?">(.+?)</div>').findall(link)
        if len(match):
            listpage += match[0].replace('li', 'lo')
        cat = updateListSEL(name, url, cat, filtrs, 0, listpage)
    p_url = p_url % (fltrCategory, page, filtrs)

    # Fetch & build video titles list for user selection, highlight user selected filtrs
    cat = re.sub(' ', '', cat)
    li = xbmcgui.ListItem(name + '（第' + str(page) + '页）【' + cat + '】（按此选择)')
    u = sys.argv[0] + "?mode=9&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&cat=" + urllib.quote_plus(cat) + "&filtrs=" + urllib.quote_plus(filtrs) + "&page=1" + "&listpage=" + urllib.quote_plus(listpage)
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    link = getHttpData(p_url)
    if link is None:
        return

    # Movie, Video, Series, Variety & Music titles need different routines
    if (name in SERIES_LIST):
        isDir = True
        mode = '2'
    elif (name in MOVIE_LIST):
        isDir = False
        mode = '10'

    # fetch and build the video series episode list
    content = simplejson.loads(link)
    vlist = content['album_list']
    totalItems = len(vlist)
    for i in range(0, totalItems):
        p_name = vlist[i]['name'].encode('utf-8')
        # get series listing of the video
        if name in SERIES_LIST:
            aid = str(vlist[i]['aid'])
            if (name == '电视剧'):
                v_url = 'http://www.letv.com/tv/%s.html' % aid
            else:
                v_url = 'http://www.letv.com/comic/%s.html' % aid
        # get first video link for direct play back
        else:
            vid = str(vlist[i]['vids'].split(',')[0])
            v_url = 'http://www.letv.com/ptv/vplay/%s.html' % vid

        try:
            p_thumb = vlist[i]['images']['150*200']
        except KeyError:
            p_thumb = vlist[i]['images']['160*120']
        except:
            p_thumb = ''

        p_title = p_name
        p_list = str(i + 1) + '. ' + p_title + ' '

        try:  # Extract rating information
            p_rating = float(vlist[i]['rating'])
            if (p_rating is not None and p_rating > 0.01):
                p_rating = "%0.1f" % p_rating
                p_list += '[' + p_rating + ']'
        except:
            pass

        try:  # get language + area information
            p_lang = ''
            if name in MOVIE_LIST:
                p_lang = vlist[i]['lgName'] + '-'
            p_area = vlist[i]['areaName']
            p_list += '[' + (p_lang + p_area).encode('utf-8') + ']'
        except:
            pass

        p_sdx = vlist[i]['duration']
        if (p_sdx is not None) and (len(p_sdx) > 0) and (int(p_sdx) > 0):
            p_dx = int(p_sdx)
            p_duration = "[%02d:%02d]" % (int(p_dx / 60), (p_dx % 60))
            p_list += '[' + p_duration + ']'

        p_artists = vlist[i]['starring']
        if (p_artists is not None) and len(p_artists):
            p_artist = ""
            p_list += '['
            for key in p_artists:
                p_artist += p_artists[key].encode('utf-8') + ' '
            p_list += p_artist[:-1] + ']'
        else:
            p_subcategory = vlist[i]['subCategoryName']
            if p_subcategory is not None:
                p_list += '[' + p_subcategory.encode('utf-8') + ']'

        li = xbmcgui.ListItem(p_list, iconImage='', thumbnailImage=p_thumb)
        # li.setInfo(type = "Video", infoLabels = {"Title":p_list, "Artist":p_artist})
        u = sys.argv[0] + "?mode=" + mode + "&name=" + urllib.quote_plus(p_name) + "&url=" + urllib.quote_plus(v_url) + "&thumb=" + urllib.quote_plus(p_thumb)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, isDir, totalItems)

    p_itemCount = content['album_count']
    pages = getPages(p_itemCount, page)

    for page in pages:
        li = xbmcgui.ListItem("... 第" + str(page) + "页")
        u = sys.argv[0] + "?mode=1" + "&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&cat=" + urllib.quote_plus(cat) + "&filtrs=" + urllib.quote_plus(filtrs) + "&page=" + str(page) + "&listpage=" + urllib.quote_plus(listpage)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


##################################################################################
# Routine to fetch and build the video series selection menu
# - for 电视剧  & 动漫
# - selected page & filters (user selectable)
# - Video series list
# - user selectable pages
##################################################################################
def progListSeries(name, url, thumb):
    link = getHttpData(url)
    match = re.compile('<i class="i-t">(.+?)</i>').findall(link)
    episodes = ''
    if match:
        episodes = ' (' + ' '.join(match[0].split()) + ')'

    li = xbmcgui.ListItem('【' + name + '-' + episodes + ' | [选择: ' + name + ']】', iconImage='', thumbnailImage=thumb)
    u = sys.argv[0] + "?mode=2&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&thumb=" + urllib.quote_plus(thumb)
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    # fetch and build the video series list
    match = re.compile('<div.+?data-tabct="j-tab[1-9]+_child".+?statectn="n_list[1-9]+">(.+?)</div>').findall(link)
    # special handling for '动漫'
    if match is None:
        match = re.compile('<div.+?data-tabct="j-tab[1-9]+_child"(.+?)</div>').findall(link)
    else:
        matchp = re.compile('<dl class="w96">(.+?)</dl>').findall(match[0])
        if len(matchp):  # not the right one, so re-fetch
            match = re.compile('<div.+?data-tabct="j-tab[1-9]+_child"(.+?)</div>').findall(link)

    for j in range(0, len(match)):
        matchp = re.compile('<dl class="w120">(.+?)</dl>').findall(match[j])
        totalItems = len(matchp)
        for i in range(0, len(matchp)):
            match1 = re.compile('<img.+?src="(.+?)"').findall(matchp[i])
            p_thumb = match1[0]
            match1 = re.compile('<p class="p1">.+?href="(.+?)"[\s]*title="(.+?)".+?>(.+?)</a>').findall(matchp[i])
            p_url = match1[0][0]
            p_name = match1[0][1]
            sn = match1[0][2]
            p_list = sn + ': ' + p_name

            match1 = re.compile('class="time">(.+?)</span>').findall(matchp[i])
            if match1:
                p_list += ' [ ' + match1[0].strip() + ' ]'

            li = xbmcgui.ListItem(p_list, iconImage='', thumbnailImage=p_thumb)
            u = sys.argv[0] + "?mode=10&name=" + urllib.quote_plus(p_name) + "&url=" + urllib.quote_plus(p_url)
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, False, totalItems)

    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


##################################################################################
# Routine to display Singer list for selection
# - for 明星
# - selected page & filtrs
# - Video series list
# - user selectable pages
##################################################################################
def progListStar(name, url, cat, filtrs, page, listpage):
    fltrCategory = VIDEO_LIST[name][0]
    if page is None:
        page = '1'
    p_url = "http://list.letv.com/apin/stardata.json?d=%s&p=%s%s"

    if listpage is None:
        link = getHttpData(url)
        listpage = re.compile('class="label_list.+?>(.+?)</ul>').findall(link)[0]
        match = re.compile('<div class="sort_navy.+?">(.+?)</div>').findall(link)
        if len(match):
            listpage += match[0].replace('li', 'lo')
        cat = updateListSEL(name, url, cat, filtrs, 0, listpage)
    p_url = p_url % (fltrCategory, page, filtrs)

    # Fetch & build video titles list for user selection, highlight user selected filter
    li = xbmcgui.ListItem(name + '（第' + str(page) + '页）【' + cat + '】（按此选择)')
    u = sys.argv[0] + "?mode=9&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&cat=" + urllib.quote_plus(cat) + "&filtrs=" + urllib.quote_plus(filtrs) + "&page=1" + "&listpage=" + urllib.quote_plus(listpage)
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    link = getHttpData(p_url)
    if link is None:
        return

    # fetch and build the video series episode list
    content = simplejson.loads(link)
    vlist = content['star_list']
    totalItems = len(vlist)
    for i in range(0, totalItems):
        p_name = vlist[i]['name'].encode('utf-8')
        # v_url = 'http://so.letv.com/star?wd=%s&from=list' % p_name
        v_url = 'http://so.letv.com/s?wd=%s' % p_name
        p_thumb = vlist[i]['postS1']
        p_list = str(i + 1) + '. []' + p_name + '[] '

        match = vlist[i]['professional']
        p_prof = re.compile('":"(.+?)"').findall(match)
        if ((p_prof is not None) and len(p_prof)):
            p_list += '['
            for prof in p_prof:
                p_list += prof.encode('utf-8') + ' '
            p_list = p_list[:-1] + '] '

        p_area = vlist[i]['areaName']
        if (p_area is not None):
            p_list += '[' + p_area.encode('utf-8') + '] '

        p_birthday = vlist[i]['birthday']
        if (p_birthday is not None) and len(p_birthday):
            p_list += '[' + p_birthday.encode('utf-8') + '] '

        li = xbmcgui.ListItem(p_list, iconImage='', thumbnailImage=p_thumb)
        # li.setInfo(type = "Video", infoLabels = {"Title":p_list, "Artist":p_name})
        u = sys.argv[0] + "?mode=5" + "&name=" + urllib.quote_plus(p_name) + "&url=" + urllib.quote_plus(v_url) + "&thumb=" + urllib.quote_plus(p_thumb)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True, totalItems)

    p_itemCount = content['star_count']
    pages = getPages(p_itemCount, page)

    for page in pages:
        li = xbmcgui.ListItem("... 第" + str(page) + "页")
        u = sys.argv[0] + "?mode=4" + "&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&cat=" + urllib.quote_plus(cat) + "&filtrs=" + urllib.quote_plus(filtrs) + "&page=" + str(page) + "&listpage=" + urllib.quote_plus(listpage)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


##################################################################################
# Routine to extract video series selection menu for user playback
# - for 明星
# filtrs: movie cg=1; series cg=2; pn=pageNumber; ps=pageSize
# p_url = 'http://open.api.letv.com/ms?hl=1&dt=2&ph=420001&from=pcjs
# p_url += '&cg=1&pn=%s&ps=30&wd=%s&_=1391387253932' % (page, name)
##################################################################################
def progListStarVideo(name, url, page, thumb):
    if page is None:
        page = '1'
    p_url = 'http://open.api.letv.com/ms?hl=1&dt=2&pn=%s&ps=30&wd=%s' % (page, name)

    li = xbmcgui.ListItem('【' + name + ' | （第' + page + '页）】', iconImage='', thumbnailImage=thumb)
    u = sys.argv[0] + "?mode=5&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&thumb=" + urllib.quote_plus(thumb)
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    link = getHttpData(p_url)
    if link is None:
        return

    # mplaylist = xbmc.PlayList(0)  # use Music playlist for temporary storage
    mplaylist.clear()

    # fetch and build the video series episode list
    content = simplejson.loads(link)
    vlist = content['data_list']
    totalItems = len(vlist)
    for i in range(0, totalItems):
        p_title = vlist[i]['name'].encode('utf-8')

        # aid = str(vlist[i]['aid'])
        vid = str(vlist[i]['vid'])
        v_url = 'http://www.letv.com/ptv/vplay/%s.html' % vid

        try:
            p_thumb = vlist[i]['images']['150*200']
        except KeyError:
            p_thumb = vlist[i]['images']['160*120']
        except:
            p_thumb = ''

        p_name = p_list = str(i + 1) + '. ' + p_title + ' '
        p_category = vlist[i]['categoryName']
        if (p_category is not None) and len(p_category):
            p_subcategory = '-' + vlist[i]['subCategoryName']
            p_list += '[' + (p_category + p_subcategory).encode('utf-8') + ' '

        try:
            p_rating = float(vlist[i]['rating'])
            if (p_rating is not None and p_rating > 0.01):
                p_rating = "%0.1f" % p_rating
                p_list += '[' + p_rating + ']'
        except:
            pass

        p_dx = int(vlist[i]['duration'])
        if (p_dx is not None) and (p_dx > 0):
            p_duration = "[%02d:%02d]" % (int(p_dx / 60), (p_dx % 60))
            p_list += '[' + p_duration + ']'

        li = xbmcgui.ListItem(p_list, iconImage='', thumbnailImage=p_thumb)
        # li.setInfo(type = "Video", infoLabels = {"Title":p_list, "Artist":p_name})
        u = sys.argv[0] + "?mode=10" + "&name=" + urllib.quote_plus(p_name) + "&url=" + urllib.quote_plus(v_url) + "&thumb=" + urllib.quote_plus(p_thumb)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True, totalItems)
        mplaylist.add(v_url, li)

    # Fetch and build page selection menu
    p_itemCount = content['data_count']
    pages = getPages(p_itemCount, page)

    for page in pages:
        li = xbmcgui.ListItem("... 第" + str(page) + "页")
        u = sys.argv[0] + "?mode=5" + "&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&page=" + str(page) + "&thumb=" + urllib.quote_plus(thumb)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


##################################################################################
# Routine to fetch and build the ugc selection menu
# - for categories not in VIDEO_LIST
# - selected page & filtrs (user selectable)
# - ugc items list
# - user selectable pages
# http://list.letv.com/apin/chandata.json?a=50006&c=3&d=2&md=&o=9&p=2&vt=440141
##################################################################################
def progListUgc(name, url, cat, filtrs, page, listpage):
    fltrCategory = UGC_LIST[name][0]
    if page is None:
        page = '1'
    p_url = "http://list.letv.com/apin/chandata.json?c=%s&d=2&md=&p=%s%s"

    if listpage is not None:
        link = getHttpData(url)
        listpage = re.compile('class="label_list.+?>(.+?)</ul>').findall(link)[0]
        listpage += re.compile('class="sort_navy.+?">(.+?)</div>').findall(link)[0].replace('li', 'lo')
        cat = updateListSEL(name, url, cat, filtrs, 0, listpage)
    p_url = p_url % (fltrCategory, page, filtrs)

    # Fetch & build video titles list for user selection, highlight user selected filter
    cat = re.sub(' ', '', cat)
    li = xbmcgui.ListItem(name + '（第' + str(page) + '页）【' + cat + '】（按此选择)')
    if listpage is None:
        listpage = ''
    u = sys.argv[0] + "?mode=9&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&cat=" + urllib.quote_plus(cat) + "&filtrs=" + urllib.quote_plus(filtrs) + "&page=1" + "&listpage=" + urllib.quote_plus(listpage)
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    link = getHttpData(p_url)
    if link is None:
        return

    # mplaylist = xbmc.PlayList(0)  # use Music playlist for temporary storage
    mplaylist.clear()

    # fetch and build the video series episode list
    content = simplejson.loads(link)

    vlist = content['data_list']
    totalItems = len(vlist)
    for i in range(0, totalItems):
        vid = str(vlist[i]['vid'])
        v_url = 'http://www.letv.com/ptv/vplay/%s.html' % vid
        p_title = vlist[i]['name'].encode('utf-8')

        try:
            p_thumb = vlist[i]['images']['150*200']
        # except KeyError:
        #    p_thumb = vlist[i]['images']['160*120']
        except:
            pass

        p_list = p_name = str(i + 1) + '. ' + p_title + ' '
        p_artist = vlist[i]['actor']
        if (p_artist is not None) and len(p_artist):
            p_list += '['
            for actor in p_artist:
                p_list += actor.encode('utf-8') + ' '
            p_list = p_list[:-1] + ']'

        p_dx = int(vlist[i]['duration'])
        if (p_dx is not None):
            p_duration = "[%02d:%02d]" % (int(p_dx / 60), (p_dx % 60))
            p_list += '[' + p_duration + ']'

        p_album = vlist[i]['albumName']
        if (p_album is not None):
            p_album = p_album.encode('utf-8')
            p_list += '[' + p_album + ']'

        li = xbmcgui.ListItem(p_list, iconImage='', thumbnailImage=p_thumb)
        # li.setInfo(type = "Video", infoLabels = {"Title":p_list, "Artist":p_artist})
        u = sys.argv[0] + "?mode=20" + "&name=" + urllib.quote_plus(p_list) + "&url=" + urllib.quote_plus(v_url) + "&thumb=" + urllib.quote_plus(p_thumb)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, False, totalItems)
        mplaylist.add(v_url, li)

    # Fetch and build page selection menu
    p_itemCount = content['data_count']
    pages = getPages(p_itemCount, page)

    for page in pages:
        li = xbmcgui.ListItem("... 第" + str(page) + "页")
        u = sys.argv[0] + "?mode=8" + "&name=" + urllib.quote_plus(name) + "&url=" + urllib.quote_plus(url) + "&cat=" + urllib.quote_plus(cat) + "&filtrs=" + urllib.quote_plus(filtrs) + "&page=" + str(page) + "&listpage=" + urllib.quote_plus(listpage)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


#################################################################################
# Get user input for LeTV site
# http://open.api.letv.com/ms?hl=1&dt=2&ph=420001&from=pcjs&pn=1&ps=25&wd=%E7%88%B1%E4%BA%BA&_=1392364710043
##################################################################################
def searchLetv():
    keyboard = Apps('', '请输入搜索内容')
    # keyboard.setHiddenInput(hidden)
    xbmc.sleep(1500)
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        keyword = keyboard.getText()
        letvSearchList(keyword, '1')


##################################################################################
# Routine to search LeTV site based on user given keyword for:
##################################################################################
def letvSearchList(name, page):
    p_url = 'http://open.api.letv.com/ms?hl=1&dt=2&ph=420001&from=pcjs&pn=%s&ps=30&wd=%s'
    p_url = p_url % (page, urllib.quote(name))
    link = getHttpData(p_url)

    li = xbmcgui.ListItem('[COLOR FFFF0000]当前搜索: 第' + page + '页[/COLOR][COLOR FFFFFF00] (' + name + ')[/COLOR]【[COLOR FF00FF00]' + '点此输入新搜索内容' + '[/COLOR]】')
    u = sys.argv[0] + "?mode=31&name=" + urllib.quote_plus(name) + "&page=" + page
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    if link is None:
        li = xbmcgui.ListItem('  抱歉，没有找到[COLOR FFFF0000] ' + name + ' [/COLOR]的相关视频')
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, False)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        return

    # fetch and build the video series episode list
    content = simplejson.loads(link)
    vlist = content['data_list']
    totalItems = len(vlist)
    for i in range(0, totalItems):
        vid = str(vlist[i]['vid'])
        v_url = 'http://www.letv.com/ptv/vplay/%s.html' % vid
        p_title = vlist[i]['name'].encode('utf-8')

        try:
            p_thumb = vlist[i]['images']['150*200']
        except KeyError:
            p_thumb = vlist[i]['images']['160*120']
        except:
            pass

        p_categoryName = vlist[i]['categoryName']
        if (p_categoryName is not None):
            p_list = p_name = str(i + 1) + '. [' + p_categoryName.encode('utf-8') + '] ' + p_title + ' '
        else:
            p_list = p_name = str(i + 1) + '. ' + p_title + ' '

        try:
            p_rating = float(vlist[i]['rating'])
            if (p_rating is not None and p_rating > 0.01):
                p_rating = "%0.1f" % p_rating
                p_list += '[' + p_rating + ']'
        except:
            pass

        p_dx = int(vlist[i]['duration'])
        if (p_dx is not None):
            p_duration = "[%02d:%02d]" % (int(p_dx / 60), (p_dx % 60))
            p_list += '[' + p_duration + ']'

        p_artists = vlist[i]['actor']
        if ((p_artists is not None) and len(p_artists)):
            p_artist = ""
            p_list += '['
            for key in p_artists:
                p_artist += p_artists[key].encode('utf-8') + ' '
            p_list += p_artist[:-1] + ']'

        li = xbmcgui.ListItem(p_list, iconImage='', thumbnailImage=p_thumb)
        u = sys.argv[0] + "?mode=10" + "&name=" + urllib.quote_plus(p_list) + "&url=" + urllib.quote_plus(v_url) + "&thumb=" + urllib.quote_plus(p_thumb)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, False, totalItems)

    # Fetch and build page selection menu
    p_itemCount = content['video_count']
    pages = getPages(p_itemCount, page)

    for page in pages:
        li = xbmcgui.ListItem("... 第" + str(page) + "页")
        u = sys.argv[0] + "?mode=32" + "&name=" + urllib.quote_plus(name) + "&page=" + str(page)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, li, True)

    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


##################################################################################
# LeTV Video Link Decode Algorithm
# Extract all the video list and start playing first found valid link
# http://www.letv.com/ptv/vplay/1967644.html
##################################################################################
def calcTimeKey(t):
    ror = lambda val, r_bits, : ((val & (2 ** 32 - 1)) >> r_bits % 32) | (val << (32 - (r_bits % 32)) & (2 ** 32 - 1))
    return ror(ror(t, 773625421 % 13) ^ 773625421, 773625421 % 17)


# # --- decrypt m3u8 data --------- ##
def decode(data):
    version = data[0:5]
    if version.lower() == b'vc_01':
        # get real m3u8
        loc2 = bytearray(data[5:])
        length = len(loc2)
        loc4 = [0] * (2 * length)
        for i in range(length):
            loc4[2 * i] = loc2[i] >> 4
            loc4[2 * i + 1] = loc2[i] & 15
        loc6 = loc4[len(loc4) - 11:] + loc4[:len(loc4) - 11]
        loc7 = [0] * length
        for i in range(length):
            loc7[i] = (loc6[2 * i] << 4) + loc6[2 * i + 1]
        return ''.join([chr(i) for i in loc7])
    else:
        # directly return
        return data


# # ------ video links decrypt ---------------------- ##
def decrypt_url(url, mCheck=True):
    videoRes = int(__addon__.getSetting('video_resolution'))
    serverIndex = int(__addon__.getSetting('video_server')) - 1
    vparamap = {0:'1300', 1:'720p', 2:'1080p'}

    t_url = 'http://api.letv.com/mms/out/video/playJson?id={}&platid=1&splatid=101&format=1&tkey={}&domain=www.letv.com'
    t_url2 = '&ctv=pc&m3v=1&termid=1&format=1&hwtype=un&ostype=Linux&tag=letv&sign=letv&expect=3&tn={}&pay=0&iscpn=f9051&rateid={}'

    try:
        vid = re.compile('/vplay/(\d+).html').findall(url)[0]
        j_url = t_url.format(vid, calcTimeKey(int(time.time())))
        link = getHttpData(j_url)
        info = simplejson.loads(link)
        playurl = info['playurl']
    except:
        return ''

    if (mCheck):
        pDialog.update(30)
    stream_id = None
    support_stream_id = info["playurl"]["dispatch"].keys()
#     print("Current Video Supports:")
#     for i in support_stream_id:
#         print("\t--format",i,"<URL>")
    if "1080p" in support_stream_id:
        stream_id = '1080p'
    elif "720p" in support_stream_id:
        stream_id = '720p'
    else:
        stream_id = sorted(support_stream_id, key=lambda i: int(i[1:]))[-1]

    # pick a random domain or user selected to minimize overloading single server
    if (serverIndex == -1):
        index = random.randint(0, len(playurl['domain']) - 1)
    else:
        index = serverIndex % len(playurl['domain'])
    domain = playurl['domain'][index]
    # print "### Video Server Selection: %i %i = %s" % (serverIndex, index, playurl['domain'])

    vodRes = playurl['dispatch']
    vod = None
    while (vod is None) and (videoRes >= 0):
        vRes = vparamap.get(videoRes, 0)
        try:
            vod = vodRes.get(vRes)[0]
        except:
            pass
        videoRes -= 1
    if vod is None:
        try:
            vod = playurl['dispatch']['1000'][0]
        except KeyError:
            vod = playurl['dispatch']['350'][0]
        except:
            return ''

    url = domain + vod
    url += t_url2.format(random.random(), vRes)
    ext = vodRes[stream_id][1].split('.')[-1]

    r2 = getHttpData(url)
    if (mCheck):
        pDialog.update(60, line2="### 服务器  [ %i ]" % (index + 1))

    # try:
    info2 = simplejson.loads(r2)

    # need to decrypt m3u8 (encoded) - may hang here
    m3u8 = getHttpData(info2["location"], False, True)
    if (m3u8 is None):
        return None

    if (mCheck):
        pDialog.update(90)
    m3u8_list = decode(m3u8)
        # urls contains array of v_url video links for playback
    urls = re.findall(r'^[^#][^\r]*', m3u8_list, re.MULTILINE)
    return urls


##################################################################################
def playVideoLetv(name, url, thumb):
    pDialog.create('匹配视频', '请耐心等候! 尝试匹配视频文件 ...')
    pDialog.update(0)

    v_urls = decrypt_url(url)
    pDialog.close()

    if len(v_urls):
        xplayer.play(name, thumb, v_urls)

        # need xmbc.sleep to make xbmc callback working properly
        while xplayer.is_active:
            xbmc.sleep(100)
        pDialog.close()
    else:
        # if '解析失败' in link: (license constraint etc)
        dialog.ok(__addonname__, '无法播放：未匹配到视频文件，请选择其它视频')


##################################################################################
# Continuous Player start playback from user selected video
# User backspace to previous menu will not work - playlist = last selected
##################################################################################
def playVideoUgc(name, url, thumb):
    xplayer.play(name, thumb)

    # need xmbc.sleep(100) to make xbmc callback working properly
    while xplayer.is_active:
        xbmc.sleep(100)
    pDialog.close()
    # return


xplayer = LetvPlayer()
mplaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
dialog = xbmcgui.Dialog()
pDialog = xbmcgui.DialogProgress()

params = sys.argv[2][1:]
params = dict(urllib2.urlparse.parse_qsl(params))

url = params.get('url')
name = params.get('name')
page = params.get('page', '1')
cat = params.get('cat')
filtrs = params.get('filtrs')
thumb = params.get('thumb')
listpage = params.get('listpage')
mode = params.get('mode')

runlist = {
    None: 'mainMenu()',
    '1': 'progListMovie(name, url, cat, filtrs, page, listpage)',
    '2': 'progListSeries(name, url, thumb)',
    '4': 'progListStar(name, url, cat, filtrs, page, listpage)',
    '5': 'progListStarVideo(name, url, page, thumb)',
    '8': 'progListUgc(name, url, cat, filtrs, page, listpage)',
    '9': 'updateListSEL(name, url, cat, filtrs, page, listpage)',
    '10': 'playVideoLetv(name, url, thumb)',
    '20': 'playVideoUgc(name, url, thumb)i',
    '31': 'searchLetv()',
    '32': 'letvSearchList(name, page)'
}

eval(runlist[mode])
