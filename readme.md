# Data Analysis Dashboard

A web application for automated data cleaning, profiling, visualization, outlier detection, clustering, and insights generation.

Built using Flask, Plotly.js, Bootstrap 5, and Vanilla JavaScript.

## Features

- Upload .csv or .xlsx datasets
- Automated data cleaning (missing values handling, datetime parsing)
- Dataset profiling (summary statistics, column-level insights, missing values report)
- Outlier detection (Z-Score, IQR, Isolation Forest)
- Correlation analysis with heatmaps
- Visualizations (histograms, bar charts, scatter plots)
- K-Means clustering with dynamic k-selection and PCA visualization
- Key insights based on dataset analysis
- Responsive UI using Bootstrap 5 and Plotly.js

## Tech Stack

- Backend: Python, Flask, Pandas, Scikit-learn, Plotly
- Frontend: HTML, CSS (Bootstrap 5), JavaScript (Vanilla)
- Libraries: chardet, openpyxl, xlrd, pyarrow

## Project Structure
your-project-folder/
├── app.py
├── README.md
├── uploads/
│   └── (uploaded files are stored here temporarily)
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── styles.css
    └── js/
        └── main.js



