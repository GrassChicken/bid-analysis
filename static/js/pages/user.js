// --- 校验逻辑 ---
        function validatePhone() {
            var input = document.getElementById('phone');
            var err = document.getElementById('phoneError');
            if (!/^1[3-9]\d{9}$/.test(input.value)) { showError(input, err, '请输入正确的 11 位手机号码'); return false; }
            showSuccess(input, err); return true;
        }
        function validateEmail() {
            var input = document.getElementById('email');
            var err = document.getElementById('emailError');
            if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(input.value)) { showError(input, err, '请输入正确的邮箱地址'); return false; }
            showSuccess(input, err); return true;
        }
        function validateNewPassword() {
            var input = document.getElementById('newPassword');
            var err = document.getElementById('passwordError');
            var val = input.value;
            if (val.length < 8) { showError(input, err, '密码长度至少 8 位'); return false; }
            if (!(/[a-zA-Z]/.test(val) && /\d/.test(val) && /[!@#$%^&*(),.?":{}|<>]/.test(val))) {
                showError(input, err, '密码必须包含字母、数字和特殊字符'); return false;
            }
            showSuccess(input, err); return true;
        }
        function validateConfirmPassword() {
            var input = document.getElementById('confirmNewPassword');
            var err = document.getElementById('confirmPasswordError');
            if (input.value !== document.getElementById('newPassword').value) { showError(input, err, '两次输入的密码不一致'); return false; }
            showSuccess(input, err); return true;
        }

        // 密码强度计算
        document.getElementById('newPassword').addEventListener('input', function() {
            var val = this.value;
            var score = 0;
            if(val.length >= 8) score++; if(val.length >= 12) score++;
            if(/[a-z]/.test(val) && /[A-Z]/.test(val)) score++;
            if(/\d/.test(val)) score++;
            if(/[!@#$%^&*(),.?":{}|<>]/.test(val)) score++;
            var level = score <= 2 ? 1 : (score <= 3 ? 2 : (score <= 4 ? 3 : 4));
            if(!val) level = 0;
            
            var bars = [document.getElementById('bar1'), document.getElementById('bar2'), document.getElementById('bar3'), document.getElementById('bar4')];
            var colors = ['#e74c3c', '#f39c12', '#3498db', '#27ae60'];
            var texts = ['弱', '一般', '强', '极强'];
            var label = document.getElementById('strengthLabel');
            
            bars.forEach((b, i) => b.style.background = i < level ? colors[level-1] : '#e0e0e0');
            if(level > 0) { label.style.display = 'block'; label.textContent = texts[level-1]; label.style.color = colors[level-1]; }
            else { label.style.display = 'none'; }
        });

        function showError(input, errDiv, msg) { input.classList.remove('success'); input.classList.add('error'); errDiv.textContent = msg; errDiv.style.display = 'block'; }
        function showSuccess(input, errDiv) { input.classList.remove('error'); input.classList.add('success'); errDiv.style.display = 'none'; }

        // 实时校验
        document.getElementById('phone').addEventListener('blur', validatePhone);
        document.getElementById('email').addEventListener('blur', validateEmail);
        document.getElementById('confirmNewPassword').addEventListener('blur', validateConfirmPassword);

        // 提交处理
        function handleUpdateProfile(e) {
            e.preventDefault();
            if (!validatePhone() || !validateEmail()) return;
            
            var btn = document.getElementById('saveProfileBtn');
            btn.disabled = true; btn.textContent = '保存中...';
            
            fetch('/api/user/update-info', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone: document.getElementById('phone').value, email: document.getElementById('email').value })
            })
            .then(r => r.json()).then(data => {
                var msg = document.getElementById('profileMsg');
                if(data.success) { msg.className = 'message message-success'; msg.textContent = '保存成功'; }
                else { msg.className = 'message message-error'; msg.textContent = data.error; }
            }).catch(e => { document.getElementById('profileMsg').className = 'message message-error'; document.getElementById('profileMsg').textContent = '网络错误'; })
            .finally(() => { btn.disabled = false; btn.textContent = '💾 保存修改'; });
        }

        function handleChangePassword(e) {
            e.preventDefault();
            if (!validateNewPassword() || !validateConfirmPassword()) return;
            if (!document.getElementById('oldPassword').value) { document.getElementById('passwordMsg').className='message message-error'; document.getElementById('passwordMsg').textContent='请输入当前密码'; return; }

            var btn = document.getElementById('changePassBtn');
            btn.disabled = true; btn.textContent = '修改中...';

            fetch('/api/user/change-password', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    old_password: document.getElementById('oldPassword').value,
                    new_password: document.getElementById('newPassword').value
                })
            })
            .then(r => r.json()).then(data => {
                var msg = document.getElementById('passwordMsg');
                if(data.success) { msg.className = 'message message-success'; msg.textContent = '密码修改成功'; document.getElementById('passwordForm').reset(); document.getElementById('strengthLabel').style.display='none'; }
                else { msg.className = 'message message-error'; msg.textContent = data.error; }
            }).catch(e => { document.getElementById('passwordMsg').className='message message-error'; document.getElementById('passwordMsg').textContent='网络错误'; })
            .finally(() => { btn.disabled = false; btn.textContent = '🔄 确认修改密码'; });
        }

        // 退出登录模态框
        function showLogoutModal() { document.getElementById('logoutModal').style.display = 'flex'; }
        function hideLogoutModal() { document.getElementById('logoutModal').style.display = 'none'; }
        function performLogout() {
            fetch('/api/auth/logout', { method: 'POST' })
            .then(() => { window.location.href = '/login'; });
        }