const clusterColorSchemes = [
    ['#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f', '#edc949', '#af7aa1', '#ff9da7', '#9c755f', '#bab0ab'],
    ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
];

function updateClusteringSection() {
    document.getElementById("clusteringResults").style.display = "none";
}

function runClustering() {
    const groupBy = document.getElementById("cluster_group_by").value;
    const technique = document.getElementById("clustering_technique").value;
    const nClusters = parseInt(document.getElementById("n_clusters").value || "0");
    
    const features = [];
    if (document.getElementById("feature_price").checked) features.push("price");
    if (document.getElementById("feature_discount").checked) features.push("discount");
    if (document.getElementById("feature_rating").checked) features.push("rating");
    
    if (!groupBy) {
        alert("Please select a grouping variable");
        return;
    }
    
    if (features.length < 2) {
        alert("Please select exactly 2 features for clustering");
        return;
    }
    
    if (features.length > 2) {
        alert("Please select exactly 2 features for clustering. 3D visualization is not supported.");
        return;
    }
    
    const resultsDiv = document.getElementById("clusteringResults");
    if (resultsDiv) {
        resultsDiv.style.display = "block";
        resultsDiv.innerHTML = `
            <div class="text-center my-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Running ${technique === 'kmeans' ? 'K-Means' : 'Hierarchical'} clustering analysis...</p>
            </div>
        `;
    } else {
        console.error("Element with ID 'clusteringResults' not found");
        return;
    }
    
    fetch('/run_clustering', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            group_by: groupBy, 
            technique: technique, 
            n_clusters: nClusters,
            features: features
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            resultsDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }
        
        resultsDiv.innerHTML = `
            <div class="alert alert-info mb-4">
                <h4 class="alert-heading">Clustering Results (${data.technique === 'kmeans' ? 'K-Means' : 'Hierarchical'})</h4>
                <div id="clusterMetrics" class="metrics-display"></div>
                <hr>
                <p class="mb-0">The chart below shows how ${data.group_by}s are grouped based on ${data.features.join(', ')} patterns.</p>
                ${data.technique === 'hierarchical' ? '<p class="mt-2"><i>Hierarchical clustering uses Ward linkage method for optimal grouping.</i></p>' : ''}
                ${data.features.length > 2 ? '<p class="mt-2"><i>Displaying 3D visualization. You can rotate and zoom using your mouse.</i></p>' : ''}
            </div>
            
            <ul class="nav nav-tabs" id="clusterChartTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="scatter-plot-tab" data-bs-toggle="tab" data-bs-target="#scatter-plot" type="button" role="tab" aria-controls="scatter-plot" aria-selected="true">Cluster Visualization</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="elbow-method-tab" data-bs-toggle="tab" data-bs-target="#elbow-method" type="button" role="tab" aria-controls="elbow-method" aria-selected="false">Elbow Method</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="silhouette-tab" data-bs-toggle="tab" data-bs-target="#silhouette" type="button" role="tab" aria-controls="silhouette" aria-selected="false">Silhouette Scores</button>
                </li>
            </ul>
            
            <div class="tab-content" id="clusterChartTabContent">
                <div class="tab-pane fade show active" id="scatter-plot" role="tabpanel" aria-labelledby="scatter-plot-tab">
                    <div id="clusteringScatterPlot" style="height: 500px; width: 100%; margin-top: 20px;"></div>
                </div>
                <div class="tab-pane fade" id="elbow-method" role="tabpanel" aria-labelledby="elbow-method-tab">
                    <div id="elbowMethodChart" style="height: 400px; width: 100%; margin-top: 20px;"></div>
                </div>
                <div class="tab-pane fade" id="silhouette" role="tabpanel" aria-labelledby="silhouette-tab">
                    <div id="silhouetteScoreChart" style="height: 400px; width: 100%; margin-top: 20px;"></div>
                </div>
            </div>
        `;
        
        const metricsDiv = document.getElementById("clusterMetrics");
        if (metricsDiv) {
            metricsDiv.innerHTML = `
                <div class="metric-card">
                    <div>Silhouette Score</div>
                    <div class="metric-value">${data.silhouette_score.toFixed(3)}</div>
                    <small>${interpretSilhouetteScore(data.silhouette_score)}</small>
                </div>
                <div class="metric-card">
                    <div>Number of Clusters</div>
                    <div class="metric-value">${data.n_clusters}</div>
                    <small>${data.technique === 'kmeans' ? 'K-Means optimal' : 'Hierarchical (Ward)'}</small>
                </div>
                <div class="metric-card">
                    <div>Grouping</div>
                    <div class="metric-value">${data.group_by.charAt(0).toUpperCase() + data.group_by.slice(1)}</div>
                </div>
            `;
        }
        
        setTimeout(() => {
            render2DClusteringScatterPlot(data);
            
            const elbowTab = document.getElementById("elbow-method-tab");
            const elbowChart = document.getElementById("elbowMethodChart");
            
            if (data.technique === 'kmeans' && data.elbow_data && data.elbow_data.length > 0) {
                if (elbowTab) elbowTab.style.display = "";
                if (elbowChart) renderElbowMethodChart(data.elbow_data);
            } else {
                if (elbowTab) elbowTab.style.display = "none";
                if (elbowChart) {
                    elbowChart.innerHTML = `
                        <div class="alert alert-info mt-3">
                            Elbow method is only applicable to K-Means clustering.<br>
                            Hierarchical clustering uses different optimization criteria.
                        </div>
                    `;
                }
            }
            
            const silhouetteTab = document.getElementById("silhouette-tab");
            const silhouetteChart = document.getElementById("silhouetteScoreChart");
            
            if (data.silhouette_data && data.silhouette_data.length > 0) {
                if (silhouetteTab) silhouetteTab.style.display = "";
                if (silhouetteChart) renderSilhouetteScoreChart(data.silhouette_data, data.technique);
            } else {
                if (silhouetteTab) silhouetteTab.style.display = "none";
            }
        }, 100); 
    })
    .catch(error => {
        console.error('Error:', error);
        if (resultsDiv) {
            resultsDiv.innerHTML = `<div class="alert alert-danger">An error occurred: ${error.message}</div>`;
        }
    });
}

