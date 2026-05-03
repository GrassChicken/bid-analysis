// 从后端获取的数据
        const methodDistribution = {{ method_distribution | safe }};
        // const k1Values = Object.keys({{ k1_distribution | safe }});
        const k1Counts = Object.values({k1_distribution});

        // 方法类别分布图
        const ctx1 = document.getElementById('distributionChart').getContext('2d');
        new Chart(ctx1, {
            type: 'bar',
            data: {
                labels: Object.keys(methodDistribution),
                datasets: [{
                    label: '方法类别分布',
                    data: Object.values(methodDistribution),
                    backgroundColor: 'rgba(102, 126, 234, 0.6)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });

        function logout() {
            fetch('/api/logout', {method: 'POST'})
            .then(function() {
                window.location.href = '/';
            });
        }