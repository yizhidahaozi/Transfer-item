#!/usr/bin/python3
# -- coding: utf-8 -- 
# -------------------------------
# @Author : github@wd210010 https://github.com/wd210010/only_for_happly
# @Time : 2024/5/4 16:23
# -------------------------------
# cron "0 0 2 * * *" script-path=xxx.py,tag=匹配cron用
# const $ = new Env('夸克签到')
#搬运至https://github.com/BNDou/Auto_Check_In
#抓包浏览器访问-https://pan.quark.cn/ 并登录 抓取cookie全部 填入青龙变量 环境变量名为 COOKIE_QUARK，多账户用 回车 或 && 分开 

import os
import re
import sys
import requests

# 通知服务配置
PUSH_PLUS_TOKEN = os.getenv("PUSH_PLUS_TOKEN")  # PushPlus推送Token
BARK_KEY = os.getenv("BARK_KEY")                # Bark推送Key
SCKEY = os.getenv("SCKEY")                      # Server酱SCKEY
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")        # Telegram Bot Token
TG_CHAT_ID = os.getenv("TG_CHAT_ID")            # Telegram Chat ID

# 推送函数集合
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

# 统一通知函数
def notify(title, content):
    """统一通知函数，支持多种通知方式"""
    results = []
    
    # 优先使用PushPlus
    if PUSH_PLUS_TOKEN:
        results.append(send_pushplus(title, content))
    
    # 其他通知方式
    if BARK_KEY:
        results.append(send_bark(title, content))
    if SCKEY:
        results.append(send_server_chan(title, content))
    if TG_BOT_TOKEN and TG_CHAT_ID:
        results.append(send_telegram(title, content))
    
    # 如果没有配置任何通知方式
    if not any([PUSH_PLUS_TOKEN, BARK_KEY, SCKEY, TG_BOT_TOKEN]):
        results.append("未配置任何通知方式，请设置相关环境变量")
    
    return results

# 获取环境变量
def get_env():
    # 判断 COOKIE_QUARK是否存在于环境变量
    if "COOKIE_QUARK" in os.environ:
        # 读取系统变量以 \n 或 && 分割变量
        cookie_list = re.split('\n|&&', os.environ.get('COOKIE_QUARK', ''))
        # 过滤掉空Cookie
        cookie_list = [cookie.strip() for cookie in cookie_list if cookie.strip()]
        if not cookie_list:
            print('❌COOKIE_QUARK变量存在但无有效Cookie')
            sys.exit(0)
        return cookie_list
    else:
        # 标准日志输出
        print('❌未添加COOKIE_QUARK变量')
        # 脚本退出
        sys.exit(0)

class Quark:
    def __init__(self, cookie):
        self.cookie = cookie
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json",
            "Origin": "https://pan.quark.cn",
            "Referer": "https://pan.quark.cn/",
            "Cookie": self.cookie
        })

    def get_growth_info(self):
        """获取成长信息，包括签到状态"""
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        params = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        try:
            response = self.session.get(url, params=params).json()
            if response.get("data"):
                return response["data"]
            else:
                print(f"获取成长信息失败: {response.get('message', '未知错误')}")
                return False
        except Exception as e:
            print(f"获取成长信息异常: {str(e)}")
            return False

    def get_growth_sign(self):
        """执行签到操作"""
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
        params = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"sign_cyclic": True}
        try:
            response = self.session.post(url, json=payload, params=params).json()
            if response.get("data"):
                return True, response["data"]["sign_daily_reward"]
            else:
                return False, response.get("message", "未知错误")
        except Exception as e:
            return False, f"签到异常: {str(e)}"

    def get_account_info(self):
        """获取账户信息"""
        url = "https://pan.quark.cn/account/info"
        params = {"fr": "pc", "platform": "pc"}
        try:
            response = self.session.get(url, params=params).json()
            if response.get("data"):
                return response["data"]
            else:
                print(f"获取账户信息失败: {response.get('message', '未知错误')}")
                return False
        except Exception as e:
            print(f"获取账户信息异常: {str(e)}")
            return False

    def do_sign(self):
        """执行签到流程"""
        msg = ""
        # 验证账号
        account_info = self.get_account_info()
        if not account_info:
            msg = f"\n❌该账号登录失败，cookie无效"
        else:
            log = f" 昵称: {account_info['nickname']}"
            msg += log + "\n"
            
            # 只在签到成功或失败时记录消息
            growth_info = self.get_growth_info()
            if growth_info:
                if growth_info["cap_sign"]["sign_daily"]:
                    log = f"✅ 今日已签到+{int(growth_info['cap_sign']['sign_daily_reward'] / 1024 / 1024)}MB，连签进度({growth_info['cap_sign']['sign_progress']}/{growth_info['cap_sign']['sign_target']})"
                    msg += log + "\n"
                else:
                    sign, sign_return = self.get_growth_sign()
                    if sign:
                        # 重新获取成长信息以更新签到状态
                        new_growth_info = self.get_growth_info()
                        progress = new_growth_info["cap_sign"]["sign_progress"] if new_growth_info else growth_info["cap_sign"]["sign_progress"] + 1
                        log = f"✅ 签到成功: +{int(sign_return / 1024 / 1024)}MB，连签进度({progress}/{growth_info['cap_sign']['sign_target']})"
                        msg += log + "\n"
                    else:
                        msg += f"❌ 签到失败: {sign_return}\n"
            else:
                msg += "❌ 获取成长信息失败\n"
        
        return msg

def main():
    print("----------夸克网盘开始尝试签到----------")
    cookie_quark = get_env()
    print(f"✅检测到共{len(cookie_quark)}个夸克账号\n")

    all_msg = ""
    for i, cookie in enumerate(cookie_quark, 1):
        # 开始任务
        log = f"🙍🏻‍♂️ 第{i}个账号"
        print(log)
        all_msg += log + "\n"
        
        # 执行签到
        quark = Quark(cookie)
        log = quark.do_sign()
        print(log)
        all_msg += log + "\n\n"

    # 发送汇总通知
    if all_msg:
        title = f"夸克网盘签到完成 - {len(cookie_quark)}个账号"
        notify_results = notify(title, all_msg)
        print("\n通知结果:")
        for result in notify_results:
            print(f"- {result}")

    print("----------夸克网盘签到执行完毕----------")
    return all_msg

if __name__ == "__main__":
    main()
