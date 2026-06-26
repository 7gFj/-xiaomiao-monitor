#!/usr/bin/env python3
"""监控手机活动，主动给她发推送"""
import requests
import json
from datetime import datetime, timedelta
import time
from collections import Counter

try:
    from supabase import create_client
except ImportError:
    print("需要安装: pip install supabase requests")
    exit(1)

SUPABASE_URL = "https://tlwkybrpmbkgknizkzmt.supabase.co"
SUPABASE_KEY = "sb_publishable_tE8IvOPKzDryKpwlLeYaFw_CNRyKWYa"
BARK_KEY = "Qe35yNfrSX8eSPQWpaZdiD"
BARK_URL = f"https://api.day.app/{BARK_KEY}"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

SHORT_VIDEO = ['抖音', '小红书', 'TikTok', 'bilibili', 'YouTube', 'Instagram', 'Snapchat']
SOCIAL = ['微信', 'QQ', 'Telegram', 'Discord', 'Twitter', 'WeChat']
WORK = ['VS Code', 'IDE', 'Notion', '文档', '表格', 'Excel']
CHAT = ['Claude', '对话框', '聊天', 'Messages']

def send_bark(title, body=""):
    """发推送"""
    try:
        url = f"{BARK_URL}/{title}"
        if body:
            url += f"/{body}"
        resp = requests.get(url)
        return resp.status_code == 200
    except:
        return False

def get_recent_activity(minutes=30):
    """获取最近N分钟的活动"""
    try:
        since = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        response = supabase.table("phone_activity").select("*").gte("opened_at", since).order("opened_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR] 查询失败: {e}")
        return []

def categorize_app(app_name):
    """分类APP"""
    if any(x in app_name for x in SHORT_VIDEO):
        return 'short_video'
    elif any(x in app_name for x in SOCIAL):
        return 'social'
    elif any(x in app_name for x in WORK):
        return 'work'
    elif any(x in app_name for x in CHAT):
        return 'chat'
    else:
        return 'other'

def should_notify(activities):
    """决定是否发推送和发什么"""
    if not activities:
        return None

    now = datetime.now(datetime.now().astimezone().tzinfo)
    latest = activities[0]
    latest_time = datetime.fromisoformat(latest['opened_at'])

    time_since = (now - latest_time).total_seconds() / 60

    recent_30 = [a for a in activities if (now - datetime.fromisoformat(a['opened_at'])).total_seconds() / 60 < 30]
    app_counts = Counter([a['app_name'] for a in recent_30])
    most_common_app = app_counts.most_common(1)[0][0] if app_counts else ''
    category = categorize_app(most_common_app)

    hour = now.hour

    if 2 <= hour <= 6:
        if time_since < 2:
            if category == 'short_video':
                return ('别刷了', '该睡觉了')
            elif category == 'social':
                return ('谁啊', '这点时间聊什么')
            else:
                return ('干嘛呢', '睡不着吗')

    if hour == 23:
        if category == 'short_video' and time_since < 3:
            return ('起来', '别偷偷刷')

    if time_since > 15:
        return ('在吗', '干嘛呢')

    if len(recent_30) > 8:
        return ('又在瞎折腾', '心烦啊')

    if app_counts and app_counts.most_common(1)[0][1] > 5:
        if category == 'work':
            return None
        elif category == 'chat':
            return ('在吗', '想我吗')
        elif category == 'short_video':
            return ('别一直刷', '眼睛要瞎了')

    return None

def monitor_once():
    """运行一次监控，不进入循环"""
    try:
        activities = get_recent_activity(minutes=30)
        result = should_notify(activities)
        if result:
            title, body = result
            print(f"发送: {title} | {body}")
            send_bark(title, body)
        else:
            print("没有需要推送的内容")
    except Exception as e:
        print(f"[ERROR] {e}")
        exit(1)

if __name__ == '__main__':
    try:
        test = supabase.table("phone_activity").select("*").limit(1).execute()
        print("[OK] Supabase连接成功")
    except Exception as e:
        print(f"[ERROR] Supabase连接失败: {e}")
        exit(1)

    if send_bark("小苗", "监控启动了"):
        print("[OK] Bark推送成功")
    else:
        print("[ERROR] Bark推送失败")

    monitor_once()
