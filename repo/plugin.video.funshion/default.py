# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib2
import urllib
import re
import sys
import gzip
import StringIO
from random import randrange
import simplejson
UserAgent_IPAD = 'Mozilla/5.0 (iPad; U; CPU OS 4_2_1 like Mac OS X; ja-jp) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148 Safari/6533.18.5'

# get wrong IP from some local IP
unusableIP = ("121.32.237.24",
              "121.32.237.42",
              "222.84.164.2",
              "122.228.57.21")

# followings are usable
usableIP = ("112.25.81.203",
            "111.63.135.120",
            "122.72.64.198",
            "183.203.12.197",
            "223.82.247.101",
            "222.35.249.3")


########################################################################
# 风行视频(Funshion)"
########################################################################
# v1.1.1 2015.12.04 (taxigps)
# - Update video list fetching for site change
# - Add requires of simplejson

# Plugin constants
__addon__     = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__profile__   = xbmc.translatePath(__addon__.getAddonInfo('profile'))

#CHANNEL_LIST = [['电影','movie'],['电视剧','tv'],['动漫','cartoon'],['综艺','variety'],['新闻','news'],['娱乐','ent'],['体育','sports'],['搞笑','joke'],['时尚','fashion'],['生活','life'],['旅游','tour'],['科技','tech']]
CHANNEL_LIST = {'电影': 'c-e794b5e5bdb1',
                '电视剧': 'c-e794b5e8a786e589a7',
                '动漫': 'c-e58aa8e6bcab',
                '综艺': 'c-e7bbbce889ba',
                '微电影': 'c-e5beaee794b5e5bdb1',
                '音乐': 'c-e99fb3e4b990',
                '纪录片': 'c-e7baaae5bd95e78987',
                '娱乐': 'c-e5a8b1e4b990',
                '体育': 'c-e4bd93e882b2',
                '搞笑': 'c-e6909ee7ac91',
                '新闻': 'c-e696b0e997bb',
                '旅游': 'c-e69785e6b8b8',
                '汽车': 'c-e6b1bde8bda6',
                '游戏': 'c-e6b8b8e6888f',
                '美女': 'c-e7be8ee5a5b3',
                '时尚': 'c-e697b6e5b09a',
                '母婴': 'c-e6af8de5a9b4',
                '健康': 'c-e581a5e5bab7',
                '科技': 'c-e7a791e68a80',
                '生活': 'c-e7949fe6b4bb',
                '军事': 'c-e5869be4ba8b'}

SERIES_LIST = {'电视剧', '动漫', '综艺'}
MOVIE_LIST = {'电影', '微电影'}
COLOR_LIST = ['[COLOR FFFF0000]','[COLOR FF00FF00]','[COLOR FFFFFF00]','[COLOR FF00FFFF]','[COLOR FFFF00FF]']

RES_LIST = [['tv', '低清'],
            ['dvd', '标清'],
            ['high-dvd', '高清'],
            ['super_dvd', '超清']]

LANG_LIST = [['chi','国语'], ['arm','粤语'], ['und','原声']]
UserAgent = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)'


########################################################################
def log(txt):
    pass
#    message = '%s: %s' % (__addonname__, txt)
#    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


