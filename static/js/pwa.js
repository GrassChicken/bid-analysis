/**
 * PWA 安装和推送通知管理
 */

// VAPID 公钥（用于推送通知）
// 从服务器动态获取
let VAPID_PUBLIC_KEY = '';

// 获取 VAPID 公钥
async function fetchVapidPublicKey() {
  try {
    const response = await fetch('/api/push/vapid-public-key');
    const data = await response.json();
    VAPID_PUBLIC_KEY = data.public_key;
    console.log('✅ 获取 VAPID 公钥:', VAPID_PUBLIC_KEY.substring(0, 20) + '...');
  } catch (error) {
    console.error('❌ 获取 VAPID 公钥失败:', error);
  }
}

// 存储推送订阅
let pushSubscription = null;

/**
 * 初始化 PWA 功能
 */
async function initPWA() {
  console.log('🚀 初始化 PWA...');
  
  // 先获取 VAPID 公钥
  await fetchVapidPublicKey();
  
  // 检查是否支持 Service Worker
  if (!('serviceWorker' in navigator)) {
    console.log('❌ 不支持 Service Worker');
    return;
  }

  try {
    // 注册 Service Worker
    const registration = await navigator.serviceWorker.register('/static/sw.js', {
      scope: '/'
    });
    
    console.log('✅ Service Worker 注册成功:', registration.scope);
    
    // 检查通知权限
    checkNotificationPermission();
    
    // 监听安装事件
    setupInstallPrompt();
    
    // 监听推送订阅变化
    setupPushSubscriptionChange();
    
  } catch (error) {
    console.error('❌ Service Worker 注册失败:', error);
    // iOS Safari 不支持 Service Worker，但仍可以 "添加到主屏幕"
    if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
      console.log('ℹ️ iOS Safari：Service Worker 不支持，但可手动添加到主屏幕');
      setupInstallPrompt();
    }
  }
}

/**
 * 检查通知权限
 */
async function checkNotificationPermission() {
  if (!('Notification' in window)) {
    console.log('❌ 不支持通知');
    return;
  }

  const permission = Notification.permission;
  console.log('📢 通知权限:', permission);

  if (permission === 'granted') {
    // 已授权，检查订阅
    checkPushSubscription();
  } else if (permission !== 'denied') {
    // 未拒绝，可以请求授权
    console.log('ℹ️ 可以请求通知授权');
  }
}

/**
 * 请求通知权限
 */
async function requestNotificationPermission() {
  if (!('Notification' in window)) {
    alert('您的浏览器不支持通知功能');
    return false;
  }

  const permission = await Notification.requestPermission();
  console.log('📢 通知权限结果:', permission);

  if (permission === 'granted') {
    // 请求成功后订阅推送
    await subscribeToPush();
    return true;
  } else {
    alert('您已拒绝通知权限，无法接收推送消息');
    return false;
  }
}

/**
 * 订阅推送通知
 */
async function subscribeToPush() {
  try {
    const registration = await navigator.serviceWorker.ready;
    
    // 检查是否已有订阅
    let subscription = await registration.pushManager.getSubscription();
    
    if (subscription) {
      console.log('✅ 已有推送订阅');
      pushSubscription = subscription;
      updateSubscriptionUI(true);
      return subscription;
    }

    // 创建新订阅
    console.log('📝 创建新推送订阅...');
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
    });

    console.log('✅ 推送订阅成功');
    pushSubscription = subscription;

    // 发送到服务器保存
    await savePushSubscription(subscription);
    
    updateSubscriptionUI(true);
    return subscription;

  } catch (error) {
    console.error('❌ 推送订阅失败:', error);
    throw error;
  }
}

/**
 * 取消推送订阅
 */
async function unsubscribeFromPush() {
  try {
    const registration = await navigator.serviceWorker.ready;
    let subscription = await registration.pushManager.getSubscription();
    
    if (!subscription) {
      console.log('ℹ️ 没有推送订阅');
      return false;
    }

    const successful = await subscription.unsubscribe();
    console.log('✅ 取消推送订阅:', successful);
    
    if (successful) {
      // 通知服务器删除订阅
      await removePushSubscription();
      pushSubscription = null;
      updateSubscriptionUI(false);
    }
    
    return successful;
  } catch (error) {
    console.error('❌ 取消推送订阅失败:', error);
    throw error;
  }
}

/**
 * 检查推送订阅状态
 */
async function checkPushSubscription() {
  try {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    
    if (subscription) {
      console.log('✅ 已有推送订阅');
      pushSubscription = subscription;
      updateSubscriptionUI(true);
    } else {
      console.log('ℹ️ 没有推送订阅');
      updateSubscriptionUI(false);
    }
    
    return !!subscription;
  } catch (error) {
    console.error('❌ 检查推送订阅失败:', error);
    updateSubscriptionUI(false);
    return false;
  }
}

/**
 * 保存推送订阅到服务器
 */
async function savePushSubscription(subscription) {
  try {
    const response = await fetch('/api/push/subscribe', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        subscription: subscription,
        user_id: getCurrentUserId()
      })
    });

    const result = await response.json();
    console.log('✅ 推送订阅已保存到服务器:', result);
    return result;
  } catch (error) {
    console.error('❌ 保存推送订阅失败:', error);
    throw error;
  }
}

/**
 * 从服务器删除推送订阅
 */
async function removePushSubscription() {
  try {
    const response = await fetch('/api/push/unsubscribe', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: getCurrentUserId()
      })
    });

    const result = await response.json();
    console.log('✅ 推送订阅已从服务器删除:', result);
    return result;
  } catch (error) {
    console.error('❌ 删除推送订阅失败:', error);
    throw error;
  }
}

