import requests
import json
import os
import logging
import time
import re
from datetime import datetime
from urllib.parse import urlencode

# 日志配置（区分不同级别，便于调试和监控）
logging.basicConfig(
    level=logging.INFO,  # 默认INFO级别，生产环境减少冗余信息
    format='%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 环境变量配置（支持多来源，兼容青龙/本地环境）
ENV_CONFIG = {
    "cookie": os.environ.get('ZHH_TL55_COOKIE', ''),
    "username": os.environ.get('ZHH_TL55_USERNAME', ''),
    "password": os.environ.get('ZHH_TL55_PASSWORD', ''),
    "push_token": os.environ.get('PUSH_PLUS_TOKEN', ''),
    "ql_token": os.environ.get('QL_API_TOKEN', ''),
    "ql_url": os.environ.get('QL_API_URL', 'http://localhost:5700'),
    "debug": os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
}

# 核心URL配置（严格匹配网站接口规范）
BASE_DOMAIN = "https://zhh.tl55.cn"
URLS = {
    "login_page": f"{BASE_DOMAIN}/user/login.php",
    "login_api": f"{BASE_DOMAIN}/user/ajax_user.php?act=login",  # 登录接口强制包含act=login
    "sign_api": f"{BASE_DOMAIN}/user/ajax_user.php?act=qiandao",
    "stats_api": f"{BASE_DOMAIN}/user/ajax_user.php?act=qdcount",
    "home_page": f"{BASE_DOMAIN}/user/index.php"
}

# 业务状态码映射（增强可读性）
STATUS_CODES = {
    0: "签到成功",
    -1: "今日已签到",
    -4: "未识别操作(No Act)",
    # 可扩展其他状态码
}

# 会话保持（关键：所有请求共享一个会话，确保Cookie连贯）
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
    "Origin": BASE_DOMAIN,
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty"
})

# 调试模式下启用更详细的日志
if ENV_CONFIG["debug"]:
    logger.setLevel(logging.DEBUG)
    # 启用requests库的调试日志
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)


