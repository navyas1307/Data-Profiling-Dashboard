// main.js - Client-side JavaScript for Data Analysis Dashboard

document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file');
    const loadingIndicator = document.getElementById('loading');
    const analysisResults = document.getElementById('analysis-results');
    const columnFilterButtons = document.querySelectorAll('.filter-columns');
    
    // Add event listeners
    uploadForm.addEventListener('submit', handleFormSubmit);
    columnFilterButtons.forEach(button => {
        button.addEventListener('click', handleColumnFilter);
    });
    
    // Handle form submission
    async function handleFormSubmit(event) {
        event.preventDefault();
        
        // Validate file input
        const file = fileInput.files[0];
        if (!file) {
            showAlert('Please select a file to upload.', 'danger');
            return;
        }
        
        const fileExt = file.name.split('.').pop().toLowerCase();
        if (!['csv', 'xlsx', 'xls'].includes(fileExt)) {
            showAlert('Please select a valid Excel or CSV file.', 'danger');
            return;
        }
        
        // Show loading indicator
        loadingIndicator.classList.remove('d-none');
        analysisResults.classList.add('d-none');
        
        // Prepare form data
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            // Send request to server
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            // Hide loading indicator
            loadingIndicator.classList.add('d-none');
            
            // Check for error
            if (data.error) {
                showAlert(`Error: ${data.error}`, 'danger');
                return;
            }
            
            // Process and display results
            displayResults(data);
            analysisResults.classList.remove('d-none');
            
            // Activate Bootstrap tooltips
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
            
        } catch (error) {
            loadingIndicator.classList.add('d-none');
            showAlert(`Error: ${error.message || 'Failed to process data'}`, 'danger');
        }
    }
    
    // Display analysis results
    function displayResults(data) {
        // Process each section of results
        if (data.data_profile) {
            displayDataProfile(data.data_profile);
        }
        
        if (data.insights) {
            displayInsights(data.insights);
        }
        
        if (data.visualizations) {
            displayVisualizations(data.visualizations);
        }
        
        if (data.correlations) {
            displayCorrelations(data.correlations);
        }
        
        if (data.outliers) {
            displayOutliers(data.outliers);
        }
        
        if (data.cluster_analysis) {
            displayClusters(data.cluster_analysis);
        } else {
            // Hide clusters tab if no cluster analysis
            document.getElementById('clusters-tab').classList.add('d-none');
        }
    }
    
    // Display data profile information
    function displayDataProfile(profile) {
        // Dataset summary
        const summaryHTML = `
            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <h6 class="fw-bold">Dataset Size</h6>
                        <p><i class="fas fa-table me-2 text-primary"></i> ${profile.row_count} rows × ${profile.column_count} columns</p>
                        <p><i class="fas fa-database me-2 text-primary"></i> Memory usage: ${profile.memory_usage.toFixed(2)} MB</p>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <h6 class="fw-bold">Column Types</h6>
                        <p><i class="fas fa-hashtag me-2 text-primary"></i> Numeric: ${profile.column_types.numeric}</p>
                        <p><i class="fas fa-font me-2 text-primary"></i> Categorical: ${profile.column_types.categorical}</p>
                        <p><i class="fas fa-calendar me-2 text-primary"></i> Datetime: ${profile.column_types.datetime}</p>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col-12">
                    <h6 class="fw-bold">Data Quality</h6>
                    <p><i class="fas fa-copy me-2 ${profile.duplicate_rows > 0 ? 'text-warning' : 'text-success'}"></i> 
                       Duplicate rows: ${profile.duplicate_rows} (${(profile.duplicate_rows / profile.row_count * 100).toFixed(2)}%)</p>
                </div>
            </div>
        `;
        document.getElementById('data-profile-summary').innerHTML = summaryHTML;
        
        // Missing values summary
        let missingValuesHTML = '';
        const missingVals = Object.entries(profile.missing_values).filter(([_, count]) => count > 0);
        
        if (missingVals.length > 0) {
            missingValuesHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${missingVals.length} out of ${profile.column_count} columns have missing values.
                </div>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Column</th>
                                <th>Missing Count</th>
                                <th>Missing %</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${missingVals.map(([col, count]) => `
                                <tr>
                                    <td>${col}</td>
                                    <td>${count}</td>
                                    <td>${(count / profile.row_count * 100).toFixed(2)}%</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            missingValuesHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    No missing values found in the dataset. Good data quality!
                </div>
            `;
        }
        document.getElementById('missing-values-summary').innerHTML = missingValuesHTML;
        
        // Column details table
        const tableBody = document.getElementById('column-details-table').querySelector('tbody');
        tableBody.innerHTML = '';
        
        Object.entries(profile.column_stats).forEach(([colName, colStats]) => {
            const isNumeric = colStats.type.includes('int') || colStats.type.includes('float');
            const isCategorical = colStats.type.includes('object');
            const isDatetime = colStats.type.includes('datetime');
            
            let colType = 'other';
            if (isNumeric) colType = 'numeric';
            else if (isCategorical) colType = 'categorical';
            else if (isDatetime) colType = 'datetime';
            
            let statsHTML = '';
            if (isNumeric) {
                statsHTML = `
                    <div>Min: ${colStats.min !== null ? colStats.min.toLocaleString() : 'N/A'}</div>
                    <div>Max: ${colStats.max !== null ? colStats.max.toLocaleString() : 'N/A'}</div>
                    <div>Mean: ${colStats.mean !== null ? colStats.mean.toLocaleString(undefined, {maximumFractionDigits: 2}) : 'N/A'}</div>
                    <div>Median: ${colStats.median !== null ? colStats.median.toLocaleString(undefined, {maximumFractionDigits: 2}) : 'N/A'}</div>
                    <div>Std Dev: ${colStats.std !== null ? colStats.std.toLocaleString(undefined, {maximumFractionDigits: 2}) : 'N/A'}</div>
                `;
            } else if (isCategorical && colStats.top_values) {
                const topValues = Object.entries(colStats.top_values)
                    .slice(0, 3)
                    .map(([val, count]) => `${val} (${count})`)
                    .join(', ');
                
                statsHTML = `
                    <div>Top values: ${topValues}</div>
                `;
            }
            
            const row = document.createElement('tr');
            row.dataset.columnType = colType;
            row.innerHTML = `
                <td>${colName}</td>
                <td><span class="badge ${getBadgeColorForType(colStats.type)}">${colStats.type}</span></td>
                <td>${(colStats.missing_rate * 100).toFixed(2)}%</td>
                <td>${colStats.unique_values}</td>
                <td>${statsHTML}</td>
            `;
            tableBody.appendChild(row);
        });
    }
    
    // Display insights
    function displayInsights(insights) {
        const insightsContainer = document.getElementById('insights-container');
        insightsContainer.innerHTML = '';
        
        if (insights.length === 0) {
            insightsContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No specific insights were generated for this dataset.
                </div>
            `;
            return;
        }
        
        insights.forEach(insight => {
            const insightElement = document.createElement('div');
            insightElement.className = `alert alert-${insight.type} mb-3`;
            
            let insightHTML = `
                <div class="d-flex">
                    <div class="me-3">
                        ${getInsightIcon(insight.type)}
                    </div>
                    <div>
                        <p class="mb-0">${insight.message}</p>
            `;
            
            // Add details if available
            if (insight.details) {
                insightHTML += `
                    <div class="mt-2">
                        <div class="accordion" id="insightAccordion${Math.random().toString(36).substr(2, 9)}">
                            <div class="accordion-item">
                                <h2 class="accordion-header">
                                    <button class="accordion-button collapsed p-2" type="button" data-bs-toggle="collapse" 
                                        data-bs-target="#collapse${Math.random().toString(36).substr(2, 9)}">
                                        View Details
                                    </button>
                                </h2>
                                <div id="collapse${Math.random().toString(36).substr(2, 9)}" class="accordion-collapse collapse">
                                    <div class="accordion-body">
                                        ${formatInsightDetails(insight.details)}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            insightHTML += `
                    </div>
                </div>
            `;
            
            insightElement.innerHTML = insightHTML;
            insightsContainer.appendChild(insightElement);
        });
    }
    
    // Display visualizations
    function displayVisualizations(visualizations) {
        const container = document.getElementById('visualizations-container');
        container.innerHTML = '';
    
        if (!visualizations || visualizations.length === 0) {
            container.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        No visualizations generated. Ensure your data has numeric columns.
                    </div>
                </div>
            `;
            return;
        }
    
        visualizations.forEach((viz, index) => {
            const colDiv = document.createElement('div');
            colDiv.className = 'col-md-6 mb-4';
            
            // Handle error messages from backend
            if (viz.message) {
                colDiv.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        ${viz.message}
                    </div>
                `;
                container.appendChild(colDiv);
                return;
            }
    
            const vizId = `viz-${index}`;
            colDiv.innerHTML = `
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="card-title mb-0">${viz.title}</h5>
                    </div>
                    <div class="card-body">
                        <div id="${vizId}" class="plotly-chart"></div>
                    </div>
                </div>
            `;
            
            container.appendChild(colDiv);
            
            // Render Plotly from JSON
            if (viz.plotly_figure) {
                try {
                    const figure = JSON.parse(viz.plotly_figure);
                    Plotly.newPlot(vizId, figure.data, figure.layout, {
                        responsive: true,
                        displayModeBar: true
                    });
                } catch (error) {
                    document.getElementById(vizId).innerHTML = `
                        <div class="alert alert-danger">
                            Error rendering chart: ${error.message}
                        </div>
                    `;
                }
            }
        });
    }
    
    // Display correlations
    // Display correlations
    function displayCorrelations(correlations) {
        const heatmapContainer = document.getElementById('correlation-heatmap');
        const tableContainer = document.getElementById('top-correlations-table');
        
        // Validate DOM elements exist
        if (!heatmapContainer || !tableContainer) {
            console.error('Correlation containers not found in DOM');
            return;
        }
        
        // Check if correlations data is available
        if (correlations.message) {
            heatmapContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    ${correlations.message}
                </div>
            `;
            const tbody = tableContainer.querySelector('tbody');
            if (tbody) {
                tbody.innerHTML = `
                    <tr><td colspan="3" class="text-center">Not enough numerical data for correlation analysis</td></tr>
                `;
            }
            return;
        }
        
        // Display correlation heatmap
        // Display correlation heatmap
        if (correlations.heatmap_plotly) {
            try {
                const figure = JSON.parse(correlations.heatmap_plotly);
                Plotly.newPlot('correlation-heatmap', figure.data, figure.layout, {
                    responsive: true,
                    displayModeBar: true,
                    displaylogo: false
                });
            } catch (error) {
                document.getElementById('correlation-heatmap').innerHTML = `
                    <div class="alert alert-danger">Error rendering correlation heatmap: ${error.message}</div>
                `;
            }
        }
            
        
        // Display top correlations table
        const tableBody = document.getElementById('top-correlations-table').querySelector('tbody');
        tableBody.innerHTML = '';
        
        if (correlations.pairs && correlations.pairs.length > 0) {
            correlations.pairs.forEach(pair => {
                const row = document.createElement('tr');
                
                // Determine correlation strength and color
                const corrAbs = Math.abs(pair.correlation);
                let corrClass = '';
                if (corrAbs >= 0.7) corrClass = pair.correlation > 0 ? 'text-success fw-bold' : 'text-danger fw-bold';
                else if (corrAbs >= 0.4) corrClass = pair.correlation > 0 ? 'text-success' : 'text-danger';
                
                row.innerHTML = `
                    <td>${pair.column1}</td>
                    <td>${pair.column2}</td>
                    <td class="${corrClass}">${pair.correlation.toFixed(3)}</td>
                `;
                tableBody.appendChild(row);
            });
        } else {
            tableBody.innerHTML = `
                <tr><td colspan="3" class="text-center">No significant correlations found</td></tr>
            `;
        }
    }
    
    // Display outliers information
    function displayOutliers(outliers) {
        // Outlier summary
        const summaryContainer = document.getElementById('outliers-summary');
        
        let zScoreOutlierCount = 0;
        Object.values(outliers.z_score).forEach(col => {
            zScoreOutlierCount += col.count;
        });
        
        let iqrOutlierCount = 0;
        Object.values(outliers.iqr).forEach(col => {
            iqrOutlierCount += col.count;
        });
        
        const isoForestOutlierCount = outliers.isolation_forest.count || 0;
        
        const summaryHTML = `
            <div class="row text-center">
                <div class="col-md-4">
                    <div class="card bg-light mb-3">
                        <div class="card-body">
                            <h3 class="display-4">${zScoreOutlierCount}</h3>
                            <p class="mb-0">Z-Score Outliers</p>
                            <small class="text-muted">Across ${Object.keys(outliers.z_score).length} columns</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-light mb-3">
                        <div class="card-body">
                            <h3 class="display-4">${iqrOutlierCount}</h3>
                            <p class="mb-0">IQR Outliers</p>
                            <small class="text-muted">Across ${Object.keys(outliers.iqr).length} columns</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-light mb-3">
                        <div class="card-body">
                            <h3 class="display-4">${isoForestOutlierCount}</h3>
                            <p class="mb-0">Isolation Forest Outliers</p>
                            <small class="text-muted">Multivariate analysis</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
        summaryContainer.innerHTML = summaryHTML;
        
        // Z-Score outliers
        const zScoreContainer = document.getElementById('z-score-outliers');
        if (Object.keys(outliers.z_score).length > 0) {
            let zScoreHTML = `
                <div class="alert alert-info mb-3">
                    <i class="fas fa-info-circle me-2"></i>
                    Z-Score method identifies outliers that are more than 3 standard deviations away from the mean.
                </div>
                <div class="accordion" id="zScoreAccordion">
            `;
            
            Object.entries(outliers.z_score).forEach(([column, details], index) => {
                zScoreHTML += `
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button ${index > 0 ? 'collapsed' : ''}" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#zScoreCollapse${index}">
                                ${column} <span class="badge bg-warning text-dark ms-2">${details.count} outliers</span>
                            </button>
                        </h2>
                        <div id="zScoreCollapse${index}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}">
                            <div class="accordion-body">
                                <p>Sample outlier values: ${details.values.map(v => v.toLocaleString(undefined, {maximumFractionDigits: 2})).join(', ')}</p>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            zScoreHTML += '</div>';
            zScoreContainer.innerHTML = zScoreHTML;
        } else {
            zScoreContainer.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    No Z-Score outliers detected in the dataset.
                </div>
            `;
        }
        
        // IQR outliers
        const iqrContainer = document.getElementById('iqr-outliers');
        if (Object.keys(outliers.iqr).length > 0) {
            let iqrHTML = `
                <div class="alert alert-info mb-3">
                    <i class="fas fa-info-circle me-2"></i>
                    IQR method identifies outliers that fall below Q1-1.5×IQR or above Q3+1.5×IQR.
                </div>
                <div class="accordion" id="iqrAccordion">
            `;
            
            Object.entries(outliers.iqr).forEach(([column, details], index) => {
                iqrHTML += `
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button ${index > 0 ? 'collapsed' : ''}" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#iqrCollapse${index}">
                                ${column} <span class="badge bg-warning text-dark ms-2">${details.count} outliers</span>
                            </button>
                        </h2>
                        <div id="iqrCollapse${index}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}">
                            <div class="accordion-body">
                                <p>Bounds: Lower = ${details.bounds.lower.toLocaleString(undefined, {maximumFractionDigits: 2})}, 
                                   Upper = ${details.bounds.upper.toLocaleString(undefined, {maximumFractionDigits: 2})}</p>
                                <p>Sample outlier values: ${details.values.map(v => v.toLocaleString(undefined, {maximumFractionDigits: 2})).join(', ')}</p>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            iqrHTML += '</div>';
            iqrContainer.innerHTML = iqrHTML;
        } else {
            iqrContainer.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    No IQR outliers detected in the dataset.
                </div>
            `;
        }
        
        // Isolation Forest outliers
        const isoForestContainer = document.getElementById('isolation-forest-outliers');
        
        if (outliers.isolation_forest.error) {
            isoForestContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${outliers.isolation_forest.error}
                </div>
            `;
        } else if (outliers.isolation_forest.message) {
            isoForestContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    ${outliers.isolation_forest.message}
                </div>
            `;
        } else {
            isoForestContainer.innerHTML = `
                <div class="alert alert-info mb-3">
                    <i class="fas fa-info-circle me-2"></i>
                    Isolation Forest is a multivariate method that identifies outliers based on how easily they can be isolated.
                </div>
                <div class="card">
                    <div class="card-body">
                        <h6>Detected ${outliers.isolation_forest.count} potential outliers</h6>
                        ${outliers.isolation_forest.count > 0 ? `
                            <p>Outlier score distribution (lower is more anomalous):</p>
                            <div class="row">
                                <div class="col-md-8 offset-md-2">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Percentile</th>
                                                <th>Score</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                <td>10%</td>
                                                <td>${outliers.isolation_forest.score_quantiles['10%'].toFixed(3)}</td>
                                            </tr>
                                            <tr>
                                                <td>25%</td>
                                                <td>${outliers.isolation_forest.score_quantiles['25%'].toFixed(3)}</td>
                                            </tr>
                                            <tr>
                                                <td>50% (Median)</td>
                                                <td>${outliers.isolation_forest.score_quantiles['50%'].toFixed(3)}</td>
                                            </tr>
                                            <tr>
                                                <td>75%</td>
                                                <td>${outliers.isolation_forest.score_quantiles['75%'].toFixed(3)}</td>
                                            </tr>
                                            <tr>
                                                <td>90%</td>
                                                <td>${outliers.isolation_forest.score_quantiles['90%'].toFixed(3)}</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ` : `
                            <div class="alert alert-success">
                                <i class="fas fa-check-circle me-2"></i>
                                No multivariate outliers detected.
                            </div>
                        `}
                    </div>
                </div>
            `;
        }
    }
    
    // Display cluster analysis
    function displayClusters(clusterData) {
        const container = document.getElementById('cluster-analysis-container');
        
        // Validate DOM element exists
        if (!container) {
            console.error('Cluster analysis container not found in DOM');
            return;
        }
        
        container.innerHTML = '';
    
        // Handle error cases first
        if (clusterData.error) {
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-times-circle me-2"></i>
                    Cluster analysis failed: ${clusterData.error}
                </div>
            `;
            return;
        }
    
    
        if (clusterData.message) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    ${clusterData.message}
                </div>
            `;
            return;
        }
    
        // Build cluster analysis UI
        let html = `
            <div class="row">
                <div class="col-md-8 mb-4">
                    <div class="card h-100">
                        <div class="card-header">
                            <h5 class="card-title mb-0">Cluster Visualization</h5>
                        </div>
                        <div class="card-body">
                            <div id="cluster-viz" class="plotly-chart"></div>
                            ${
                                clusterData.pca_variance ? `
                                <div class="mt-2 text-muted small">
                                    PCA Variance Explained: 
                                    PC1 (${(clusterData.pca_variance.pc1 * 100).toFixed(1)}%), 
                                    PC2 (${(clusterData.pca_variance.pc2 * 100).toFixed(1)}%)
                                </div>
                                ` : ''
                            }
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4 mb-4">
                    <div class="card h-100">
                        <div class="card-header">
                            <h5 class="card-title mb-0">Cluster Summary</h5>
                        </div>
                        <div class="card-body">
                            <h6>Optimal Clusters: ${clusterData.optimal_clusters}</h6>
                            <div id="cluster-stats" class="mt-3"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">Elbow Method Analysis</h5>
                        </div>
                        <div class="card-body">
                            <div id="elbow-curve" class="plotly-chart"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    
        container.innerHTML = html;
    
        // Render Cluster Visualization
        if (clusterData.cluster_visualization_plotly) {
            try {
                const figure = JSON.parse(clusterData.cluster_visualization_plotly);
                const vizContainer = document.getElementById('cluster-viz');
                
                if (!vizContainer) {
                    console.error('Cluster visualization container not found');
                    return;
                }
                
                Plotly.newPlot('cluster-viz', figure.data, figure.layout, {
                    responsive: true,
                    displayModeBar: true,
                    scrollZoom: true
                });
            } catch (error) {
                console.error('Cluster visualization error:', error);
                const vizContainer = document.getElementById('cluster-viz');
                if (vizContainer) {
                    vizContainer.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Error rendering cluster visualization: ${error.message}
                        </div>
                    `;
                }
            }
        }
    
        // Render Elbow Curve
        if (clusterData.elbow_curve_plotly) {
            try {
                const figure = JSON.parse(clusterData.elbow_curve_plotly);
                Plotly.newPlot('elbow-curve', figure.data, figure.layout, {
                    responsive: true,
                    displayModeBar: true
                });
            } catch (error) {
                document.getElementById('elbow-curve').innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Error rendering elbow curve: ${error.message}
                    </div>
                `;
            }
        }
    
        // Populate Cluster Statistics
        const clusterStatsContainer = document.getElementById('cluster-stats');
        if (clusterData.cluster_stats) {
            let statsHtml = '<div class="list-group">';
            
            Object.entries(clusterData.cluster_stats).forEach(([clusterName, stats]) => {
                statsHtml += `
                    <div class="list-group-item">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">${clusterName}</h6>
                            <small>${stats.size} records (${stats.percentage}%)</small>
                        </div>
                        <div class="mt-2">
                            <table class="table table-sm table-borderless mb-0">
                                <tbody>
                                    ${Object.entries(stats.mean).map(([col, value]) => `
                                        <tr>
                                            <td>${col}</td>
                                            <td class="text-end">${typeof value === 'number' ? value.toFixed(2) : value}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            });
            
            statsHtml += '</div>';
            clusterStatsContainer.innerHTML = statsHtml;
        } else {
            clusterStatsContainer.innerHTML = `
                <div class="alert alert-warning mb-0">
                    No cluster statistics available
                </div>
            `;
        }
    
        // Add resize handler for responsiveness
        window.addEventListener('resize', () => {
            if (clusterData.cluster_visualization_plotly) {
                Plotly.Plots.resize('cluster-viz');
            }
            if (clusterData.elbow_curve_plotly) {
                Plotly.Plots.resize('elbow-curve');
            }
        });
    }
    // Column filter handler
    function handleColumnFilter(event) {
        const filterValue = event.target.dataset.filter;
        
        // Update active button state
        columnFilterButtons.forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
        
        // Filter table rows
        const tableRows = document.querySelectorAll('#column-details-table tbody tr');
        tableRows.forEach(row => {
            if (filterValue === 'all' || row.dataset.columnType === filterValue) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
    
    // Helper functions
    function showAlert(message, type) {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert at top of main container
        const container = document.querySelector('main.container');
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }
    
    function getBadgeColorForType(type) {
        if (type.includes('int') || type.includes('float')) return 'bg-primary';
        if (type.includes('object')) return 'bg-success';
        if (type.includes('date')) return 'bg-info';
        return 'bg-secondary';
    }
    
    function getInsightIcon(type) {
        switch (type) {
            case 'info':
                return '<i class="fas fa-info-circle fa-2x text-info"></i>';
            case 'warning':
                return '<i class="fas fa-exclamation-triangle fa-2x text-warning"></i>';
            case 'success':
                return '<i class="fas fa-check-circle fa-2x text-success"></i>';
            case 'danger':
                return '<i class="fas fa-times-circle fa-2x text-danger"></i>';
            default:
                return '<i class="fas fa-lightbulb fa-2x text-primary"></i>';
        }
    }
    
    function formatInsightDetails(details) {
        if (Array.isArray(details)) {
            return `<ul class="mb-0">
                ${details.map(item => `<li>${item}</li>`).join('')}
            </ul>`;
        } else if (typeof details === 'object') {
            return `<table class="table table-sm table-striped">
                <tbody>
                    ${Object.entries(details).map(([key, value]) => `
                        <tr>
                            <td class="fw-bold">${key}</td>
                            <td>${value}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
        } else {
            return `<p class="mb-0">${details}</p>`;
        }
    }
    
    // Initialize tooltips and popovers when the document is fully loaded
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Add event listener for export buttons if they exist
    const exportButtons = document.querySelectorAll('.export-data');
    exportButtons.forEach(button => {
        button.addEventListener('click', handleExport);
    });
    
    // Handle data export
    function handleExport(event) {
        const format = event.target.dataset.format;
        // Implementation for export functionality would go here
        console.log(`Export data in ${format} format`);
        
        showAlert(`Exporting data in ${format} format is not implemented in this demo version.`, 'info');
    }
    
    // Add event listeners for any responsive design adjustments
    window.addEventListener('resize', function() {
        // Adjust UI elements based on screen size if needed
        const screenWidth = window.innerWidth;
        
        // Example: Collapse certain panels on smaller screens
        if (screenWidth < 768) {
            // Mobile adjustments if needed
        } else {
            // Desktop adjustments if needed
        }
    });
    
    // Optional: Add keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        // Example: Ctrl+Enter to submit form
        if (event.ctrlKey && event.key === 'Enter' && uploadForm) {
            uploadForm.dispatchEvent(new Event('submit'));
        }
    });
    
    // Optional: Add support for drag and drop file upload
    const dropZone = document.getElementById('upload-form');
    if (dropZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            dropZone.classList.add('highlight');
        }
        
        function unhighlight() {
            dropZone.classList.remove('highlight');
        }
        
        dropZone.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length) {
                fileInput.files = files;
                // Optional: Auto-submit form on drop
                // uploadForm.dispatchEvent(new Event('submit'));
            }
        }
    }
    
    // Add dark mode toggle if it exists in the UI
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleDarkMode);
        
        // Check user preference on page load
        if (localStorage.getItem('darkMode') === 'enabled') {
            document.body.classList.add('dark-mode');
            darkModeToggle.checked = true;
        }
        
        function toggleDarkMode() {
            if (darkModeToggle.checked) {
                document.body.classList.add('dark-mode');
                localStorage.setItem('darkMode', 'enabled');
            } else {
                document.body.classList.remove('dark-mode');
                localStorage.setItem('darkMode', 'disabled');
            }
        }
    }
    
    // Show welcome message or tutorial for first-time users
    if (!localStorage.getItem('visited')) {
        setTimeout(() => {
            showAlert('Welcome to the Data Analysis Dashboard! Upload a CSV or Excel file to get started.', 'info');
            localStorage.setItem('visited', 'true');
        }, 1000);
    }
    
    });