/**
 * 设置安装提示
 */
function setupInstallPrompt() {
  let deferredPrompt = null;
  const installBtn = document.getElementById('install-pwa-btn');

  // 监听浏览器原生安装提示事件
  window.addEventListener('beforeinstallprompt', (e) => {
    console.log('💡 浏览器支持 PWA 安装');
    e.preventDefault();
    deferredPrompt = e;
    
    // 显示浮动安装按钮
    if (installBtn) {
      installBtn.style.display = 'flex';
      installBtn.onclick = async () => {
        if (deferredPrompt) {
          deferredPrompt.prompt();
          const { outcome } = await deferredPrompt.userChoice;
          console.log('📲 用户选择:', outcome);
          deferredPrompt = null;
          installBtn.style.display = 'none';
        }
      };
    }
  });

  // 安装完成后的回调
  window.addEventListener('appinstalled', () => {
    console.log('✅ PWA 已安装');
    deferredPrompt = null;
    if (installBtn) {
      installBtn.style.display = 'none';
    }
  });

  // 兼容处理：Chrome HTTP 环境下不会触发 beforeinstallprompt
  // 但仍然提供手动安装指引
  if (installBtn) {
    installBtn.onclick = () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
      } else {
        // 无法自动弹出，显示手动安装指引
        showManualInstallGuide();
      }
    };
  }

  // 如果不是 Chrome 或 HTTPS，尝试手动引导
  const isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
  const isHTTPS = location.protocol === 'https:';
  const isLocalhost = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  
  if (!isChrome && !/iPhone|iPad|iPod/.test(navigator.userAgent)) {
    // 非 Chrome 浏览器，尝试显示按钮
    if (installBtn) {
      installBtn.style.display = 'flex';
    }
  } else if (isChrome && !isHTTPS && !isLocalhost) {
    // Chrome + HTTP 环境，提示需要 HTTPS
    if (installBtn) {
      installBtn.style.display = 'flex';
    }
  }
}

/**
 * 显示手动安装指引
 */
function showManualInstallGuide() {
  const ua = navigator.userAgent;
  const isIOS = /iPhone|iPad|iPod/.test(ua);
  const isAndroid = /Android/.test(ua);
  const isChrome = /Chrome/.test(ua) && /Google Inc/.test(navigator.vendor);
  
  let guide = '';
  
  if (isIOS) {
    guide = '📲 添加到主屏幕\n\n' +
      '1. 点击底部分享按钮（□↑）\n' +
      '2. 选择「添加到主屏幕」\n' +
      '3. 点击「添加」即可';
  } else if (isChrome) {
    guide = '📲 添加到主屏幕\n\n' +
      '方法1：点击浏览器右上角 ⋮ → "安装应用"\n' +
      '方法2：地址栏最右侧找到安装图标 → 点击安装\n\n' +
      '💡 提示：如果使用 HTTP 访问，Chrome 可能不会显示安装选项，建议配置 HTTPS';
  } else {
    guide = '📲 安装应用\n\n' +
      '请点击浏览器菜单中的「添加到主屏幕」或「安装应用」选项';
  }
  
  alert(guide);
}

/**
 * 监听推送订阅变化
 */
function setupPushSubscriptionChange() {
  navigator.serviceWorker.ready.then(registration => {
    registration.pushManager.onsubscriptionchange = async () => {
      console.log('🔄 推送订阅已变更');
      await checkPushSubscription();
    };
  });
}

/**
 * 更新订阅 UI 状态
 */
function updateSubscriptionUI(isSubscribed) {
  const subscribeBtn = document.getElementById('subscribe-push-btn');
  const statusEl = document.getElementById('push-status');
  
  if (subscribeBtn) {
    if (isSubscribed) {
      subscribeBtn.textContent = '关闭推送通知';
      subscribeBtn.classList.remove('btn-primary');
      subscribeBtn.classList.add('btn-danger');
    } else {
      subscribeBtn.textContent = '开启推送通知';
      subscribeBtn.classList.remove('btn-danger');
      subscribeBtn.classList.add('btn-primary');
    }
  }
  
  if (statusEl) {
    statusEl.textContent = isSubscribed ? '✅ 已开启' : '❌ 未开启';
    statusEl.className = isSubscribed ? 'status-success' : 'status-error';
  }
}

/**
 * 获取当前用户 ID（从页面或 cookie）
 */
function getCurrentUserId() {
  // 从全局变量获取
  if (window.CURRENT_USER_ID) {
    return window.CURRENT_USER_ID;
  }
  
  // 从 cookie 获取
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'user_id') {
      return value;
    }
  }
  
  return null;
}

/**
 * Base64 转 Uint8Array（VAPID 密钥转换）
 */
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

/**
 * 测试推送通知
 */
async function testPushNotification() {
  try {
    const response = await fetch('/api/push/test', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: getCurrentUserId()
      })
    });

    const result = await response.json();
    if (result.success) {
      alert('✅ 测试通知已发送，请查看通知栏');
    } else {
      alert('❌ 发送失败：' + result.message);
    }
  } catch (error) {
    alert('❌ 测试失败：' + error.message);
  }
}

// 页面加载时初始化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPWA);
} else {
  initPWA();
}

// 导出函数供全局使用
window.PWA = {
  init: initPWA,
  requestPermission: requestNotificationPermission,
  subscribe: subscribeToPush,
  unsubscribe: unsubscribeFromPush,
  test: testPushNotification
};