########################################################################
def getHttpData(url):
    log("%s::url - %s" % (sys._getframe().f_code.co_name, url))
    headers = {"Accept":"application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
               "Accept-Charset": "GBK,utf-8;q=0.7,*;q=0.3",
               "Accept-Encoding": "gzip",
               "Accept-Language": "zh-CN,zh;q=0.8",
               "Cache-Control": "max-age=0",
               "Connection": "keep-alive",
               "User-Agent": UserAgent_IPAD}

    req = urllib2.Request(url, headers=headers)
    try:
        response = urllib2.urlopen(req)
        httpdata = response.read()
        if response.headers.get('content-encoding') == 'gzip':
            httpdata = gzip.GzipFile(fileobj=StringIO.StringIO(httpdata)).read()
        charset = response.headers.getparam('charset')
        response.close()
    except:
        log("%s (%d) [%s]" % (
               sys.exc_info()[2].tb_frame.f_code.co_name,
               sys.exc_info()[2].tb_lineno,
               sys.exc_info()[1]
               ))
        return ''

    httpdata = re.sub('\t|\n|\r', ' ', httpdata)
    match = re.compile('<meta http-equiv=["]?[Cc]ontent-[Tt]ype["]? content="text/html;[\s]?charset=(.+?)"').findall(httpdata)
    if match:
        charset = match[0]
    else:
        match = re.compile('<meta charset="(.+?)"').findall(httpdata)
        if match:
            charset = match[0]
    if charset:
        charset = charset.lower()
        if (charset != 'utf-8') and (charset != 'utf8'):
            httpdata = httpdata.decode(charset, 'ignore').encode('utf8', 'ignore')

    return httpdata


########################################################################
def searchDict(dlist, idx):
    for i in range(0, len(dlist)):
        if dlist[i][0] == idx:
            return dlist[i][1]
    return ''


##################################################################################
# Routine to fetch and build video filter list
# Filters are automatically extracted for each category.
# Common routine for all categories
##################################################################################
def getListSEL(listpage):
    titlelist = []
    catlist = []
    itemList = []

    # extract categories selection
    match = re.compile('<div class="ls-nav-bar.+?>(.+?)</div>', re.DOTALL).findall(listpage)
    for k, list in enumerate(match):
        title = re.compile('<label class="bar-name">(.+?)</label>').findall(list)
        itemLists = re.compile('<a href="/[a-z]+?/(.+?)/">(.+?)</a>').findall(list)
        if (len(itemLists) > 1):
            itemList = [[x[0], x[1].strip()] for x in itemLists]
            item1 = itemList[0][0].split('.')
            item2 = itemList[1][0].split('.')
            ilist1 = len(item1)
            ilist2 = len(item2)

            # get the index of the current item variables
            for j in range(ilist2):
                if not (item2[j] in item1):
                    break

            icnt = len(itemList)
            # must do in reverse if to remove any item from array
            for i in range(icnt-1, -1, -1):
                if (itemList[i][1] == "取消选中"):
                    itemList.remove(itemList[i])
                    continue
                # no filter for first item selection i.e. "全部"
                if (i == 0) and (ilist1 < ilist2):
                    itemList[i][0] = ''
                else:
                    itemx = itemList[i][0].split('.')
                    itemList[i][0] = itemx[j]

            if len(title):
                titlelist.append(title[0])
            else:           # Order selection - missing label
                titlelist.append('排序方式')
            catlist.append(itemList)
            # print k, itemLists, title, itemList

    return titlelist, catlist


##################################################################################
# Routine to update video list as per user selected filtrs
##################################################################################
def updateListSEL(name, type, cat, filtrs, page, listpage):
    dialog = xbmcgui.Dialog()
    titlelist, catlist = getListSEL(listpage)
    fltr = filtrs[1:].split('.')

    cat = ''
    selection = ''
    for icat, title in enumerate(titlelist):
        # skip video category selection
        if title == "分类":
            continue
        fltrList = [x[0] for x in catlist[icat]]
        list = [x[1] for x in catlist[icat]]
        sel = -1
        if (page):       # page=0: auto extract cat only
            sel = dialog.select(title, list)
        if sel == -1:
            # return last choice selected if ESC by user
            if len(fltr) == len(titlelist):
                sel = fltrList.index(fltr[icat])
            else:           # default for first time entry
                sel = 0
        ctype = catlist[icat][sel][1]
        if ctype == '全部':
            ctype += title
        cat += COLOR_LIST[icat % 5] + ctype + '[/COLOR]|'
        selx = catlist[icat][sel][0]
        if (selx != ''):      # no need to add blank filter
            selection += '.'+selx
    filtrs = selection
    cat = cat[:-1]

    if not page:
        return cat
    else:
        progList(name, type, cat, filtrs, page, listpage)


