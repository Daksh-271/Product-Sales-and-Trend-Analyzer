function getChartData() {
    const option = document.getElementById("chartOption").value;

    fetch(`/get_data?type=${option}`)
        .then(response => response.json())
        .then(data => {
            let chartConfig = {
                animationEnabled: true,
                exportEnabled: true,
                theme: "light2",
                title: { 
                    text: option.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                    fontFamily: "Segoe UI",
                    fontSize: 24
                },
                axisY: { 
                    title: "Value",
                    gridColor: "#e0e0e0",
                    lineColor: "#ccc"
                },
                axisX: {
                    gridColor: "#e0e0e0",
                    lineColor: "#ccc"
                },
                legend: {
                    cursor: "pointer",
                    itemclick: toggleDataSeries
                },
                data: []
            };

            switch (option) {
                case "price_diff_category":
                case "price_diff_subcategory":
                    chartConfig.data = [
                        {
                            type: "column",
                            name: "Original Price",
                            showInLegend: true,
                            color: "#563d7c",
                            dataPoints: data.original.map(item => ({ label: item.label, y: item.y }))
                        },
                        {
                            type: "column",
                            name: "Discounted Price",
                            showInLegend: true,
                            color: "#8e79b8",
                            dataPoints: data.discounted.map(item => ({ label: item.label, y: item.y }))
                        }
                    ];
                    break;

                case "product_distribution":
                    chartConfig.data = [{
                        type: "pie",
                        startAngle: 240,
                        indexLabelFontSize: 14,
                        indexLabel: "{label} - {y}",
                        toolTipContent: "<b>{label}:</b> {y} ({percentText})",
                        dataPoints: data.map(item => ({ label: item.label, y: item.y }))
                    }];
                    break;

                case "correlation_features":
                case "discount_vs_rating":
                    chartConfig.axisX = { 
                        title: option === "correlation_features" ? "Price" : "Average Discount",
                        gridColor: "#e0e0e0"
                    };
                    chartConfig.axisY = { 
                        title: "Rating",
                        gridColor: "#e0e0e0"
                    };
                    chartConfig.data = [{
                        type: "scatter",
                        markerSize: 8,
                        color: "#563d7c",
                        toolTipContent: "X: {x}, Y: {y}",
                        dataPoints: data.map(item => ({ x: item.x, y: item.y }))
                    }];
                    break;

                case "top_selling_brands":
                    chartConfig.data = [{
                        type: "column",
                        color: "#563d7c",
                        dataPoints: data.map(item => ({ label: item.label, y: item.y }))
                    }];
                    break;

                case "rating_distribution":
                    chartConfig.data = [{
                        type: "line",
                        markerType: "circle",
                        color: "#563d7c",
                        dataPoints: data.map(item => ({ label: item.label, y: item.y }))
                    }];
                    break;

                case "best_discounted_high_rated":
                    chartConfig.data = [{
                        type: "column",
                        color: "#563d7c",
                        dataPoints: data.map(item => ({ label: item.label, y: item.y }))
                    }];
                    break;
            }

            const chart = new CanvasJS.Chart("chartContainer", chartConfig);
            chart.render();
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