class Notifier:
    """通知工具类（整合多渠道通知，支持自定义模板）"""
    
    def __init__(self, push_token, ql_url, ql_token):
        self.push_token = push_token
        self.ql_url = ql_url
        self.ql_token = ql_token
        
    def _format_content(self, title, content):
        """格式化通知内容（支持JSON/Markdown等格式）"""
        if isinstance(content, dict):
            # 添加时间戳
            content["时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return json.dumps(content, ensure_ascii=False, indent=2)
        return content
        
    def push_plus(self, title, content):
        """PushPlus通知"""
        if not self.push_token:
            return "⚠️ PushPlus Token未配置，跳过通知"
            
        try:
            formatted_content = self._format_content(title, content)
            response = requests.post(
                "https://www.pushplus.plus/send",
                json={
                    "token": self.push_token,
                    "title": title,
                    "content": formatted_content,
                    "template": "json"
                },
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            
            return f"✅ PushPlus通知成功（{result.get('msg', '未知状态')}）"
        except Exception as e:
            return f"❌ PushPlus通知失败: {str(e)}"
    
    def qinglong(self, title, content):
        """青龙面板通知"""
        if not self.ql_url or not self.ql_token:
            return "⚠️ 青龙配置不完整，跳过通知"
            
        try:
            formatted_content = self._format_content(title, content)
            response = requests.post(
                f"{self.ql_url}/open/system/notify",
                headers={"Authorization": f"Bearer {self.ql_token}"},
                json={"title": title, "content": formatted_content},
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            
            return f"✅ 青龙通知成功（{result.get('message', '未知状态')}）"
        except Exception as e:
            return f"❌ 青龙通知失败: {str(e)}"
    
    def send(self, title, content, level="info"):
        """
        发送组合通知（支持按级别过滤）
        level: info/warning/error
        """
        # 根据级别决定是否发送通知
        if level == "info" and not (self.push_token or self.ql_token):
            logger.info("跳过通知：未配置通知渠道且级别为info")
            return
            
        push_result = self.push_plus(title, content)
        ql_result = self.qinglong(title, content)
        
        # 记录通知结果
        logger.info(f"通知发送结果：{push_result}; {ql_result}")
        return {"push_plus": push_result, "qinglong": ql_result}


def get_login_params():
    """获取登录页面隐藏参数（如CSRF令牌）"""
    try:
        logger.debug("正在获取登录页面隐藏参数...")
        response = session.get(URLS["login_page"], timeout=10)
        response.raise_for_status()
        
        # 从HTML中提取可能存在的隐藏参数（根据实际页面结构调整）
        params = {}
        
        # 示例：提取CSRF令牌（如果页面中有name="csrf_token"的隐藏字段）
        csrf_match = re.search(r'name="csrf_token" value="(.*?)"', response.text)
        if csrf_match:
            params["csrf_token"] = csrf_match.group(1)
            logger.debug(f"成功获取CSRF令牌: {params['csrf_token']}")
            
        # 示例：提取时间戳（如果需要）
        timestamp_match = re.search(r'name="timestamp" value="(.*?)"', response.text)
        if timestamp_match:
            params["timestamp"] = timestamp_match.group(1)
            logger.debug(f"成功获取时间戳: {params['timestamp']}")
            
        return params
        
    except Exception as e:
        logger.warning(f"获取登录隐藏参数失败: {str(e)}，使用默认参数")
        return {}


def login(username, password):
    """登录核心逻辑（严格匹配网站接口规范）"""
    if not username or not password:
        logger.error("❌ 账号或密码未配置，无法登录")
        return False
        
    logger.info("开始登录流程...")
    
    try:
        # 1. 获取登录页面隐藏参数
        hidden_params = get_login_params()
        
        # 2. 设置登录请求头
        session.headers["Referer"] = URLS["login_page"]
        session.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        
        # 3. 构建登录数据
        login_data = {
            **hidden_params,  # 合并隐藏参数
            "username": username,
            "password": password,
            # 可根据实际需要添加其他参数
        }
        
        logger.debug(f"登录请求URL: {URLS['login_api']}")
        logger.debug(f"登录请求数据: {login_data}")
        
        # 4. 发送登录请求
        response = session.post(
            URLS["login_api"],
            data=login_data,
            timeout=15
        )
        response.raise_for_status()
        
        # 5. 解析登录响应
        try:
            result = response.json()
        except json.JSONDecodeError:
            logger.error(f"登录响应非JSON格式: {response.text[:200]}")
            return False
            
        logger.info(f"登录响应: {json.dumps(result, ensure_ascii=False)}")
        
        # 6. 判断登录结果
        if result.get("code") == 0:
            logger.info("✅ 登录成功")
            return True
        else:
            error_msg = result.get("msg", "未知错误")
            error_code = result.get("code", "未知代码")
            logger.error(f"❌ 登录失败: [{error_code}] {error_msg}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 登录过程发生异常: {str(e)}")
        return False


def check_cookie_valid():
    """验证Cookie有效性"""
    logger.info("开始验证Cookie有效性...")
    
    try:
        session.headers["Referer"] = f"{BASE_DOMAIN}/user/"
        response = session.get(URLS["home_page"], timeout=10)
        response.raise_for_status()
        
        # 根据页面内容判断是否需要登录
        if "请登录" in response.text or "login.php" in response.url:
            logger.warning("⚠️ Cookie已失效或未登录")
            return False
            
        logger.info("✅ Cookie有效")
        return True
        
    except Exception as e:
        logger.error(f"❌ 验证Cookie有效性失败: {str(e)}")
        return False


def sign_in():
    """执行签到操作"""
    logger.info("开始执行签到...")
    
    try:
        session.headers["Referer"] = f"{BASE_DOMAIN}/user/qiandao.php"
        response = session.get(URLS["sign_api"], timeout=15)
        response.raise_for_status()
        
        try:
            result = response.json()
        except json.JSONDecodeError:
            logger.error(f"签到响应非JSON格式: {response.text[:200]}")
            return None
            
        # 记录签到结果（包含业务状态码描述）
        code = result.get("code", "未知")
        status_text = STATUS_CODES.get(code, "未知状态")
        logger.info(f"签到结果: [{code}] {status_text} - {result.get('msg', '')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 签到过程发生异常: {str(e)}")
        return None


def get_sign_stats():
    """获取签到统计数据"""
    logger.info("获取签到统计数据...")
    
    try:
        session.headers["Referer"] = f"{BASE_DOMAIN}/user/qiandao.php"
        response = session.get(URLS["stats_api"], timeout=15)
        response.raise_for_status()
        
        try:
            return response.json()
        except json.JSONDecodeError:
            logger.error(f"统计响应非JSON格式: {response.text[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"❌ 获取统计数据失败: {str(e)}")
        return None


def main():
    """主流程"""
    start_time = time.time()
    logger.info("===== 开始执行自动签到流程 =====")
    
    # 初始化通知器
    notifier = Notifier(
        push_token=ENV_CONFIG["push_token"],
        ql_url=ENV_CONFIG["ql_url"],
        ql_token=ENV_CONFIG["ql_token"]
    )
    
    # 1. 加载初始Cookie（如果有）
    if ENV_CONFIG["cookie"]:
        try:
            cookies = {
                k: v for k, v in (
                    item.split('=', 1) 
                    for item in ENV_CONFIG["cookie"].split('; ') 
                    if '=' in item
                )
            }
            session.cookies.update(cookies)
            logger.info(f"已加载初始Cookie，包含 {len(cookies)} 个键值对")
        except Exception as e:
            logger.error(f"加载初始Cookie失败: {str(e)}")
    
    # 2. 验证Cookie有效性
    cookie_valid = check_cookie_valid()
    
    # 3. 如果Cookie无效，尝试登录
    if not cookie_valid:
        logger.warning("⚠️ Cookie无效，尝试使用账号密码登录...")
        
        if not ENV_CONFIG["username"] or not ENV_CONFIG["password"]:
            error_msg = "❌ 未配置账号密码，无法登录"
            logger.error(error_msg)
            notifier.send("签到失败通知", {
                "状态": "❌ 签到失败",
                "原因": "Cookie失效且未配置账号密码",
                "解决方案": "请在环境变量中配置ZHH_TL55_USERNAME和ZHH_TL55_PASSWORD"
            }, level="error")
            return
            
        login_success = login(ENV_CONFIG["username"], ENV_CONFIG["password"])
        
        if not login_success:
            error_msg = "❌ 登录失败，无法继续执行签到"
            logger.error(error_msg)
            notifier.send("签到失败通知", {
                "状态": "❌ 签到失败",
                "原因": "Cookie失效且登录失败",
                "登录响应": "请查看日志获取详细信息",
                "解决方案": "检查账号密码是否正确或更新登录接口配置"
            }, level="error")
            return
            
        logger.info("✅ 登录成功，继续执行签到流程")
    
    # 4. 执行签到
    sign_result = sign_in()
    
    if not sign_result:
        error_msg = "❌ 签到请求失败或响应解析异常"
        logger.error(error_msg)
        notifier.send("签到异常通知", {
            "状态": "⚠️ 签到异常",
            "原因": "签到请求无有效响应",
            "解决方案": "检查网络连接或API接口是否变更"
        }, level="warning")
        return
    
    # 5. 处理签到结果
    sign_code = sign_result.get("code", "未知")
    sign_msg = sign_result.get("msg", "未知")
    
    if sign_code == 0:  # 签到成功
        logger.info("✅ 签到成功，获取统计数据...")
        stats = get_sign_stats()
        
        notification_content = {
            "状态": "✅ 签到成功",
            "奖励": sign_result.get("reward", "未知"),
            "统计数据": stats if stats else "获取失败",
            "耗时": f"{time.time() - start_time:.2f}秒",
            "服务器响应": sign_result
        }
        
        notifier.send("签到成功通知", notification_content, level="info")
        
    elif sign_code == -1:  # 今日已签到
        logger.info("ℹ️ 今日已完成签到，无需重复操作")
        
        notification_content = {
            "状态": "ℹ️ 今日已签到",
            "消息": sign_msg,
            "建议": "无需重复执行，脚本将自动在明天执行签到",
            "耗时": f"{time.time() - start_time:.2f}秒"
        }
        
        # 已签到状态可以选择不发送通知，避免频繁提醒
        if ENV_CONFIG.get("NOTIFY_ALREADY_SIGNED", "true").lower() == "true":
            notifier.send("zhh.tl55.cn签到通知", notification_content, level="info")
            
    else:  # 其他异常状态
        error_msg = f"❌ 签到异常: [{sign_code}] {sign_msg}"
        logger.error(error_msg)
        
        notification_content = {
            "状态": "⚠️ 签到异常",
            "错误代码": sign_code,
            "错误信息": sign_msg,
            "服务器响应": sign_result,
            "解决方案": "检查账号状态或更新脚本配置"
        }
        
        notifier.send("签到异常通知", notification_content, level="warning")
    
    logger.info(f"===== 自动签到流程结束，耗时 {time.time() - start_time:.2f} 秒 =====")


if __name__ == "__main__":
    main()
