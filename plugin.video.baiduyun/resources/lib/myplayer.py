#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import xbmc


class Player(xbmc.Player):

    def play(self, item='', listitem=None, windowed=False, sublist=None):
        self._sublist = sublist

        super(Player, self).play(item, listitem, windowed)

        self._start_time = time.time()
        while True:
            # print self._start_time, time.time()
            if self._stopped or time.time() - self._start_time > 300:
                if self._totalTime == 999999:
                    raise PlaybackFailed(
                        'XBMC silently failed to start playback')
                break

            xbmc.sleep(500)
        # print 'play end'

    def __init__(self):
        self._stopped = False
        self._totalTime = 999999

        xbmc.Player.__init__(self, xbmc.PLAYER_CORE_AUTO)

    def onPlayBackStarted(self):
        self._totalTime = self.getTotalTime()
        self._start_time = time.time()

        sublist = self._sublist
        if sublist:
            if isinstance(sublist, basestring):
                sublist = [sublist]

            for surl in sublist:
                # print '$'*50, surl
                self.setSubtitles(surl)
            self.setSubtitleStream(0)
            # self.showSubtitles(False)

    def onPlayBackStopped(self):
        self._stopped = True

    def onPlayBackEnded(self):
        self.onPlayBackStopped()


class PlaybackFailed(Exception):

    '''Raised to indicate that xbmc silently failed to play the stream'''
