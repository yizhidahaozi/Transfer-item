# -*- coding: utf-8 -*-
import requests
import os
import re
import datetime
# const $ = new Env('签到zhh.tl55.cn')
#  配置信息（从环境变量添加Cookie，名称 SIGN_COOKIE ）

# 多渠道通知功能模块（从夸克脚本提取并适配）
# 通知配置（从环境变量获取）
PUSH_PLUS_TOKEN = os.getenv("PUSH_PLUS_TOKEN")  # PushPlus推送Token
BARK_KEY = os.getenv("BARK_KEY")                # Bark推送Key
SCKEY = os.getenv("SCKEY")                      # Server酱SCKEY
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")        # Telegram Bot Token
TG_CHAT_ID = os.getenv("TG_CHAT_ID")            # Telegram Chat ID

def send_pushplus(title, content):
    """使用PushPlus推送消息"""
    if not PUSH_PLUS_TOKEN:
        return "PushPlus Token未配置，推送失败"
    try:
        headers = {'Content-Type': 'application/json'}
        json_data = {
            "token": PUSH_PLUS_TOKEN,
            "title": title,
            "content": content.replace('\n', '<br>'),
            "template": "json"
        }
        resp = requests.post('http://www.pushplus.plus/send', json=json_data, headers=headers).json()
        return "PushPlus推送成功" if resp['code'] == 200 else f"PushPlus推送失败: {resp.get('msg', '未知错误')}"
    except Exception as e:
        return f"PushPlus推送异常: {str(e)}"

def send_bark(title, content):
    """使用Bark推送消息"""
    if not BARK_KEY:
        return "Bark Key未配置，推送失败"
    try:
        content = content.replace('\n', ' ')  # Bark不支持换行
        url = f"https://api.day.app/{BARK_KEY}/{title}/{content}"
        resp = requests.get(url).json()
        return "Bark推送成功" if resp.get('code') == 200 else f"Bark推送失败: {resp.get('message', '未知错误')}"
    except Exception as e:
        return f"Bark推送异常: {str(e)}"

def send_server_chan(title, content):
    """使用Server酱推送消息"""
    if not SCKEY:
        return "Server酱SCKEY未配置，推送失败"
    try:
        url = f"https://sctapi.ftqq.com/{SCKEY}.send"
        data = {
            "title": title,
            "desp": content
        }
        resp = requests.post(url, data=data).json()
        return "Server酱推送成功" if resp.get('code') == 0 else f"Server酱推送失败: {resp.get('message', '未知错误')}"
    except Exception as e:
        return f"Server酱推送异常: {str(e)}"

def send_telegram(title, content):
    """使用Telegram Bot推送消息"""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return "Telegram Bot配置未设置，推送失败"
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TG_CHAT_ID,
            "text": f"{title}\n\n{content}",
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, data=data).json()
        return "Telegram推送成功" if resp.get('ok') else f"Telegram推送失败: {resp.get('description', '未知错误')}"
    except Exception as e:
        return f"Telegram推送异常: {str(e)}"

def notify(title, content):
    """统一通知函数，支持多种通知方式"""
    results = []
    
    # 按优先级推送
    if PUSH_PLUS_TOKEN:
        results.append(send_pushplus(title, content))
    if BARK_KEY:
        results.append(send_bark(title, content))
    if SCKEY:
        results.append(send_server_chan(title, content))
    if TG_BOT_TOKEN and TG_CHAT_ID:
        results.append(send_telegram(title, content))
    
    # 无通知配置时提示
    if not any([PUSH_PLUS_TOKEN, BARK_KEY, SCKEY, TG_BOT_TOKEN]):
        results.append("未配置任何通知方式，跳过推送")
    
    return results


# 核心签到逻辑
def main():
    # 配置信息（仅从环境变量获取Cookie，无默认值）
    cookie = os.getenv("SIGN_COOKIE")
    if not cookie:
        print("❌ 错误：未设置SIGN_COOKIE环境变量，请配置后再运行")
        return
    
    sign_url = "https://zhh.tl55.cn/user/qiandao.php"
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 格式化时间
    
    # 执行签到
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Cookie": cookie,
            "Referer": sign_url,
            "Host": "zhh.tl55.cn"
        }
        response = requests.get(sign_url, headers=headers, timeout=15)
        response.encoding = "utf-8"
        page_content = response.text
        
        # 生成签到结果信息
        if "已签到" in page_content:
            info = f"✅ 签到成功：今日已完成签到"
        elif "连续签到" in page_content:
            start = page_content.find("连续签到") + 4
            end = page_content.find("天", start)
            days = page_content[start:end] if start < end else "N"
            info = f"✅ 签到成功：已连续签到{days}天"
        elif "签到成功" in page_content:
            info = f"✅ 签到成功：页面返回成功标识"
        elif "请登录" in page_content:
            info = f"❌ 签到失败：Cookie已过期，请重新获取"
        else:
            info = f"ℹ️ 签到结果：页面访问成功，请手动确认"
    
    except requests.exceptions.Timeout:
        info = "❌ 签到失败：请求超时，请检查网络"
    except requests.exceptions.ConnectionError:
        info = "❌ 签到失败：连接错误，可能是网站无法访问"
    except Exception as e:
        info = f"❌ 签到出错：{str(e)}"
    
    # 整合完整通知内容
    full_content = f"""
{info}
----------
运行时间：{today}
目标网站：zhh.tl55.cn
    """.strip()
    
    # 输出结果并发送通知
    print(full_content)
    print("\n发送通知...")
    notify_results = notify(title="自动签到通知-zhh.tl55", content=full_content)
    for res in notify_results:
        print(f"- {res}")


if __name__ == "__main__":
    main()
