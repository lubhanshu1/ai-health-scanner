const API_URL = "https://ai-health-backend-g329.onrender.com/predict-simple";

let chart;

document.getElementById("healthForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const data = {
        age: +age.value,
        glucose: +glucose.value,
        bp: +bp.value,
        bmi: +bmi.value
    };

    result.innerHTML = "⏳ Predicting...";

    const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });

    const r = await res.json();

    // UI
    result.innerHTML = `
        <b>Risk:</b> ${r.risk_level} <br>
        <b>Score:</b> ${r.risk_score}
    `;

    // GRAPH
    const ctx = document.getElementById('riskChart');

    if (chart) chart.destroy();

    chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Risk', 'Safe'],
            datasets: [{
                data: [r.risk_score * 100, 100 - (r.risk_score * 100)]
            }]
        }
    });
});