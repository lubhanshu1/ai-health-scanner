const API_URL = "https://ai-health-backend-g329.onrender.com/predict-simple";

document.getElementById("healthForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const data = {
        age: parseFloat(document.getElementById("age").value),
        glucose: parseFloat(document.getElementById("glucose").value),
        bp: parseFloat(document.getElementById("bp").value),
        bmi: parseFloat(document.getElementById("bmi").value)
    };

    document.getElementById("result").innerHTML = "⏳ Predicting...";

    try {
        const res = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await res.json();

        document.getElementById("result").innerHTML =
            "✅ Prediction: " + JSON.stringify(result);

    } catch (error) {
        document.getElementById("result").innerHTML =
            "❌ Error connecting to backend";
    }
});