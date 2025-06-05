const allFeatures = ["price", "original_price", "discount", "rating"];

function updateFeatures() {
    const target = document.getElementById("target").value;
    const featureDiv = document.getElementById("featureSelection");
    featureDiv.innerHTML = "<label class='form-label'>Choose Feature(s):</label><br>";

    allFeatures.forEach(f => {
        if (f !== target) {
            const checkboxDiv = document.createElement("div");
            checkboxDiv.className = "form-check";

            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "form-check-input";
            checkbox.name = "features";
            checkbox.value = f;
            checkbox.id = `feature-${f}`;

            const label = document.createElement("label");
            label.className = "form-check-label";
            label.htmlFor = `feature-${f}`;
            label.textContent = f.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

            checkboxDiv.appendChild(checkbox);
            checkboxDiv.appendChild(label);
            featureDiv.appendChild(checkboxDiv);
        }
    });

    document.getElementById("regressionResults").style.display = "none";
}

function runRegression() {
    const target = document.getElementById("target").value;
    const features = Array.from(document.querySelectorAll("input[name='features']:checked"))
                            .map(cb => cb.value);
    const technique = document.getElementById("regression_technique").value;

    if (!target || features.length === 0) {
        alert("Please select both target and at least one feature");
        return;
    }

    const resultsDiv = document.getElementById("regressionResults");
    resultsDiv.style.display = "block";
    resultsDiv.innerHTML = `
        <div class="text-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Running regression analysis...</p>
        </div>
    `;

    fetch('/run_regression', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target, features, technique })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            resultsDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }

        resultsDiv.innerHTML = `
            <div class="alert alert-info mb-4">
                <h4 class="alert-heading">Model Performance</h4>
                <div id="metrics" class="metrics-display"></div>
                <hr>
                <p class="mb-0">The chart below shows how well the model's predictions match the actual values. Points closer to the diagonal line indicate better predictions.</p>
            </div>

            <ul class="nav nav-tabs" id="chartTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="combined-tab" data-bs-toggle="tab" data-bs-target="#combined" type="button" role="tab" aria-controls="combined" aria-selected="true">Combined View</button>
                </li>
            </ul>

            <div class="tab-content" id="chartTabContent">
                <div class="tab-pane fade show active" id="combined" role="tabpanel" aria-labelledby="combined-tab">
                    <div id="regressionChart" style="height: 500px; width: 100%; margin-top: 20px;"></div>
                </div>
            </div>

            <div id="predictionForm" class="prediction-form mt-4">
                <h3 class="mb-3">Predict New Values</h3>
                <div class="row" id="featureInputs">
                    <!-- Dynamically populated -->
                </div>
                <div class="d-grid gap-2 col-md-4 mx-auto mt-3">
                    <button class="btn btn-primary" onclick="predictValue()">Predict</button>
                </div>
                <div class="text-center mt-3">
                    <div id="predictionResult"></div>
                </div>
            </div>
        `;
        resultsDiv.style.display = "block";

        const metricsDiv = document.getElementById("metrics");
        metricsDiv.innerHTML = `
            <div class="metric-card">
                <div>R² Score</div>
                <div class="metric-value">${data.r2.toFixed(3)}</div>
                <small>${interpretR2(data.r2)}</small>
            </div>
        `;

        renderRegressionChart(data);

        window.selectedFeatures = features;
        window.selectedTarget = target;
        window.selectedTechnique = technique;

        createPredictionForm(features, target);
    })
    .catch(error => {
        console.error('Error:', error);
        resultsDiv.innerHTML = `<div class="alert alert-danger">An error occurred: ${error.message}</div>`;
    });
}