##################################################################################
def progList(name, type, cat, filtrs, page, listpage):
    if page is None:
        page = '1'
    # p_url = 'http://list.funshion.com/%s/pg-%s%s/'
    ## p_url = 'http://www.funshion.com/list/%s/pg-%s%s/'

    if name in (SERIES_LIST | MOVIE_LIST):
        p_url = "http://www.fun.tv/retrieve/%s.n-e5bdb1e78987%s.pg-%s"
    else:
        p_url = "http://www.fun.tv/retrieve/%s%s.pg-%s"

    if listpage is None:
        url = p_url % (type, '', page)
        link = getHttpData(url)

        match = re.compile('<div class="ls-nav" id="ls-nav">(.+?</div>)</div>', re.DOTALL).findall(link)
        if match:
            listpage = match[0]
        match = re.compile('<div class="ls-sort" id="ls-sort">(.+?</div>)', re.DOTALL).findall(link)
        if len(match):
            listpage += match[0]
        cat = updateListSEL(name, type, cat, filtrs, 0, listpage)
    else:
        url = p_url % (type, filtrs, page)
        link = getHttpData(url)

    # Fetch & build video titles list for user selection, highlight user selected filtrs
    li = xbmcgui.ListItem(name + '（第' + page + '页）【' + cat + '】（按此选择)')
    u = sys.argv[0]+"?mode=10&name="+urllib.quote_plus(name)+"&type="+type+"&cat="+urllib.quote_plus(cat)+"&filtrs="+urllib.quote_plus(filtrs)+"&page=1"+"&listpage="+urllib.quote_plus(listpage)
    xbmcplugin.addDirectoryItem(pluginhandle, u, li, True)

    if link is None:
        return
    # Movie, Video, Series, Variety & Music types need different routines
    if name in SERIES_LIST:
        isdir = True
        mode = '2'
    elif name in MOVIE_LIST:
        isdir = False
        mode = '3'
    else:    # 娱乐,新闻,体育,搞笑,时尚,生活,旅游,科技
        isdir = False
        mode = '4'
        playlist = xbmc.PlayList(0) # use Music playlist for temporary storage
        playlist.clear()

    match = re.compile('<div class="mod-vd-i.+?>(.+?)</div></div>', re.DOTALL).findall(link)
    totalItems = len(match) + 1

    # COLOR_LIST = ['[COLOR FFFF0000]','[COLOR FF00FF00]','[COLOR FFFFFF00]','[COLOR FF00FFFF]','[COLOR FFFF00FF]']
    for i in range(0, len(match)):
        match1 = re.compile("/vplay/[a-z]+-(.+?)/").findall(match[i])
        p_id = match1[0]

        match1 = re.compile('<img src=.+?_lazysrc=[\'|"]+(.*?)[\'|"]+.+?alt="(.+?)"').findall(match[i])
        p_thumb = match1[0][0]
        p_name = match1[0][1].replace('&quot;', '"')

        p_name1 = str(i+1) + '. ' + p_name + ' '
        match1 = re.compile('<span>(.+?)</span>').findall(match[i])
        if len(match1):
            p_name1 += '[COLOR FF00FFFF](' + match1[0] + ')[/COLOR] '

        match1 = re.compile('<b class="score">(.+?)</b>').findall(match[i])
        if len(match1):
            p_rating = match1[0]
            p_name1 += '[COLOR FFFF00FF][' + p_rating + '][/COLOR]'

        if match[i].find("class='ico-dvd spdvd'") > 0:
            p_name1 += ' [COLOR FFFFFF00][超清][/COLOR]'
        elif match[i].find("class='ico-dvd hdvd'") > 0:
            p_name1 += ' [COLOR FF00FFFF][高清][/COLOR]'

        match1 = re.compile('<i class="tip">(.+?)</i>').findall(match[i])
        if len(match1):
            p_duration = match1[0]
            p_name1 += ' [COLOR FF00FF00][' + p_duration + '][/COLOR]'

        match1 = re.compile('<p class="desc">(.+?)</p>').findall(match[i])
        if len(match1):
            p_desp = match1[0]
            p_name1 += ' (' + p_desp + ')'

        li = xbmcgui.ListItem(p_name1, iconImage='', thumbnailImage=p_thumb)
        u = sys.argv[0]+"?mode="+mode+"&name="+urllib.quote_plus(p_name1)+"&id="+urllib.quote_plus(p_id)+"&thumb="+urllib.quote_plus(p_thumb)+"&type="+urllib.quote_plus(type)
        li.setInfo(type="Video", infoLabels={"Title": p_name})
        xbmcplugin.addDirectoryItem(pluginhandle, u, li, isdir, totalItems)
        if mode == '4':
            playlist.add(p_id, li)

    # Construct page selection
    match = re.compile('<div class="pager-wrap fix">(.+?)</div>', re.DOTALL).findall(link)
    if match:
        match1 = re.compile("<a[\s]+?href='.+?'>(\d+)</a>", re.DOTALL).findall(match[0])
        plist = [page]
        for num in match1:
            if (num not in plist):
                plist.append(num)
                li = xbmcgui.ListItem("... 第" + num + "页")
                u = sys.argv[0]+"?mode=1&name="+urllib.quote_plus(name)+"&type="+urllib.quote_plus(type)+"&cat="+urllib.quote_plus(cat)+"&filtrs="+urllib.quote_plus(filtrs)+"&page="+num+"&listpage="+urllib.quote_plus(listpage)
                xbmcplugin.addDirectoryItem(pluginhandle, u, li, True, totalItems)

    xbmcplugin.setContent(pluginhandle, 'movies')
    xbmcplugin.endOfDirectory(pluginhandle)


