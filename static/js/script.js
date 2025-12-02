// 1. Theme Logic
function switchTheme() {
    const current = document.body.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.cookie = `theme=${next}; path=/;`;
    location.reload();
}

// 2. Chart Drawing Function
// We make a reusable function so our HTML stays clean
function renderExpenseChart(labels, data) {
    const ctx = document.getElementById('expenseChart').getContext('2d');

    if (labels.length > 0) {
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: ['#ff3b30', '#0071e3', '#34c759', '#ff9500', '#af52de', '#5ac8fa', '#ffcc00'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    } else {
        document.getElementById('expenseChart').style.display = 'none';
        // We add a text message if no chart exists
        const msg = document.createElement('p');
        msg.textContent = "No expenses to show yet.";
        msg.style.textAlign = "center";
        msg.style.color = "gray";
        document.getElementById('expenseChart').parentElement.appendChild(msg);
    }
}