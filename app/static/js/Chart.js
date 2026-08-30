```html
<script>
    const chartElement = document.getElementById('budgetChart');

    if (chartElement) {
        const ctx = chartElement.getContext('2d');

        // Data passed from FastAPI/Jinja backend
        const categoryLabels = {{ category_names | default([]) | tojson }};
        const budgetData = {{ budget_amounts | default([]) | tojson }};
        const actualData = {{ actual_amounts | default([]) | tojson }};

        new Chart(ctx, {
            type: 'bar',

            data: {
                labels: categoryLabels,

                datasets: [
                    {
                        label: 'Budget (RM)',
                        data: budgetData,
                        backgroundColor: 'rgba(37, 99, 235, 0.7)',
                        borderColor: 'rgba(37, 99, 235, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Actual Spent (RM)',
                        data: actualData,
                        backgroundColor: 'rgba(34, 197, 94, 0.7)',
                        borderColor: 'rgba(34, 197, 94, 1)',
                        borderWidth: 1
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                scales: {
                    y: {
                        beginAtZero: true,

                        ticks: {
                            color: '#94a3b8',

                            callback: function(value) {
                                return 'RM ' + value;
                            }
                        },

                        grid: {
                            color: '#334155'
                        }
                    },

                    x: {
                        ticks: {
                            color: '#94a3b8'
                        },

                        grid: {
                            display: false
                        }
                    }
                },

                plugins: {
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                }
            }
        });
    }
</script>
```
