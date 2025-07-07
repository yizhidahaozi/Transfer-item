const axios = require('axios');
const fs = require('fs');
const path = require('path');
const dayjs = require('dayjs');

// 日志函数
const log = (message) => {
  const timestamp = dayjs().format('YYYY-MM-DD HH:mm:ss');
  console.log(`[${timestamp}] ${message}`);
};

// 获取环境变量中的Cookie
const getEnvCookies = () => {
  try {
    const cookies = process.env.MEITUAN_COOKIE;
    if (!cookies) {
      log('未找到MEITUAN_COOKIE环境变量');
      return [];
    }
    return cookies.split('&').filter(Boolean);
  } catch (error) {
    log(`获取Cookie失败: ${error.message}`);
    return [];
  }
};

// 检查Cookie有效性
const validateCookie = (cookie) => {
  const requiredFields = ['waimai_uuid', 'token', 'userid'];
  return requiredFields.every(field => cookie.includes(field));
};

// 获取用户信息
const getUserInfo = async (cookie) => {
  const headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
    'Cookie': cookie,
    'Referer': 'https://h5.waimai.meituan.com/'
  };

  try {
    const res = await axios.get('https://h5.waimai.meituan.com/waimai/mindex/api/user/info', { headers });
    if (res.data.code === 0) {
      return res.data.data.nickname || '未命名用户';
    }
    return '未知用户';
  } catch (error) {
    return '未知用户';
  }
};

// 签到函数
const checkIn = async (cookie, userInfo) => {
  const headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
    'Cookie': cookie,
    'Referer': 'https://h5.waimai.meituan.com/waimai/mindex/pages/checkin/index',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'https://h5.waimai.meituan.com',
    'Accept': 'application/json',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive'
  };

  try {
    // 1. 获取签到状态
    log(`${userInfo} - 正在获取签到状态...`);
    const statusRes = await axios.get('https://h5.waimai.meituan.com/waimai/mindex/api/checkin/status', { headers });
    
    if (statusRes.data.code !== 0) {
      return { success: false, message: `获取签到状态失败: ${statusRes.data.msg}` };
    }
    
    if (statusRes.data.data.hasCheckIn) {
      return { success: true, message: '今日已签到', checkedIn: true, rewardAmount: 0 };
    }
    
    // 2. 执行签到
    log(`${userInfo} - 准备签到...`);
    const checkInRes = await axios.post('https://h5.waimai.meituan.com/waimai/mindex/api/checkin/checkin', '', { headers });
    
    if (checkInRes.data.code === 0) {
      const rewardAmount = checkInRes.data.data.rewardAmount || 0;
      const consecutiveDays = checkInRes.data.data.consecutiveDays || 0;
      return { 
        success: true, 
        message: `签到成功，获得 ${rewardAmount} 元红包，连续签到 ${consecutiveDays} 天`,
        checkedIn: true,
        rewardAmount
      };
    } else {
      return { success: false, message: `签到失败: ${checkInRes.data.msg || '未知错误'}` };
    }
  } catch (error) {
    return { success: false, message: `签到异常: ${error.message}` };
  }
};

// 获取账户红包信息
const getRedEnvelopes = async (cookie, userInfo) => {
  const headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
    'Cookie': cookie,
    'Referer': 'https://h5.waimai.meituan.com/waimai/mindex/pages/mycoupon/index',
  };

  try {
    const res = await axios.get('https://h5.waimai.meituan.com/waimai/mindex/api/coupon/list', { headers });
    
    if (res.data.code === 0) {
      const available = res.data.data.coupons.filter(c => c.status === 1).length;
      const expired = res.data.data.coupons.filter(c => c.status === 2).length;
      return { available, expired };
    }
    
    return { available: 0, expired: 0 };
  } catch (error) {
    log(`${userInfo} - 获取红包信息失败: ${error.message}`);
    return { available: 0, expired: 0 };
  }
};

// 主函数
const main = async () => {
  log('===== 美团自动签到脚本开始执行 =====');
  const cookies = get_env_cookies();
  
  if (cookies.length === 0) {
    log('没有可用的Cookie，退出执行');
    return;
  }
  
  let summary = [];
  
  for (let i = 0; i < cookies.length; i++) {
    log(`\n===== 开始处理第 ${i + 1}/${cookies.length} 个账号 =====`);
    const cookie = cookies[i];
    
    // 验证Cookie有效性
    if (!validateCookie(cookie)) {
      log(`警告: 第 ${i + 1} 个Cookie不完整，可能缺少必要字段`);
      summary.push({ account: `账号${i + 1}`, success: false, message: 'Cookie不完整' });
      continue;
    }
    
    // 获取用户信息
    const userInfo = await getUserInfo(cookie);
    log(`当前账号: ${userInfo}`);
    
    // 执行签到
    const checkInResult = await checkIn(cookie, userInfo);
    log(`${userInfo} - ${checkInResult.message}`);
    
    // 获取红包信息
    const红包Info = await getRedEnvelopes(cookie, userInfo);
    log(`${userInfo} - 当前可用红包: ${红包Info.available} 个，已过期: ${红包Info.expired} 个`);
    
    // 记录结果
    summary.push({
      account: `${userInfo} (账号${i + 1})`,
      success: checkInResult.success,
      message: checkInResult.message,
      checkedIn: checkInResult.checkedIn,
      rewardAmount: checkInResult.rewardAmount || 0,
      coupons: 红包Info.available
    });
    
    // 账号间延迟，避免请求频繁
    if (i < cookies.length - 1) {
      const delay = Math.floor(Math.random() * 5000) + 5000; // 5-10秒随机延迟
      log(`等待 ${delay/1000} 秒后处理下一个账号...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  // 汇总结果
  log('\n===== 签到结果汇总 =====');
  summary.forEach((result, index) => {
    const status = result.success ? (result.checkedIn ? '✅ 已签到' : '✅ 今日已签过') : '❌ 签到失败';
    log(`${index + 1}. ${result.account}: ${status} - ${result.message}`);
  });
  
  // 保存日志
  try {
    const logDir = path.join(__dirname, 'logs');
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir);
    }
    
    const logPath = path.join(logDir, `meituan_checkin_${dayjs().format('YYYY-MM-DD')}.log`);
    const logContent = summary.map((result, index) => 
      `${index + 1}. ${result.account}: ${result.success ? '成功' : '失败'} - ${result.message}`
    ).join('\n');
    
    fs.writeFileSync(logPath, logContent);
    log(`结果已保存到: ${logPath}`);
  } catch (error) {
    log(`保存日志失败: ${error.message}`);
  }
  
  log('\n===== 美团自动签到脚本执行完毕 =====');
};

// 执行主函数
main()。catch(error => {
  log(`脚本运行异常: ${error.message}`);
  process.exit(1);
});    
