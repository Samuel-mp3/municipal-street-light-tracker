// Reports Chart.js Initializations

document.addEventListener('DOMContentLoaded', function () {
    const wardCanvas = document.getElementById('reportWardChart');
    const faultCanvas = document.getElementById('reportFaultChart');
    const monthlyCanvas = document.getElementById('reportMonthlyChart');

    if (!wardCanvas || !faultCanvas || !monthlyCanvas) return;

    fetch('/api/reports/chart-data')
        .then(response => response.json())
        .then(data => {
            // 1. Ward Chart
            new Chart(wardCanvas, {
                type: 'bar',
                data: {
                    labels: data.ward.labels,
                    datasets: [{
                        label: 'Total Complaints',
                        data: data.ward.datasets[0].data,
                        backgroundColor: '#1e3a8a',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } }
                }
            });

            // 2. Fault Chart
            new Chart(faultCanvas, {
                type: 'pie',
                data: {
                    labels: data.fault.labels,
                    datasets: [{
                        data: data.fault.datasets[0].data,
                        backgroundColor: ['#ef4444', '#f59e0b', '#3b82f6', '#10b981', '#8b5cf6', '#64748b']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } }
                }
            });

            // 3. Monthly Trend Chart (Line Chart)
            new Chart(monthlyCanvas, {
                type: 'line',
                data: {
                    labels: data.monthly.labels,
                    datasets: [
                        {
                            label: 'Total Reported',
                            data: data.monthly.datasets[0].data,
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            fill: true,
                            tension: 0.3
                        },
                        {
                            label: 'Repaired',
                            data: data.monthly.datasets[1].data,
                            borderColor: '#10b981',
                            backgroundColor: 'transparent',
                            borderDash: [5, 5],
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } }
                }
            });
        })
        .catch(err => console.error("Error loading report chart data:", err));
});