##################################################################################
def rootList():
    totalItems = len(CHANNEL_LIST)
    cat = "全部"
    i = 0
    for name in CHANNEL_LIST:
        i += 1
        ilist = "[COLOR FF00FFFF]%s. %s[/COLOR]" % (i, name)
        li = xbmcgui.ListItem(ilist)
        u = sys.argv[0]+"?mode=1&" + \
                        "name="+urllib.quote_plus(name) + \
                        "&type="+urllib.quote_plus(CHANNEL_LIST[name]) + \
                        "&cat="+cat + \
                        "&filtrs=&page=1" + \
                        "&listpage="
        xbmcplugin.addDirectoryItem(pluginhandle, u, li, True, totalItems)
    xbmcplugin.endOfDirectory(pluginhandle)


##################################################################################
def seriesList(name, id, thumb):
    # url = 'http://api.funshion.com/ajax/get_web_fsp/%s/mp4?isajax=1' % (id)
    url = 'http://api.funshion.com/ajax/vod_panel/%s/w-1?isajax=1' % (id) #&dtime=1397342446859
    link = getHttpData(url)
    json_response = simplejson.loads(link)
    if json_response['status'] == 404:
        ok = xbmcgui.Dialog().ok(__addonname__, '本片暂不支持网页播放')
        return

    resolution = int(__addon__.getSetting('resolution'))
    if resolution == 0:
        resolution = 1            # set default resolution as DVD
    else:
        resolution -= 1

    items = json_response['data']['videos']
    name = json_response['data']['name'].encode('utf-8')
    totalItems = len(items)
    for item in items:
        p_name = '%s %s' % (name, item['name'].encode('utf-8'))
        # p_number = str(item['number'])
        p_id2 = item['streams'][resolution]['hashid']
        p_thumb = item['pic'].encode('utf-8')
        if not p_thumb:
            p_thumb = thumb

        li = xbmcgui.ListItem(p_name, iconImage='', thumbnailImage=p_thumb)
        u = sys.argv[0] + "?mode=3&name=" + urllib.quote_plus(p_name) + "&id=" + urllib.quote_plus(id)+ "&thumb=" + urllib.quote_plus(p_thumb) + "&id2=" + urllib.quote_plus(p_id2)
        xbmcplugin.addDirectoryItem(pluginhandle, u, li, False, totalItems)
    xbmcplugin.setContent(pluginhandle, 'episodes')
    xbmcplugin.endOfDirectory(pluginhandle)


