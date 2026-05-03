// 移动端优化
        document.addEventListener('DOMContentLoaded', function() {
            var inputs = document.querySelectorAll('input');
            inputs.forEach(function(input) {
                input.addEventListener('focus', function() {
                    setTimeout(function() {
                        input.scrollIntoView({behavior: 'smooth', block: 'center'});
                    }, 300);
                });
            });
        });

        function handleLogin(event) {
            event.preventDefault();

            var username = document.getElementById('username').value.trim();
            var password = document.getElementById('password').value;
            var btn = document.getElementById('loginBtn');
            var errorDiv = document.getElementById('errorMessage');

            if (!username || !password) {
                errorDiv.textContent = '请输入用户名和密码';
                errorDiv.style.display = 'block';
                return;
            }

            // 显示加载状态
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span>登录中...';

            fetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: username, password: password})
            })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.success) {
                    window.location.href = '/dashboard';
                } else {
                    errorDiv.textContent = data.error || '登录失败';
                    // 账号禁用时使用特殊样式
                    if (data.error_code === 'ACCOUNT_DISABLED') {
                        errorDiv.className = 'error-message error-message--disabled';
                    } else {
                        errorDiv.className = 'error-message';
                    }
                    errorDiv.style.display = 'block';
                    btn.disabled = false;
                    btn.innerHTML = '登录';
                }
            })
            .catch(function(error) {
                errorDiv.textContent = '网络错误,请稍后重试';
                errorDiv.style.display = 'block';
                btn.disabled = false;
                btn.innerHTML = '登录';
            });
        }