function renderRegressionChart(data) {
    const chart = new CanvasJS.Chart("regressionChart", {
        animationEnabled: true,
        theme: "light2",
        title: { 
            text: "Regression Analysis: Actual vs Predicted Values",
            fontFamily: "Segoe UI"
        },
        axisY: { 
            title: "Actual Values",
            gridColor: "#e0e0e0"
        },
        axisX: {
            title: "Predicted Values",
            gridColor: "#e0e0e0"
        },
        legend: {
            cursor: "pointer",
            itemclick: toggleDataSeries
        },
        data: [
            {
                type: "scatter",
                name: "Training Data",
                showInLegend: true,
                markerType: "circle",
                markerSize: 8,
                color: "#4CAF50",
                toolTipContent: "Actual: {y}, Predicted: {x}",
                dataPoints: data.train_actual.map((y, i) => ({ 
                    x: data.train_pred[i], 
                    y: y 
                }))
            },
            {
                type: "scatter",
                name: "Test Data",
                showInLegend: true,
                markerType: "triangle",
                markerSize: 10,
                color: "#0077b6",
                toolTipContent: "Actual: {y}, Predicted: {x}",
                dataPoints: data.test_actual.map((y, i) => ({ 
                    x: data.test_pred[i],
                    y: y 
                }))
            },
            {
                type: "line",
                name: "Perfect Prediction Line",
                showInLegend: true,
                lineDashType: "dash",
                color: "#563d7c",
                markerType: "none",
                dataPoints: (function() {
                    const allValues = [...data.test_actual, ...data.test_pred, ...data.train_actual, ...data.train_pred];
                    const min = Math.min(...allValues);
                    const max = Math.max(...allValues);
                    return [
                        { x: min, y: min },
                        { x: max, y: max }
                    ];
                })()
            }
        ]
    });
    chart.render();
}

function interpretR2(r2) {
    if (r2 >= 0.8) return "Excellent fit";
    if (r2 >= 0.6) return "Good fit";
    if (r2 >= 0.4) return "Moderate fit";
    if (r2 >= 0.2) return "Weak fit";
    return "Poor fit";
}

function createPredictionForm(features, target) {
    const predictionForm = document.getElementById("predictionForm");
    const featureInputs = document.getElementById("featureInputs");
    
    featureInputs.innerHTML = "";
    
    features.forEach(feature => {
        const formGroupDiv = document.createElement("div");
        formGroupDiv.className = "col-md-6 mb-3";
        
        const label = document.createElement("label");
        label.className = "form-label";
        label.htmlFor = `input-${feature}`;
        label.textContent = feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        const input = document.createElement("input");
        input.type = "number";
        input.className = "form-control";
        input.id = `input-${feature}`;
        input.name = feature;
        input.required = true;
        input.step = "any";
        input.placeholder = `Enter ${feature.replace(/_/g, ' ')}`;
        
        formGroupDiv.appendChild(label);
        formGroupDiv.appendChild(input);
        featureInputs.appendChild(formGroupDiv);
    });
    
    predictionForm.style.display = "block";
    document.getElementById("predictionResult").textContent = "";
}

function predictValue() {
    const inputs = {};
    window.selectedFeatures.forEach(feature => {
        const value = parseFloat(document.getElementById(`input-${feature}`).value);
        if (isNaN(value)) {
            alert(`Please enter a valid number for ${feature}`);
            return;
        }
        inputs[feature] = value;
    });
    
    const resultElement = document.getElementById("predictionResult");
    resultElement.innerHTML = `
        <div class="spinner-border text-primary spinner-border-sm" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <span class="ms-2">Calculating prediction...</span>
    `;
    
    fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            inputs: inputs,
            target: window.selectedTarget,
            technique: window.selectedTechnique
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            resultElement.innerHTML = `<div class="text-danger">${data.error}</div>`;
            return;
        }
        
        const targetName = window.selectedTarget.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        resultElement.innerHTML = `
            <div class="alert alert-success">
                Predicted ${targetName}: <strong>${data.predicted.toFixed(2)}</strong>
            </div>
        `;
    })
    .catch(error => {
        console.error('Error:', error);
        resultElement.innerHTML = `<div class="text-danger">An error occurred during prediction</div>`;
    });
}

function toggleDataSeries(e) {
    if (typeof(e.dataSeries.visible) === "undefined" || e.dataSeries.visible) {
        e.dataSeries.visible = false;
    } else {
        e.dataSeries.visible = true;
    }
    e.chart.render();
}