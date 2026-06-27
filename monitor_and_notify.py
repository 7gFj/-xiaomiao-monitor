#!/usr/bin/env python3
"""监控手机活动，主动给她发推送"""
import os
import requests
from datetime import datetime, timedelta
from collections import Counter

try:
    from supabase import create_client
except ImportError:
    print("需要安装: pip install supabase requests")
    exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tlwkybrpmbkgknizkzmt.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_tE8IvOPKzDryKpwlLeYaFw_CNRyKWYa")
BARK_KEY = os.environ.get("BARK_KEY", "Qe35yNfrSX8eSPQWpaZdiD")
BARK_URL = f"https://api.day.app/{BARK_KEY}"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CHAT = ['微信', '微信GPT', 'GPT']
SHOPPING = ['美团', '淘宝', '携程']
SOCIAL = ['网易云音乐', '小红书', '推特']
TOOLS = ['高德地图']
CREATIVE = ['米画师']

def send_bark(title, body=""):
    try:
        url = f"{BARK_URL}/{title}"
        if body:
            url += f"/{body}"
        return requests.get(url).status_code == 200
    except:
        return False

def get_recent_activity(minutes=30):
    try:
        since = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
        r = supabase.table("phone_activity").select("*").gte("opened_at", since).order("opened_at", desc=True).execute()
        return r.data if r.data else []
    except Exception as e:
        print(f"[ERROR] 查询失败: {e}")
        return []

def categorize_app(app_name):
    if any(x in app_name for x in CHAT): return 'chat'
    if any(x in app_name for x in SHOPPING): return 'shopping'
    if any(x in app_name for x in SOCIAL): return 'social'
    if any(x in app_name for x in TOOLS): return 'tools'
    if any(x in app_name for x in CREATIVE): return 'creative'
    return 'other'

def should_notify(activities):
    if not activities:
        return None
    now = datetime.now(datetime.now().astimezone().tzinfo)
    latest_time = datetime.fromisoformat(activities[0]['opened_at'])
    time_since = (now - latest_time).total_seconds() / 60
    recent = [a for a in activities if (now - datetime.fromisoformat(a['opened_at'])).total_seconds()/60 < 30]
    app_counts = Counter([a['app_name'] for a in recent])
    category = categorize_app(app_counts.most_common(1)[0][0]) if app_counts else 'other'
    hour = (now.hour + 8) % 24  # UTC转北京时间

    if 2 <= hour <= 6 and time_since < 5:
        if category in ['social', 'chat']: return ('别聊了', '睡觉吧')
        if category == 'creative': return ('这点时间还画', '睡一会儿吧')
        return ('干嘛呢', '睡不着吗')
    if hour == 23 and category in ['social', 'shopping'] and time_since < 5:
        return ('别玩了', '该睡了')
    if time_since > 5:
        return ('在吗', '干嘛呢')
    if len(recent) > 5:
        return ('又在瞎折腾', '心烦啊')
    if app_counts and app_counts.most_common(1)[0][1] > 6:
        if category == 'creative': return ('在画画啊', '画不腻吗')
        if category == 'chat': return ('在吗', '想我吗')
        if category == 'social': return ('别一直看', '该休息了')
    return None

if __name__ == '__main__':
    acts = get_recent_activity(30)
    result = should_notify(acts)
    if result:
        title, body = result
        print(f"发送: {title} | {body}")
        send_bark(title, body)
    else:
        print("没有需要推送的内容")