function validateFeatureSelection() {
    const featurePrice = document.getElementById("feature_price");
    const featureDiscount = document.getElementById("feature_discount");
    const featureRating = document.getElementById("feature_rating");
    
    let selectedCount = 0;
    if (featurePrice && featurePrice.checked) selectedCount++;
    if (featureDiscount && featureDiscount.checked) selectedCount++;
    if (featureRating && featureRating.checked) selectedCount++;
    
    let warningElement = document.getElementById("feature-warning");
    if (!warningElement) {
        warningElement = document.createElement("div");
        warningElement.id = "feature-warning";
        warningElement.className = "mt-2";
        
        const featureContainer = document.querySelector(".feature-selection") || 
                               document.getElementById("feature_price").closest(".form-group") ||
                               document.getElementById("feature_price").parentNode;
        
        if (featureContainer) {
            featureContainer.appendChild(warningElement);
        }
    }
    
    if (selectedCount > 2 && selectedCount < 2) {
        warningElement.innerHTML = `
            <div class="alert alert-info py-2 small">
                <i class="fas fa-info-circle"></i> 
                Please select at least 2 features for clustering.
            </div>
        `;
    }
    else {
        warningElement.innerHTML = ""; 
    }
    
    const runButton = document.querySelector("button[onclick='runClustering()']");
    if (runButton) {
        runButton.disabled = (selectedCount < 2);
    }
    
    return selectedCount;
}

function setupFeatureValidation() {
    const features = ["feature_price", "feature_discount", "feature_rating"];
    
    features.forEach(featureId => {
        const element = document.getElementById(featureId);
        if (element) {
            element.addEventListener("change", validateFeatureSelection);
        }
    });
    
    validateFeatureSelection();
}

document.addEventListener('DOMContentLoaded', function() {
    setupFeatureValidation();
});

function interpretSilhouetteScore(score) {
    if (score >= 0.7) return "Excellent separation";
    if (score >= 0.5) return "Good separation";
    if (score >= 0.3) return "Reasonable separation";
    if (score >= 0.0) return "Weak separation";
    return "Poor clustering";
}

