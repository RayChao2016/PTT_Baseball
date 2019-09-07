# -*- coding: utf-8 -*-

#PTT爬文
import requests
import re
import os
import json
import time
import datetime
from datetime import date, timedelta
from django.db.models import Q
from app.models import Gossippost, Baseballpost, Sexpost
from celery import shared_task, task
import random
from django.conf import settings
from PTTLibrary import PTT


@task(name='daily_baseball')
def daily_baseball():
    day_list = [5, 6]
    day_n = datetime.datetime.now().weekday()
    hour_n = datetime.datetime.now().hour
    if hour_n < 12:
        ps_1 = '17'
        ps_2 = 20
    else:
        if day_n in day_list:
            ps_1 = '17'
            ps_2 = 20
        else:
            ps_1 = '22'
            ps_2 = 28

    no_list=[0, 1]
    srr = random.SystemRandom()
    no_order = srr.choice(no_list)
    file_ = open(os.path.join(settings.BASE_DIR, 'app/acc.py'))
    #with open(file_) as f:
    data = json.load(file_)
    ID = data['acc'][no_order]['ID']
    Password = data['acc'][no_order]['Password']

    PTTBot = PTT.Library(
        ConnectMode = PTT.ConnectMode.WebSocket,
        #LogLevel = PTT.LogLevel.TRACE,
    )

    for x in range(5): 
        try:
            PTTBot.login(ID, Password)
            print('Login successfully')
        except PTT.Exceptions.LoginError:
            print('Login failed ' + str(x) + 'times' )
            time.sleep(1)
            continue
        break  


    #Baseball
    def CrawlBoard_baseball(): 
        
        board = 'Baseball'
        TestRange = 30
        fstrlist = ['[Live]', '[LIVE]', '[公告]', '[先發]', '[祭品]']  #Forbidden str
            
        def crawlHandler(Post):

            if Post.getDeleteStatus() != PTT.PostDeleteStatus.NotDeleted:
                pass
            else:
                if not Post.getTitle() or not Post.getAID() or not Post.getAuthor() or not Post.getDate() or not Post.getWebUrl() or re.findall(r'[\u4e00-\u9fff]+', Post.getAID()) or any(x in Post.getTitle() for x in fstrlist) or len(Post.getAID())< 7:
                    pass
                else:
                    PushCount = 0
                    BooCount = 0
                    ArrowCount = 0
                    for Push in Post.getPushList():

                        if Push.getType() == PTT.PushType.Push:
                            PushCount += 1
                        if Push.getType() == PTT.PushType.Boo:
                            BooCount += 1
                        if Push.getType() == PTT.PushType.Arrow:
                            ArrowCount += 1
                    if PushCount > ps_2 and BooCount < 30:
                        if Baseballpost.objects.filter(aid=Post.getAID()).exists():
                            baspost=Baseballpost.objects.get(aid=Post.getAID())       
                            baspost.push_count = PushCount
                            baspost.boo_count = BooCount
                            baspost.arrow_count = ArrowCount
                            baspost.title = Post.getTitle()
                            baspost.parse_update_time = datetime.datetime.now()
                            baspost.save(update_fields=['push_count', 'boo_count', 'arrow_count', 'title', 'parse_update_time'])
                            print('Baseball, '+ Post.getAID() +' - updated')
                            time.sleep(0.5)
                        else:
                            a_time=datetime.datetime.strptime(Post.getDate()[4:], '%b %d %H:%M:%S %Y')
                            baspost = Baseballpost(
                                arthur = Post.getAuthor()[:Post.getAuthor().find(" ")],
                                aid = Post.getAID(),
                                title = Post.getTitle(),
                                weburl = Post.getWebUrl(),
                                push_count =  PushCount,
                                boo_count =  BooCount,
                                arrow_count =  ArrowCount,
                                article_time = datetime.datetime.strptime(Post.getDate()[4:], '%b %d %H:%M:%S %Y'),
                                article_date = a_time.date()
                            )
                            baspost.save()
                            print('Baseball, '+ Post.getAID() +' - saved')
                            time.sleep(0.5)
                    else:
                        pass

        time.sleep(0.5)
        NewestIndex = PTTBot.getNewestIndex(
            PTT.IndexType.Board,
            Board=board,
            SearchType=PTT.PostSearchType.Push, 
            SearchCondition=ps_1,
        )

        StartIndex = NewestIndex - TestRange + 1

        #print(f'預備爬行 {board} 編號 {StartIndex} ~ {NewestIndex} 文章')
        time.sleep(0.5)
        PTTBot.crawlBoard(
            crawlHandler,
            board,
            StartIndex=StartIndex,
            EndIndex=NewestIndex,
            SearchType=PTT.PostSearchType.Push, 
            SearchCondition=ps_1,
        )
        PTTBot.logout()
    CrawlBoard_baseball()
