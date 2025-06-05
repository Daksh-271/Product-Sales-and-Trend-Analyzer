const classFeaturesByTarget = {
    "brand_popularity": ["rating", "discount", "price", "id"],
    "price_category": ["original_price", "discount", "rating", "brand"]
};

function updateClassFeatures() {
    const target = document.getElementById("class_target").value;
    const featureDiv = document.getElementById("classFeatureSelection");
    featureDiv.innerHTML = "<label class='form-label'>Choose Feature(s):</label><br>";

    if (!target) return;

    classFeaturesByTarget[target].forEach(f => {
        const checkboxDiv = document.createElement("div");
        checkboxDiv.className = "form-check";
        
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "form-check-input";
        checkbox.name = "class_features";
        checkbox.value = f;
        checkbox.id = `class-feature-${f}`;
        
        const label = document.createElement("label");
        label.className = "form-check-label";
        label.htmlFor = `class-feature-${f}`;
        label.textContent = f.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        checkboxDiv.appendChild(checkbox);
        checkboxDiv.appendChild(label);
        featureDiv.appendChild(checkboxDiv);
    });
    
    document.getElementById("classificationResults").style.display = "none";
}

function runClassification() {
    const target = document.getElementById("class_target").value;
    const features = Array.from(document.querySelectorAll("input[name='class_features']:checked"))
                        .map(cb => cb.value);
    const technique = document.getElementById("classification_technique").value;

    if (!target || features.length === 0) {
        alert("Please select both target and at least one feature");
        return;
    }

    const resultsDiv = document.getElementById("classificationResults");
    resultsDiv.style.display = "block";
    resultsDiv.innerHTML = `
        <div class="text-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Running classification analysis...</p>
        </div>
    `;

    fetch('/run_classification', {
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
                <div id="classMetrics" class="metrics-display"></div>
                <hr>
                <p class="mb-0">The chart below shows how well the model's predictions match the actual values. The confusion matrix helps visualize the classification results.</p>
            </div>
            
            <ul class="nav nav-tabs" id="classChartTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="class-combined-tab" data-bs-toggle="tab" data-bs-target="#class-combined" type="button" role="tab" aria-controls="class-combined" aria-selected="true">Combined View</button>
                </li>
            </ul>
            
            <div class="tab-content" id="classChartTabContent">
                <div class="tab-pane fade show active" id="class-combined" role="tabpanel" aria-labelledby="class-combined-tab">
                    <div id="classificationChart" style="height: 500px; width: 100%; margin-top: 20px;"></div>
                </div>
            </div>
            
            <div id="classPredictionForm" class="prediction-form mt-4">
                <h3 class="mb-3">Predict New Values</h3>
                <div class="row" id="classFeatureInputs">
                    <!-- Dynamically populated -->
                </div>
                <div class="d-grid gap-2 col-md-4 mx-auto mt-3">
                    <button class="btn btn-primary" onclick="predictClassValue()">Predict</button>
                </div>
                <div class="text-center mt-3">
                    <div id="classPredictionResult"></div>
                </div>
            </div>
        `;
        resultsDiv.style.display = "block";

        const metricsDiv = document.getElementById("classMetrics");
        metricsDiv.innerHTML = `
            <div class="metric-card">
                <div>Accuracy</div>
                <div class="metric-value">${(data.accuracy * 100).toFixed(1)}%</div>
                <small>${interpretAccuracy(data.accuracy)}</small>
            </div>
            <div class="metric-card">
                <div>Precision</div>
                <div class="metric-value">${(data.precision * 100).toFixed(1)}%</div>
            </div>
            <div class="metric-card">
                <div>Recall</div>
                <div class="metric-value">${(data.recall * 100).toFixed(1)}%</div>
            </div>
        `;

        renderClassificationChart(data);

        window.selectedClassFeatures = features;
        window.selectedClassTarget = target;
        window.selectedClassTechnique = technique;
        window.classLabels = data.class_labels;
        
        createClassPredictionForm(features, target);
    })
    .catch(error => {
        console.error('Error:', error);
        resultsDiv.innerHTML = `<div class="alert alert-danger">An error occurred: ${error.message}</div>`;
    });
}

function interpretAccuracy(accuracy) {
    if (accuracy >= 0.9) return "Excellent";
    if (accuracy >= 0.8) return "Very good";
    if (accuracy >= 0.7) return "Good";
    if (accuracy >= 0.6) return "Fair";
    return "Needs improvement";
}

function renderClassificationChart(data) {
    const chartOptions = {
        animationEnabled: true,
        theme: "light2",
        title: {
            text: "Classification Results: Correct vs Incorrect Predictions",
            fontFamily: "Segoe UI"
        },
        legend: {
            cursor: "pointer",
            itemclick: toggleDataSeries
        },
        data: [
            {
                type: "column",
                name: "Actual vs Predicted Classes",
                showInLegend: true,
                toolTipContent: "{label}: {y}",
                indexLabel: "{y}",
                indexLabelFontColor: "#FFFFFF",
                indexLabelPlacement: "inside",
                dataPoints: data.confusion_matrix_data
            }
        ]
    };
    
    const chart = new CanvasJS.Chart("classificationChart", chartOptions);
    chart.render();
}

function createClassPredictionForm(features, target) {
    const predictionForm = document.getElementById("classPredictionForm");
    const featureInputs = document.getElementById("classFeatureInputs");
    
    featureInputs.innerHTML = "";
    
    features.forEach(feature => {
        const formGroupDiv = document.createElement("div");
        formGroupDiv.className = "col-md-6 mb-3";
        
        const label = document.createElement("label");
        label.className = "form-label";
        label.htmlFor = `class-input-${feature}`;
        label.textContent = feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        let input;
        
        if (feature === 'brand' && target === 'price_category') {
            input = document.createElement("select");
            input.className = "form-select";
            input.id = `class-input-${feature}`;
            input.name = feature;
            
            const placeholderOption = document.createElement("option");
            placeholderOption.value = "";
            placeholderOption.textContent = `Select ${feature.replace(/_/g, ' ')}`;
            input.appendChild(placeholderOption);
            
            fetch('/get_brands')
                .then(res => res.json())
                .then(data => {
                    if (data.brands) {
                        data.brands.forEach(brand => {
                            const option = document.createElement("option");
                            option.value = brand;
                            option.textContent = brand;
                            input.appendChild(option);
                        });
                    }
                });
        } else {
            input = document.createElement("input");
            input.type = "number";
            input.className = "form-control";
            input.id = `class-input-${feature}`;
            input.name = feature;
            input.required = true;
            input.step = "any";
            input.placeholder = `Enter ${feature.replace(/_/g, ' ')}`;
        }
        
        formGroupDiv.appendChild(label);
        formGroupDiv.appendChild(input);
        featureInputs.appendChild(formGroupDiv);
    });
    
    predictionForm.style.display = "block";
    document.getElementById("classPredictionResult").textContent = "";
}

function predictClassValue() {
    const inputs = {};
    window.selectedClassFeatures.forEach(feature => {
        const inputElement = document.getElementById(`class-input-${feature}`);
        
        if (inputElement.tagName === 'SELECT') {
            inputs[feature] = inputElement.value;
            if (!inputs[feature]) {
                alert(`Please select a value for ${feature}`);
                return;
            }
        } else {
            const value = parseFloat(inputElement.value);
            if (isNaN(value)) {
                alert(`Please enter a valid number for ${feature}`);
                return;
            }
            inputs[feature] = value;
        }
    });
    
    const resultElement = document.getElementById("classPredictionResult");
    resultElement.innerHTML = `
        <div class="spinner-border text-primary spinner-border-sm" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <span class="ms-2">Calculating prediction...</span>
    `;
    
    fetch('/predict_class', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            inputs: inputs,
            target: window.selectedClassTarget,
            technique: window.selectedClassTechnique
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            resultElement.innerHTML = `<div class="text-danger">${data.error}</div>`;
            return;
        }
        
        const targetName = window.selectedClassTarget === 'brand_popularity' ? 'Brand Popularity' : 'Price Category';
        resultElement.innerHTML = `
            <div class="alert alert-success">
                Predicted ${targetName}: <strong>${data.predicted_class}</strong>
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