function render2DClusteringScatterPlot(data) {
    const chartContainer = document.getElementById("clusteringScatterPlot");
    if (!chartContainer) {
        console.error("Element with ID 'clusteringScatterPlot' not found");
        return;
    }
    
    const scatterData = [];
    const colorScheme = clusterColorSchemes[0];
    
    const xFeature = data.features[0];
    const yFeature = data.features[1];
    
    const clusterGroups = {};
    
    data.scatter_data.forEach(point => {
        if (!clusterGroups[point.cluster]) {
            clusterGroups[point.cluster] = [];
        }
        clusterGroups[point.cluster].push({
            x: point[xFeature],
            y: point[yFeature],
            name: point.name,
            markerSize: 8,  
            markerColor: colorScheme[point.cluster % colorScheme.length],
            toolTipContent: `${point.name}<br/>${xFeature}: ${point[xFeature].toFixed(2)}<br/>${yFeature}: ${point[yFeature].toFixed(2)}`
        });
    });
    
    if (data.centroids && data.centroids.length > 0) {
        data.centroids.forEach(centroid => {
            const clusterColor = colorScheme[centroid.cluster % colorScheme.length];
            
            scatterData.push({
                type: "scatter",
                name: `Cluster ${centroid.cluster + 1}`,
                showInLegend: true,
                markerType: "cross",
                markerSize: 15,  
                markerColor: clusterColor,
                dataPoints: [{
                    x: centroid[xFeature],
                    y: centroid[yFeature],
                    toolTipContent: `Centroid ${centroid.cluster + 1}<br/>${xFeature}: ${centroid[xFeature].toFixed(2)}<br/>${yFeature}: ${centroid[yFeature].toFixed(2)}`
                }]
            });
        });
    }
    
    Object.keys(clusterGroups).forEach(cluster => {
        const clusterColor = colorScheme[parseInt(cluster) % colorScheme.length];
        
        scatterData.push({
            type: "scatter",
            name: `Cluster ${parseInt(cluster) + 1}`,
            showInLegend: true,
            markerSize: 8,
            color: clusterColor,
            dataPoints: clusterGroups[cluster]
        });
    });
    
    try {
        const chart = new CanvasJS.Chart("clusteringScatterPlot", {
            animationEnabled: true,
            theme: "light2",
            title: {
                text: `${data.technique === 'kmeans' ? 'K-Means' : 'Hierarchical'} Clustering by ${data.group_by}`,
                fontFamily: "Segoe UI"
            },
            axisX: {
                title: xFeature.charAt(0).toUpperCase() + xFeature.slice(1),
                titleFontFamily: "Segoe UI",
                crosshair: {
                    enabled: true
                }
            },
            axisY: {
                title: yFeature.charAt(0).toUpperCase() + yFeature.slice(1),
                titleFontFamily: "Segoe UI",
                crosshair: {
                    enabled: true
                }
            },
            legend: {
                cursor: "pointer",
                verticalAlign: "bottom",
                horizontalAlign: "center",
                dockInsidePlotArea: false,
                itemclick: toggleDataSeries
            },
            data: scatterData
        });
        
        chart.render();
    } catch (error) {
        console.error("Error rendering 2D chart:", error);
        chartContainer.innerHTML = `<div class="alert alert-danger">Error rendering chart: ${error.message}</div>`;
    }
}

function renderElbowMethodChart(elbowData) {
    const chartContainer = document.getElementById("elbowMethodChart");
    if (!chartContainer) {
        console.error("Element with ID 'elbowMethodChart' not found");
        return;
    }
    
    try {
        const chart = new CanvasJS.Chart("elbowMethodChart", {
            animationEnabled: true,
            theme: "light2",
            title: {
                text: "Elbow Method for Optimal Clusters (K-Means)",
                fontFamily: "Segoe UI"
            },
            axisX: {
                title: "Number of Clusters",
                titleFontFamily: "Segoe UI",
                interval: 1
            },
            axisY: {
                title: "Inertia (Within-Cluster Sum of Squares)",
                titleFontFamily: "Segoe UI"
            },
            data: [{
                type: "line",
                markerSize: 10,
                xValueFormatString: "#",
                showInLegend: false,
                dataPoints: elbowData
            }]
        });
        
        chart.render();
    } catch (error) {
        console.error("Error rendering elbow chart:", error);
        chartContainer.innerHTML = `<div class="alert alert-danger">Error rendering chart: ${error.message}</div>`;
    }
}

function renderSilhouetteScoreChart(silhouetteData, technique) {
    const chartContainer = document.getElementById("silhouetteScoreChart");
    if (!chartContainer) {
        console.error("Element with ID 'silhouetteScoreChart' not found");
        return;
    }
    
    try {
        const chart = new CanvasJS.Chart("silhouetteScoreChart", {
            animationEnabled: true,
            theme: "light2",
            title: {
                text: `Silhouette Scores by Number of Clusters (${technique === 'kmeans' ? 'K-Means' : 'Hierarchical'})`,
                fontFamily: "Segoe UI"
            },
            axisX: {
                title: "Number of Clusters",
                titleFontFamily: "Segoe UI",
                interval: 1
            },
            axisY: {
                title: "Silhouette Score",
                titleFontFamily: "Segoe UI",
                minimum: 0,
                maximum: 1
            },
            data: [{
                type: "line",
                markerSize: 10,
                xValueFormatString: "#",
                yValueFormatString: "0.000",
                showInLegend: false,
                dataPoints: silhouetteData
            }]
        });
        
        chart.render();
    } catch (error) {
        console.error("Error rendering silhouette chart:", error);
        chartContainer.innerHTML = `<div class="alert alert-danger">Error rendering chart: ${error.message}</div>`;
    }
}

function toggleDataSeries(e) {
    if (typeof(e.dataSeries.visible) === "undefined" || e.dataSeries.visible) {
        e.dataSeries.visible = false;
    } else {
        e.dataSeries.visible = true;
    }
    e.chart.render();
}