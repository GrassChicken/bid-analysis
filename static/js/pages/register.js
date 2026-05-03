// 实时验证
        document.getElementById('username').addEventListener('blur', validateUsername);
        document.getElementById('password').addEventListener('input', updateStrengthMeter);
        document.getElementById('password').addEventListener('blur', validatePassword);
        document.getElementById('confirmPassword').addEventListener('blur', validateConfirmPassword);
        document.getElementById('phone').addEventListener('blur', validatePhone);
        document.getElementById('email').addEventListener('blur', validateEmail);
        
        function validateUsername() {
            var input = document.getElementById('username');
            var errorDiv = document.getElementById('usernameError');
            var value = input.value.trim();
            
            if (value.length < 3 || value.length > 20) {
                showError(input, errorDiv, '用户名长度必须在 3-20 位之间');
                return false;
            }
            if (!/^[a-zA-Z0-9_]+$/.test(value)) {
                showError(input, errorDiv, '用户名只能包含字母、数字和下划线');
                return false;
            }
            showSuccess(input, errorDiv);
            return true;
        }
        
        function validatePassword() {
            var input = document.getElementById('password');
            var errorDiv = document.getElementById('passwordError');
            var value = input.value;
            
            if (value.length < 8) {
                showError(input, errorDiv, '密码长度至少 8 位');
                return false;
            }
            // 检查复杂度：必须包含字母、数字、特殊字符
            // 特殊字符定义为：!@#$%^&*(),.?":{}|<>
            var hasLetter = /[a-zA-Z]/.test(value);
            var hasNumber = /\d/.test(value);
            var hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(value);
            
            if (!hasLetter || !hasNumber || !hasSpecial) {
                showError(input, errorDiv, '密码必须包含字母、数字和特殊字符');
                return false;
            }
            
            // 如果验证通过且强度不够，提示提升强度
            if (getPasswordScore(value) < 2) {
                 // 允许提交，但不报错，或者强制要求中强密码
                 // 这里我们仅要求满足上述复杂度，强度指示器仅作提示
            }
            
            showSuccess(input, errorDiv);
            return true;
        }
        
        function getPasswordScore(password) {
            var score = 0;
            if (password.length >= 8) score++;
            if (password.length >= 12) score++;
            if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
            if (/\d/.test(password)) score++;
            if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;
            
            // 归一化到 0-3 (对应 4 个条)
            if (score <= 1) return 1; // 弱
            if (score <= 2) return 2; // 中
            if (score <= 3) return 3; // 强
            return 4; // 极强
        }
        
        function updateStrengthMeter() {
            var input = document.getElementById('password');
            var value = input.value;
            var bars = [
                document.getElementById('bar1'),
                document.getElementById('bar2'),
                document.getElementById('bar3'),
                document.getElementById('bar4')
            ];
            var label = document.getElementById('strengthLabel');
            
            if (!value) {
                label.style.display = 'none';
                bars.forEach(b => b.style.background = '#e0e0e0');
                return;
            }
            
            label.style.display = 'block';
            var score = getPasswordScore(value);
            var colors = ['#e74c3c', '#f39c12', '#3498db', '#27ae60'];
            var texts = ['弱', '一般', '强', '极强'];
            
            bars.forEach((bar, index) => {
                if (index < score) {
                    bar.style.background = colors[score - 1];
                } else {
                    bar.style.background = '#e0e0e0';
                }
            });
            
            label.textContent = texts[score - 1];
            label.style.color = colors[score - 1];
        }
        
        function validateConfirmPassword() {
            var input = document.getElementById('confirmPassword');
            var errorDiv = document.getElementById('confirmPasswordError');
            var password = document.getElementById('password').value;
            var value = input.value;
            
            if (value !== password) {
                showError(input, errorDiv, '两次输入的密码不一致');
                return false;
            }
            showSuccess(input, errorDiv);
            return true;
        }
        
        function validatePhone() {
            var input = document.getElementById('phone');
            var errorDiv = document.getElementById('phoneError');
            var value = input.value.trim();
            
            if (!/^1[3-9]\d{9}$/.test(value)) {
                showError(input, errorDiv, '请输入正确的 11 位手机号码');
                return false;
            }
            showSuccess(input, errorDiv);
            return true;
        }
        
        function validateEmail() {
            var input = document.getElementById('email');
            var errorDiv = document.getElementById('emailError');
            var value = input.value.trim();
            
            if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value)) {
                showError(input, errorDiv, '请输入正确的邮箱地址');
                return false;
            }
            showSuccess(input, errorDiv);
            return true;
        }
        
        function showError(input, errorDiv, message) {
            input.classList.remove('success');
            input.classList.add('error');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }
        
        function showSuccess(input, errorDiv) {
            input.classList.remove('error');
            input.classList.add('success');
            errorDiv.style.display = 'none';
        }
        
        function handleRegister(event) {
            event.preventDefault();
            
            // 验证所有字段
            var valid = true;
            valid = validateUsername() && valid;
            valid = validatePassword() && valid;
            valid = validateConfirmPassword() && valid;
            valid = validatePhone() && valid;
            valid = validateEmail() && valid;
            
            if (!valid) {
                return;
            }
            
            var username = document.getElementById('username').value.trim();
            var password = document.getElementById('password').value;
            var phone = document.getElementById('phone').value.trim();
            var email = document.getElementById('email').value.trim();
            var btn = document.getElementById('registerBtn');
            var errorDiv = document.getElementById('errorMessage');
            var successDiv = document.getElementById('successMessage');
            
            // 显示加载状态
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span>注册中...';
            errorDiv.style.display = 'none';
            successDiv.style.display = 'none';
            
            fetch('/api/auth/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: username,
                    password: password,
                    phone: phone,
                    email: email
                })
            })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.success) {
                    successDiv.textContent = '✅ 注册成功！即将跳转到登录页面...';
                    successDiv.style.display = 'block';
                    setTimeout(function() {
                        window.location.href = '/';
                    }, 2000);
                } else {
                    errorDiv.textContent = data.error || '注册失败，请稍后重试';
                    errorDiv.style.display = 'block';
                    btn.disabled = false;
                    btn.innerHTML = '立即注册';
                }
            })
            .catch(function(error) {
                errorDiv.textContent = '网络错误，请稍后重试';
                errorDiv.style.display = 'block';
                btn.disabled = false;
                btn.innerHTML = '立即注册';
            });
        }