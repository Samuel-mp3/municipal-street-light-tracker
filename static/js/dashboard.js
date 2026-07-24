// Dashboard Chart.js Initializations

document.addEventListener('DOMContentLoaded', function () {
    const wardCanvas = document.getElementById('wardChart');
    const faultCanvas = document.getElementById('faultChart');

    if (!wardCanvas || !faultCanvas) return;

    fetch('/api/dashboard-charts')
        .then(response => response.json())
        .then(data => {
            // 1. Ward Chart (Bar Chart)
            new Chart(wardCanvas, {
                type: 'bar',
                data: {
                    labels: data.by_ward.labels,
                    datasets: [{
                        label: 'Number of Complaints',
                        data: data.by_ward.data,
                        backgroundColor: '#3b82f6',
                        borderColor: '#1d4ed8',
                        borderWidth: 1,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { precision: 0 }
                        }
                    }
                }
            });

            // 2. Fault Category Chart (Doughnut Chart)
            new Chart(faultCanvas, {
                type: 'doughnut',
                data: {
                    labels: data.by_fault.labels,
                    datasets: [{
                        data: data.by_fault.data,
                        backgroundColor: [
                            '#ef4444',
                            '#f59e0b',
                            '#3b82f6',
                            '#10b981',
                            '#8b5cf6',
                            '#ec4899'
                        ],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { boxWidth: 12, padding: 12 }
                        }
                    }
                }
            });
        })
        .catch(err => console.error("Error fetching dashboard chart data:", err));
});
