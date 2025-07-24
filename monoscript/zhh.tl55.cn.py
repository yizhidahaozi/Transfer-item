import requests
import os
import datetime

# 从环境变量获取关键配置
COOKIE = os.getenv("SIGN_COOKIE")  # 需配置用户 Cookie，格式同浏览器抓包
NOTIFY_TYPE = os.getenv("NOTIFY_TYPE", "pushplus")  # 通知方式，可选 pushplus/bark/serverchan/telegram，默认 pushplus
# 各通知方式的密钥，按需配置环境变量
PUSH_PLUS_TOKEN = os.getenv("PUSH_PLUS_TOKEN")
BARK_KEY = os.getenv("BARK_KEY")
SCKEY = os.getenv("SCKEY")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# 签到相关固定配置
BASE_URL = "https://zhh.tl55.cn"
SIGN_PAGE_URL = f"{BASE_URL}/user/qiandao.php"
SIGN_API_URL = f"{BASE_URL}/user/ajax_user.php?act=qiandao"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"

def send_notify(title, content, notify_type):
    """
    统一通知函数，支持多种通知渠道
    :param title: 通知标题
    :param content: 通知内容
    :param notify_type: 通知类型，可选 pushplus/bark/serverchan/telegram
    :return: 通知结果
    """
    if notify_type == "pushplus" and PUSH_PLUS_TOKEN:
        url = "http://www.pushplus.plus/send"
        data = {
            "token": PUSH_PLUS_TOKEN,
            "title": title,
            "content": content,
            "template": "json"
        }
        return requests.post(url, json=data).json().get("msg", "推送失败")
    elif notify_type == "bark" and BARK_KEY:
        url = f"https://api.day.app/{BARK_KEY}/{title}/{content}"
        return requests.get(url).json().get("message", "推送失败")
    elif notify_type == "serverchan" and SCKEY:
        url = f"https://sctapi.ftqq.com/{SCKEY}.send"
        data = {"title": title, "desp": content}
        return requests.post(url, data=data).json().get("message", "推送失败")
    elif notify_type == "telegram" and TG_BOT_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TG_CHAT_ID,
            "text": f"{title}\n{content}",
            "parse_mode": "HTML"
        }
        return requests.post(url, data=data).json().get("description", "推送失败")
    return "未配置有效通知方式"

def main():
    """主执行函数"""
    session = requests.Session()
    # 设置请求头，模拟真实浏览器
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Referer": SIGN_PAGE_URL,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9"
    })
    # 设置Cookie
    if COOKIE:
        cookie_dict = {}
        for cookie in COOKIE.split(";"):
            cookie = cookie.strip()
            if "=" in cookie:
                key, value = cookie.split("=", 1)
                cookie_dict[key] = value
        session.cookies.update(cookie_dict)
    else:
        print("未配置Cookie，无法执行签到")
        return

    try:
        # 先访问签到页面，获取必要的会话信息（若有）
        session.get(SIGN_PAGE_URL, timeout=10)
        # 执行签到请求
        response = session.get(SIGN_API_URL, timeout=10)
        response.encoding = "utf-8"
        result = response.json()

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = "自动签到结果通知"
        if result.get("code") == 0:
            content = f"""✅ 签到成功
时间：{now}
提示：{result.get("msg")}
"""
        elif result.get("code") == -1:
            content = f"""✅ 今日已签到
时间：{now}
提示：{result.get("msg")}
"""
        else:
            content = f"""❌ 签到失败
时间：{now}
错误：{result.get("msg", "未知错误")}
"""
        print(content)
        # 发送通知
        notify_result = send_notify(title, content, NOTIFY_TYPE)
        print(f"通知结果：{notify_result}")
    except requests.RequestException as e:
        content = f"""❌ 签到请求异常
时间：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
错误：{str(e)}
"""
        print(content)
        send_notify("签到请求异常", content, NOTIFY_TYPE)

if __name__ == "__main__":
    main()