##################################################################################
def selResolution(items):
    ratelist = []
    for i in range(0, len(items)):
        if items[i][0] == RES_LIST[0][0]:
            ratelist.append([3, RES_LIST[0][1], i]) # [清晰度设置值, 清晰度, items索引]
        if items[i][0] == RES_LIST[1][0]:
            ratelist.append([2, RES_LIST[1][1], i])
        if items[i][0] == RES_LIST[2][0]:
            ratelist.append([1, RES_LIST[2][1], i])
    ratelist.sort()
    if len(ratelist) > 1:
        resolution = int(__addon__.getSetting('resolution'))
        if resolution == 0:    # 每次询问视频清晰度
            list = [x[1] for x in ratelist]
            sel = xbmcgui.Dialog().select('清晰度（低网速请选择低清晰度）', list)
            if sel == -1:
                return None, None
        else:
            sel = 0
            while sel < len(ratelist)-1 and resolution > ratelist[sel][0]:
                sel += 1
    else:
        sel = 0
    return items[ratelist[sel][2]][1], ratelist[sel][1]


def PlayVideo_test(name, id, thumb):
    url = 'http://api.funshion.com/ajax/vod_panel/%s/w-1?isajax=1' % (id) #&dtime=1397342446859
    link = getHttpData(url)
    json_response = simplejson.loads(link)

    resolution = int(__addon__.getSetting('resolution'))
    if resolution == 0:
        resolution = 1            # set default resolution as DVD
    else:
        resolution -= 1

    hashid = json_response['data']['videos'][0]['streams'][resolution]['hashid']

    url = 'http://jobsfe.funshion.com/query/v1/mp4/%s.json' % (hashid)

    link = getHttpData(url)
    json_response = simplejson.loads(link)
    if json_response['return'].encode('utf-8') == 'succ':
        listitem = xbmcgui.ListItem(name, thumbnailImage=thumb)

        #xbmc.Player().play(json_response['playlist'][0]['urls'][0], listitem)
        # Randomly pick a server to stream video
        v_urls = json_response['playlist'][0]['urls']   #json_response['data']['fsps']['mult']
        # print "streamer servers: ", len(v_urls), v_urls, link, json_response['playlist'][0]
        try:
            i_url = randrange(len(v_urls))
        except:
            i_url = 0

        v_url = v_urls[i_url]
        ip = re.compile('http://(\d+\.\d+\.\d+\.\d+)').findall(v_url)
        if ip[0] not in usableIP:    # replace a usable IP
            i_url = randrange(len(usableIP))
            v_url = re.sub('http://(\d+\.\d+\.\d+\.\d+)',
                           'http://%s'%(usableIP[i_url]), v_url)
        xbmc.Player().play(v_url, listitem)
    else:
        ok = xbmcgui.Dialog().ok(__addonname__, '没有可播放的视频')


