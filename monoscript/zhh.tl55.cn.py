import requests
import json
import os
import logging
import time

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 从青龙环境变量获取配置
COOKIE = os.environ.get('ZHH_TL55_COOKIE', '')
PUSH_PLUS_TOKEN = os.environ.get('PUSH_PLUS_TOKEN', '')  # PushPlus通知Token
QL_API_TOKEN = os.environ.get('QL_API_TOKEN', '')  # 青龙面板API Token
QL_API_URL = os.environ.get('QL_API_URL', 'http://localhost:5700')  # 青龙面板URL

if not COOKIE:
    logging.error("未获取到有效的 Cookie，请检查青龙环境变量设置")
    exit(1)

BASE_URL = "https://zhh.tl55.cn/user"
SIGN_API = f"{BASE_URL}/ajax_user.php?act=qiandao"
STATS_API = f"{BASE_URL}/ajax_user.php?act=qdcount"

# 完善请求头，增加浏览器标识相关字段
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/qiandao.php",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cookie": COOKIE,
    "sec-ch-ua": "\"Chromium\";v=\"129\", \"Not=A?Brand\";v=\"8\"",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-ua-mobile": "?0",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Origin": "https://zhh.tl55.cn",
    "Connection": "keep-alive"
}

class PushPlusNotifier:
    """PushPlus通知工具类"""
    
    def __init__(self, token: str):
        self.token = token
        
    def send(self, title: str, content: str) -> str:
        """发送通知"""
        if not self.token:
            return "未配置 PushPlus Token，跳过通知"
            
        try:
            response = requests.post(
                url="https://www.pushplus.plus/send",
                json={
                    "token": self.token,
                    "title": title,
                    "content": content,
                    "template": "json"
                },
                timeout=10
            )
            result = response.json()
            
            if result.get("code") == 200:
                return "通知发送成功"
            else:
                return f"通知失败：{result.get('msg', '未知错误')}"
                
        except Exception as e:
            return f"通知异常：{str(e)}"

class QingLongNotifier:
    """青龙面板通知工具类"""
    
    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url
        self.api_token = api_token
        
    def send(self, title: str, content: str) -> str:
        """调用青龙API发送系统通知"""
        if not self.api_token or not self.api_url:
            return "未配置青龙API Token或URL，跳过通知"
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # 青龙系统通知API
            url = f"{self.api_url}/open/system/notify"
            data = {
                "title": title,
                "content": content
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            result = response.json()
            
            if result.get("code") == 200:
                return "青龙通知发送成功"
            else:
                return f"青龙通知失败：{result.get('message', '未知错误')}"
                
        except Exception as e:
            return f"青龙通知异常：{str(e)}"

def sign_in():
    """执行签到操作"""
    try:
        # 添加随机延迟，模拟人工操作
        time.sleep(1 + 2 * random.random())
        
        response = requests.get(SIGN_API, headers=headers)
        response.raise_for_status()
        
        # 记录完整响应内容用于调试
        logging.debug(f"签到原始响应: {response.text}")
        
        result = response.json()
        logging.info(f"签到结果: {result.get('msg', '未知错误')}")
        return result
    except requests.RequestException as e:
        logging.error(f"签到请求失败: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"签到响应解析失败，响应内容: {response.text[:200]}")
        return None

def get_stats():
    """获取签到统计数据"""
    try:
        # 添加随机延迟，模拟人工操作
        time.sleep(1 + 2 * random.random())
        
        response = requests.get(STATS_API, headers=headers)
        response.raise_for_status()
        
        # 记录完整响应内容用于调试
        logging.debug(f"统计原始响应: {response.text}")
        
        result = response.json()
        logging.info(f"统计数据: {json.dumps(result, ensure_ascii=False)}")
        return result
    except requests.RequestException as e:
        logging.error(f"获取统计数据请求失败: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"统计数据响应解析失败，响应内容: {response.text[:200]}")
        return None

def main():
    """主流程"""
    logging.info("开始执行自动签到流程")
    
    # 初始化通知器
    push_plus_notifier = PushPlusNotifier(PUSH_PLUS_TOKEN)
    qinglong_notifier = QingLongNotifier(QL_API_URL, QL_API_TOKEN)
    
    # 执行签到
    sign_result = sign_in()
    stats = None
    
    # 组装通知内容
    现在 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    title = "自动签到通知-刷刷王 应用"
    
    if not sign_result:
        info = {
            "时间": now,
            "状态": "❌ 签到失败",
            "详情": "请求异常，请检查Cookie有效性"
        }
    else:
        # 获取统计数据（如果签到成功）
        if sign_result.get("code") == 0:
            stats = get_stats()
            info = {
                "时间": now,
                "状态": "✅ 签到成功",
                "奖励": sign_result.get("reward", "未知"),
                "统计": stats if stats else "获取失败"
            }
        else:
            info = {
                "时间": now,
                "状态": "⚠️ 签到异常",
                "详情": sign_result.get("msg", "未知错误"),
                "响应": sign_result  # 包含完整响应信息便于排查
            }
    
    # 转为JSON字符串
    info_json = json.dumps(info, ensure_ascii=False, indent=2)
    
    # 发送通知
    if PUSH_PLUS_TOKEN:
        push_result = push_plus_notifier.send(title, info_json)
        logging.info(f"PushPlus通知状态: {push_result}")
    
    # 使用青龙API发送通知
    if QL_API_TOKEN and QL_API_URL:
        print("发送青龙通知...")
        ql_result = qinglong_notifier.send(title, info_json)
        print(ql_result)
        logging.info(f"青龙通知状态: {ql_result}")
    
    logging.info("自动签到流程结束")

if __name__ == "__main__":
    # 导入随机模块用于添加随机延迟
    import random
    main()    
