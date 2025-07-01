#!/usr/bin/python3
# -- coding: utf-8 --
# -------------------------------
# @Author : 优化版富贵论坛签到脚本
# @Time : 2025/7/1
# -------------------------------
# cron "1 0 * * *" script-path=xxx.py,tag=匹配cron用
# const $ = new Env('富贵论坛签到');

import requests
import re
import time
import json
import os
import notify
import random
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup

class FGLTForumSignIn:
    def __init__(self, cookies):
        self.cookies = cookies
        self.base_url = 'https://www.fglt.net/'
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'TE': 'trailers'
        }
        self.signin_count_file = 'signin_count.json'
        self.load_signin_count()
    
    def load_signin_count(self):
        """加载签到统计信息"""
        try:
            if os.path.exists(self.signin_count_file):
                with open(self.signin_count_file, 'r') as f:
                    data = json.load(f)
                    self.signin_count = data.get('count', 0)
                    self.last_signin_date = data.get('last_date', '')
            else:
                self.signin_count = 0
                self.last_signin_date = ''
        except Exception as e:
            print(f"加载签到统计失败: {e}")
            self.signin_count = 0
            self.last_signin_date = ''
    
    def save_signin_count(self):
        """保存签到统计信息"""
        try:
            data = {
                'count': self.signin_count,
                'last_date': self.last_signin_date,
            }
            with open(self.signin_count_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"保存签到统计失败: {e}")
    
    def check_need_signin(self):
        """检查今天是否需要签到"""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.last_signin_date != today
    
    def get_formhash(self, session):
        """获取签到所需的formhash参数"""
        time.sleep(random.uniform(2, 5))
        
        try:
            pages = [
                self.base_url,
                f"{self.base_url}forum.php",
                f"{self.base_url}home.php",
                f"{self.base_url}plugin.php?id=dsu_amupper",
                f"{self.base_url}home.php?mod=spacecp"
            ]
            
            for page in pages:
                print(f"尝试从 {page} 获取formhash")
                time.sleep(random.uniform(1, 3))
                
                response = session.get(page)
                response.raise_for_status()
                
                # 增强安全验证检测
                verification_keywords = [
                    "安全验证", "验证码", "verification", "captcha", "security", 
                    "需要登录", "请登录", "风控", "验证", "human verification"
                ]
                if any(keyword in response.text for keyword in verification_keywords):
                    print("检测到安全验证页面，无法继续签到")
                    # 保存页面内容用于调试
                    with open(f"security_verification_{int(time.time())}.html", "w", encoding="utf-8") as f:
                        f.write(response.text)
                    print(f"安全验证页面已保存至security_verification_*.html")
                    return None
                
                # 混合使用BeautifulSoup和正则表达式提取formhash
                try:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # 通过标签属性提取
                    input_tags = soup.find_all('input', {'name': 'formhash'})
                    if input_tags:
                        formhash = input_tags[0].get('value')
                        if formhash:
                            print(f"通过BeautifulSoup从 {page} 获取到formhash: {formhash[:4]}...")
                            return formhash
                    
                    # 通过JavaScript变量提取
                    script_tags = soup.find_all('script')
                    for script in script_tags:
                        script_text = script.get_text()
                        match = re.search(r'var\s+formhash\s*=\s*["\'](.*?)["\']', script_text)
                        if match:
                            formhash = match.group(1)
                            print(f"从JavaScript变量获取到formhash: {formhash[:4]}...")
                            return formhash
                except Exception as e:
                    print(f"BeautifulSoup解析异常: {e}")
                
                # 扩展正则表达式匹配模式
                patterns = [
                    r'<input\s+type="hidden"\s+name="formhash"\s+value="(.*?)"\s*/>',
                    r'formhash=([a-f0-9]{8,32})',
                    r'"formhash"\s*:\s*["\']([a-f0-9]{8,32})["\']',
                    r'&formhash=([a-f0-9]{8,32})',
                    r'formhash=(\w+)',
                    r'<input\s+id="formhash"\s+value="(.*?)"',
                    r'formhash:\s*["\'](.*?)["\']',
                    r'_formhash\s*=\s*["\'](.*?)["\']'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        formhash = match.group(1)
                        print(f"成功从 {page} 使用模式 {pattern} 获取到formhash: {formhash[:4]}...")
                        return formhash
            
            # 保存未获取到formhash的页面内容
            with open(f"no_formhash_{int(time.time())}.html", "w", encoding="utf-8") as f:
                f.write(response.text[:5000])  # 保存前5000字符
            print(f"未能获取formhash，页面内容已保存至no_formhash_*.html")
            return None
        except requests.RequestException as e:
            print(f"获取formhash请求失败: {e}")
            # 记录网络请求异常详情
            if hasattr(e, 'response') and e.response:
                print(f"响应状态码: {e.response.status_code}")
                if e.response.status_code == 429:
                    print("检测到请求频率限制(429)，请降低请求频率")
            return None
        except Exception as e:
            print(f"获取formhash过程中发生未知异常: {e}")
            return None
    
    def sign_in(self, cookie):
        """执行单个账号的签到操作"""
        session = requests.Session()
        session.headers.update(self.get_random_headers())
        session.cookies.update(self.parse_cookie(cookie))
        
        # 检查是否需要签到
        today = datetime.now().strftime('%Y-%m-%d')
        need_signin = self.check_need_signin()
        
        # 获取formhash
        formhash = self.get_formhash(session)
        if not formhash:
            # 记录详细的formhash获取失败信息
            fail_reason = "获取formhash失败，可能原因：Cookie失效/安全验证/网站结构变更"
            print(fail_reason)
            return fail_reason
        
        print(f'获取到formhash: {formhash[:4]}...')
        
        # 执行签到
        sign_url = f"{self.base_url}plugin.php?id=dsu_amupper&ppersubmit=true&formhash={formhash}&infloat=yes&handlekey=dsu_amupper&inajax=1&ajaxtarget=fwin_content_dsu_amupper"
        
        try:
            # 增加请求头随机性
            session.headers.update({
                'X-Requested-With': random.choice(['XMLHttpRequest', ''])
            })
            response = session.post(sign_url, timeout=15)
            response.raise_for_status()
            
            # 解析签到结果
            result = None
            response_text = response.text
            
            # 优先解析XML响应（可能来自某些框架）
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response_text)
                cdata_content = root.text
                if cdata_content:
                    result = self._parse_result(cdata_content)
            except:
                result = self._parse_result(response_text)
            
            if result:
                if "成功" in result or "已签到" in result:
                    if need_signin and self.check_need_signin():
                        self.signin_count += 1
                        self.last_signin_date = today
                        self.save_signin_count()
                        return f"签到成功，今日第{self.signin_count}次签到"
                    else:
                        return f"{result}，今日已签到{self.signin_count}次"
                else:
                    # 记录详细的失败原因
                    return f"签到失败: {result}"
            else:
                # 处理未知响应格式
                return "签到失败: 无法解析响应内容"
        except requests.HTTPError as e:
            # 处理HTTP错误状态码
            status_code = e.response.status_code
            error_msg = f"签到请求失败(HTTP {status_code}): {e.response.reason}"
            if status_code == 403:
                error_msg += "，可能原因：权限不足或账号被封禁"
            elif status_code == 500:
                error_msg += "，服务器内部错误，请稍后重试"
            print(error_msg)
            return error_msg
        except requests.Timeout:
            # 处理请求超时
            print("签到请求超时，请检查网络连接或服务器状态")
            return "签到失败: 请求超时"
        except requests.ConnectionError:
            # 处理连接错误
            print("签到请求连接错误，请检查网络连接")
            return "签到失败: 连接错误"
        except Exception as e:
            # 处理其他异常
            print(f"签到过程中发生未知异常: {e}")
            return f"签到失败: 未知异常 - {str(e)}"
    
    def _parse_result(self, text):
        """解析签到结果文本"""
        patterns = [
            r'showDialog\("(.*?)",',
            r'"message"\s*:\s*["\'](.*?)["\']',
            r'<div\s+class="alert_info">\s*(.*?)\s*</div>',
            r'<div\s+class="alert_success">\s*(.*?)\s*</div>',
            r'签到成功',
            r'已签到',
            r'您今日已经签到',
            r'恭喜你签到成功',
            r'签到排名第(\d+)名',
            r'错误：(.*)',
            r'失败：(.*)',
            r'提示：(.*)',
            r'系统提示：(.*)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1) if len(match.groups()) > 0 else pattern
        return None
    
    def get_random_headers(self):
        """获取随机请求头，增强反爬能力"""
        headers = self.headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        # 增加随机请求头参数
        headers['Accept-Encoding'] = random.choice(['gzip, deflate', 'gzip, deflate, br', 'identity'])
        headers['DNT'] = str(random.randint(0, 1))
        return headers
    
    def parse_cookie(self, cookie_str):
        """将cookie字符串解析为字典格式，增强错误处理"""
        try:
            if not cookie_str:
                return {}
            return dict(item.split('=', 1) for item in cookie_str.split('; ') if '=' in item)
        except (ValueError, AttributeError) as e:
            print(f"解析cookie失败: {cookie_str}, 错误: {e}")
            return {}
    
    def run(self):
        """执行所有账号的签到操作，增强失败信息发送"""
        success_results = []
        failed_results = []
        
        for i, cookie in enumerate(self.cookies, 1):
            print(f"\n***开始第{i}个账号签到***")
            try:
                cookie_hash = hashlib.md5(cookie.encode('utf-8')).hexdigest()[:8]
                print(f"处理账号 (哈希): {cookie_hash}")
                
                result = self.sign_in(cookie)
                print(result)
                
                if "签到成功" in result or "已签到" in result:
                    success_results.append(f"账号{i}: {result}")
                else:
                    failed_results.append(f"账号{i}: {result}")
                
                delay = random.uniform(8, 15)
                print(f"等待{delay:.2f}秒后处理下一个账号")
                time.sleep(delay)
            except Exception as e:
                # 捕获账号处理过程中的全局异常
                error_msg = f"账号{i}处理过程中发生未预期异常: {str(e)}"
                print(error_msg)
                failed_results.append(f"账号{i}: {error_msg}")
                time.sleep(random.uniform(5, 10))
        
        # 发送成功和失败通知
        notification_content = ""
        if success_results:
            success_summary = "\n".join([f"✅ {res}" for res in success_results])
            notification_content += f"【签到成功】\n{success_summary}\n\n"
        
        if failed_results:
            failed_summary = "\n".join([f"❌ {res}" for res in failed_results])
            notification_content += f"【签到失败】\n{failed_summary}"
        
        if notification_content:
            try:
                notify.send("富贵论坛签到结果通知", notification_content)
                print("\n通知已发送，内容如下:")
                print(notification_content)
            except Exception as e:
                print(f"发送通知失败: {e}")
                print("通知内容:")
                print(notification_content)
        
        # 打印统计信息
        if not failed_results:
            print("\n所有账号签到成功")
        else:
            print(f"\n签到统计: {len(success_results)}/{len(self.cookies)}个账号成功，{len(failed_results)}个账号失败")
        
        return success_results, failed_results

if __name__ == "__main__":
    fg_cookies = os.getenv("fg_cookies", "").split('&')
    
    if not fg_cookies or fg_cookies[0] == "":
        print("未配置cookie，退出程序")
        # 发送配置错误通知
        try:
            notify.send("富贵论坛签到错误", "未配置cookie，签到程序退出")
        except:
            pass
    else:
        print(f"共配置了{len(fg_cookies)}个账号")
        
        start_delay = random.uniform(15, 45)
        print(f"随机延迟{start_delay:.2f}秒后开始")
        time.sleep(start_delay)
        
        sign_bot = FGLTForumSignIn(fg_cookies)
        success, failed = sign_bot.run()