##################################################################################
def PlayVideo(name, id, thumb, id2):
    if id2 == '1':
        # url = 'http://api.funshion.com/ajax/get_webplayinfo/%s/%s/mp4' % (id, id2)
        url = 'http://api.funshion.com/ajax/get_web_fsp/%s/mp4' % (id)
        link = getHttpData(url)
        json_response = simplejson.loads(link)
        if not json_response['data']:
            ok = xbmcgui.Dialog().ok(__addonname__, '没有可播放的视频')
            return

        # idx = (id2 - 1) # may also fetch with array index for a given id2 number
        try:
            hashid = json_response['data']['fsps']['mult'][0]['hashid'].encode('utf-8')
        except:
            ok = xbmcgui.Dialog().ok(__addonname__, '没有可播放的视频')
            return
    else:
        # hashid provided by series - feteching no required
        hashid = id2       # provided by series

    # url = 'http://jobsfe.funshion.com/query/v1/mp4/c847d5281686aab8bb3f4b338802c29fd236f8b2.json?clifz=fun&mac=&tm=1399766798&token=OVKHzVc57+mVfV1qDkAtYcmYKqbLRsoR2Uyv6aaI8vqW4IaC0VO+iWV0rXmhiMoRXXYhrI1/6J2dgg=='
    url = 'http://jobsfe.funshion.com/query/v1/mp4/%s.json' % (hashid)

    link = getHttpData(url)
    json_response = simplejson.loads(link)
    if json_response['return'].encode('utf-8') == 'succ':
        listitem = xbmcgui.ListItem(name, thumbnailImage=thumb)

        #xbmc.Player().play(json_response['playlist'][0]['urls'][0], listitem)
        # Randomly pick a server to stream video
        v_urls = json_response['playlist'][0]['urls']   #json_response['data']['fsps']['mult']
        # print "streamer servers: ", len(v_urls), v_urls, link, json_response['playlist'][0]
        try:
            i_url = randrange(len(v_urls))
        except:
            i_url = 0
        v_url = v_urls[i_url]
        ip = re.compile('http://(\d+\.\d+\.\d+\.\d+\)/').findall(v_url)
        if ip[0] not in usableIP:    # replace a usable IP
            i_url = randrange(len(usableIP))
            v_url = re.sub('http://(\d+\.\d+\.\d+\.\d+)',
                           'http://%s'%(usableIP[i_url]), v_url)
        xbmc.Player().play(v_url, listitem)
    else:
        ok = xbmcgui.Dialog().ok(__addonname__, '没有可播放的视频')


##################################################################################
# Retrieve json file not further support ['dub_one'] key
##################################################################################
def PlayVideox(name, id, thumb, id2):
    url = 'http://api.funshion.com/ajax/get_webplayinfo/%s/%s/mp4' % (id, id2)
    link = getHttpData(url)
    json_response = simplejson.loads(link)
    if not json_response['playinfos']:
        ok = xbmcgui.Dialog().ok(__addonname__, '没有可播放的视频')
        return

    langlist = set([x['dub_one'].encode('utf-8') for x in json_response['playinfos']])
    langlist = [x for x in langlist]
    langid = json_response['playinfos'][0]['dub_one'].encode('utf-8')
    lang_select = int(__addon__.getSetting('lang_select'))    # 默认|每次选择|自动首选
    if lang_select != 0 and len(langlist) > 1:
        if lang_select == 1:
            list = [searchDict(LANG_LIST, x) for x in langlist]
            sel = xbmcgui.Dialog().select('选择语言', list)
            if sel == -1:
                return
            langid = langlist[sel]
        else:
            lang_prefer = __addon__.getSetting('lang_prefer')    # 国语|粤语
            for i in range(0, len(LANG_LIST)):
                if LANG_LIST[i][1] == lang_prefer:
                    if LANG_LIST[i][0] in langlist:
                        langid = LANG_LIST[i][0]
                    break

    items = [[x['clarity'].encode('utf-8'), x['hashid'].encode('utf-8')]for x in json_response['playinfos'] if x['dub_one'].encode('utf-8') == langid]
    hashid, res = selResolution(items)
    lang = searchDict(LANG_LIST, langid)
    name = '%s(%s %s)' % (name, lang, res)
    url = 'http://jobsfe.funshion.com/query/v1/mp4/%s.json' % (hashid)
    link = getHttpData(url)
    json_response = simplejson.loads(link)
    if json_response['return'].encode('utf-8') == 'succ':
        listitem = xbmcgui.ListItem(name, thumbnailImage=thumb)
        xbmc.Player().play(json_response['playlist'][0]['urls'][0], listitem)
    else:
        ok = xbmcgui.Dialog().ok(__addonname__, '没有可播放的视频')


