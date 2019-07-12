# uestc_calendar_bot

## Description

提供uestc教务系统课程表的查询功能，并能制定闹钟，定时提醒使用者

## Plan

本来我准备在google functions里面写一个bot，并与google firestore联动，实现无服务器的tg bot

但由于uestc的网页添加了js代码加密，所以用requests不能爬到原来的页面

经尝试，用requests-html的render方法可以很好地渲染

但是用到了多线程，所以是不能放到google function里面了



> 现在准备写两个bot，一个用于推送上课信息，一个用于爬取信息

推送信息需要用到 google functions 和 google cloud scheduler进行定时唤醒

爬取信息使用自己的服务器，与用户交互，爬到课程表之后保存到google cloud firestore里面去

由于有服务器，所以也不必像以前那样把用户的状态全部保存到firestore中，直接把用户状态保存到内存即可，拿一个字典来存储

## function

1.  登录uestc
2.  获取课程表
3.  把课程表保存到google firestore
4.  telegram bot与用户的交互（直接用内存保存）
5. 定时提醒用户