##################################################################################
def PlayVideo2(name, id, thumb, type):
    videoplaycont = __addon__.getSetting('video_vplaycont')

    playlistA = xbmc.PlayList(0)
    playlist = xbmc.PlayList(1)
    playlist.clear()

    v_pos = int(name.split('.')[0]) - 1
    psize = playlistA.size()
    ERR_MAX = psize-1
    TRIAL = 1
    errcnt = 0
    k = 0

    pDialog = xbmcgui.DialogProgress()
    ret = pDialog.create('匹配视频', '请耐心等候! 尝试匹配视频文件 ...')
    pDialog.update(0)

    for x in range(psize):
        # abort if ERR_MAX or more access failures and no video playback
        if (errcnt >= ERR_MAX and k == 0):
            pDialog.close()
            dialog = xbmcgui.Dialog()
            ok = dialog.ok(__addonname__, '无法播放：多次未匹配到视频文件，请选择其它视频')
            break

        if x < v_pos:
            continue
        p_item = playlistA.__getitem__(x)
        p_url = p_item.getfilename(x)
        p_list = p_item.getdescription(x)

        li = p_item   # pass all li items including the embedded thumb image
        li.setInfo(type="Video", infoLabels={"Title": p_list})

        if not re.search('http://', p_url):  # fresh search
            if type == 'video':
                url = 'http://api.funshion.com/ajax/get_media_data/ugc/%s' % (p_url)
            else:
                url = 'http://api.funshion.com/ajax/get_media_data/video/%s' % (p_url)

            if (pDialog.iscanceled()):
                pDialog.close()
                x = psize     # quickily terminate any old thread
                err_cnt = 0
                return
            pDialog.update(errcnt*100/ERR_MAX + 100/ERR_MAX/TRIAL*1)

            link = getHttpData(url)
            try:
                json_response = simplejson.loads(link)
                hashid = json_response['data']['hashid'].encode('utf-8')
                filename = json_response['data']['filename'].encode('utf-8')
            except:
                errcnt += 1   # increment consequetive unsuccessful access
                continue
            url = 'http://jobsfe.funshion.com/query/v1/mp4/%s.json?file=%s' % (hashid, filename)

            link = getHttpData(url)
            try:   # prevent system occassion throw error
                json_response = simplejson.loads(link)
                status = json_response['return'].encode('utf-8')
            except:
                errcnt += 1   # increment consequetive unsuccessful access
                continue
            if status == 'succ':
                v_url = json_response['playlist'][0]['urls'][0]
                playlistA.remove(p_url)   # remove old url
                playlistA.add(v_url, li, x)  # keep a copy of v_url in Audio Playlist
            else:
                errcnt += 1   # increment consequetive unsuccessful access
                continue
        else:
            v_url = p_url

        err_cnt = 0    # reset error count
        ip = re.compile('http://(\d+\.\d+\.\d+\.\d+)').findall(v_url)
        if ip[0] not in usableIP:    # replace a usable IP
            i_url = randrange(len(usableIP))
            v_url = re.sub('http://(\d+\.\d+\.\d+\.\d+)',
                           'http://%s'%(usableIP[i_url]), v_url)
        playlist.add(v_url, li, k)
        k += 1
        if k == 1:
            pDialog.close()
            xbmc.Player(1).play(playlist)
        if videoplaycont == 'false':
            break

#  main program goes here #
pluginhandle = int(sys.argv[1])
params = sys.argv[2][1:]
params = dict(urllib2.urlparse.parse_qsl(params))

name = params.get('name')
type = params.get('type', '')
id2 = params.get('id2', '1')
filtrs = params.get('filtrs', '')
page = params.get('page')
id = params.get('id')
thumb = params.get('thumb')
listpage = params.get('listpage')
cat = params.get('cat', '')

mode = params.get('mode')
if mode is None:
    rootList()
elif mode == '1':
    progList(name, type, cat, filtrs, page, listpage)
elif mode == '2':
    seriesList(name, id, thumb)
elif mode == '3':
    PlayVideo_test(name, id, thumb)
    # PlayVideo(name, id, thumb, id2)
elif mode == '4':
    PlayVideo2(name, id, thumb, type)
elif mode == '10':
    updateListSEL(name, type, cat, filtrs, page, listpage)