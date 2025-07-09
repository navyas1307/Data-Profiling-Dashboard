from flask import Flask, request, jsonify, render_template, send_from_directory, session
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import chardet
import base64
import json
import os
from datetime import datetime
from sklearn.preprocessing import StandardScaler
import warnings
from werkzeug.utils import secure_filename
warnings.filterwarnings('ignore')

# Plotly imports
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Define blue color scheme
BLUE_PALETTE = {
    'primary': '#0047AB',
    'secondary': '#4682B4',
    'accent': '#00BFFF',
    'light': '#E6F2FF',
    'dark': '#00008B'
}

app = Flask(__name__)
app.secret_key = 'data_analyzer_secret_key'

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        # Handle pandas Timestamp objects
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        # Handle datetime objects
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

app.json_encoder = CustomJSONEncoder

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx', 'xlsm', 'xlsb', 'odf', 'ods', 'odt'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_read_file(file_path):
    """Read files with proper encoding and Excel engine detection"""
    try:
        if file_path.endswith('.csv'):
            with open(file_path, 'rb') as f:
                result = chardet.detect(f.read())
            encoding = result['encoding'] or 'utf-8'
            
            return pd.read_csv(
                file_path,
                encoding=encoding,
                engine='python',
                on_bad_lines='skip',
                parse_dates=True,
                dtype_backend='pyarrow'
            )
        else:
            engine = 'openpyxl' if file_path.endswith(('.xlsx', '.xlsm')) else 'xlrd'
            return pd.read_excel(
                file_path,
                engine=engine,
                # Removed the infer_datetime_format parameter
                parse_dates=True,
                dtype_backend='pyarrow'
            )
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")

def clean_dataframe(df):
    """Comprehensive data cleaning and preprocessing"""
    df = df.replace([np.inf, -np.inf], np.nan)
    
    # Convert object columns to string
    obj_cols = df.select_dtypes(include=['object']).columns
    df[obj_cols] = df[obj_cols].astype('string')
    
    # Convert datetime columns
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass
    
    # Handle missing values
    num_cols = df.select_dtypes(include=np.number).columns
    df[num_cols] = df[num_cols].apply(lambda x: x.fillna(x.median()))
    
    cat_cols = df.select_dtypes(include=['string', 'category']).columns
    for col in cat_cols:
        mode_val = df[col].mode()[0] if not df[col].mode().empty else 'Unknown'
        df[col] = df[col].fillna(mode_val)
    
    return df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'})
    
    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        file.save(file_path)
        
        df = safe_read_file(file_path)
        df = clean_dataframe(df)
        
        cleaned_path = file_path + '_cleaned.parquet'
        df.to_parquet(cleaned_path)
        session['current_file_path'] = cleaned_path
        
        result = analyze_data(df)
        result['data_preview'] = {
            'columns': df.columns.tolist(),
            'head': df.head(10).replace({np.nan: None}).to_dict('records'),
            'total_rows': len(df)
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/get_data', methods=['GET'])
def get_data():
    if 'current_file_path' not in session:
        return jsonify({'error': 'No file uploaded'})
    
    file_path = session['current_file_path']
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'})
    
    try:
        df = pd.read_parquet(file_path)
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, len(df))
        
        # Convert datetime columns to string before serialization
        df_copy = df.copy()
        for col in df_copy.select_dtypes(include=['datetime64']).columns:
            df_copy[col] = df_copy[col].astype(str)
        
        return jsonify({
            'columns': df.columns.tolist(),
            'data': df_copy.iloc[start_idx:end_idx].replace({np.nan: None}).to_dict('records'),
            'total_rows': len(df),
            'total_pages': (len(df) + page_size - 1) // page_size,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)})

def analyze_data(df):
    """Main analysis function"""
    result = {
        'data_profile': generate_data_profile(df),
        'outliers': detect_outliers(df),
        'correlations': analyze_correlations(df),
        'visualizations': generate_visualizations(df),
        'insights': generate_insights(df),
        'cluster_analysis': perform_clustering(df) if len(df) > 10 else {'message': 'Not enough data for clustering analysis'}

    }
    return result

def generate_data_profile(df):
    """Generate dataset profile"""
    numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_columns = df.select_dtypes(include=['string', 'category']).columns.tolist()
    datetime_columns = df.select_dtypes(include=['datetime64']).columns.tolist()
    
    profile = {
        'row_count': len(df),
        'column_count': len(df.columns),
        'column_types': {
            'numeric': len(numeric_columns),
            'categorical': len(categorical_columns),
            'datetime': len(datetime_columns)
        },
        'missing_values': {k: int(v) for k, v in df.isna().sum().items()},
        'duplicate_rows': int(df.duplicated().sum()),
        'memory_usage': df.memory_usage(deep=True).sum() / (1024 * 1024)
    }
    
    column_stats = {}
    for col in df.columns:
        col_stats = {'type': str(df[col].dtype)}
        
        if df[col].dtype.kind in 'iufc':
            col_stats.update({
                'min': float(df[col].min()) if not pd.isna(df[col].min()) else None,
                'max': float(df[col].max()) if not pd.isna(df[col].max()) else None,
                'mean': float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                'median': float(df[col].median()) if not pd.isna(df[col].median()) else None,
                'std': float(df[col].std()) if not pd.isna(df[col].std()) else None,
                'unique_values': int(df[col].nunique()),
                'missing_rate': float(df[col].isna().mean())
            })
        else:
            col_stats.update({
                'unique_values': int(df[col].nunique()),
                'top_values': {str(k): int(v) for k, v in df[col].value_counts().head(5).to_dict().items()},
                'missing_rate': float(df[col].isna().mean())
            })
            
        column_stats[col] = col_stats
    
    profile['column_stats'] = column_stats
    return profile

def detect_outliers(df):
    """Outlier detection implementation"""
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty or numeric_df.shape[1] < 1:
        return {'message': 'No numeric columns available for outlier detection'}
    
    numeric_df = numeric_df.fillna(numeric_df.median())
    outliers = {}
    
    # Z-score method
    z_score_outliers = {}
    for col in numeric_df.columns:
        z_scores = np.abs((numeric_df[col] - numeric_df[col].mean()) / numeric_df[col].std())
        z_outliers = df.index[z_scores > 3].tolist()
        if z_outliers:
            z_score_outliers[col] = {
                'count': len(z_outliers),
                'indices': z_outliers[:10],
                'values': numeric_df.loc[z_outliers, col].tolist()[:10]
            }
    
    # IQR method
    iqr_outliers = {}
    for col in numeric_df.columns:
        Q1 = numeric_df[col].quantile(0.25)
        Q3 = numeric_df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = float(Q1 - 1.5 * IQR)
        upper_bound = float(Q3 + 1.5 * IQR)
       
        outliers_mask = (numeric_df[col] < lower_bound) | (numeric_df[col] > upper_bound)
        iqr_outlier_indices = df.index[outliers_mask].tolist()
        
        if iqr_outlier_indices:
            iqr_outliers[col] = {
                'count': len(iqr_outlier_indices),
                'indices': iqr_outlier_indices[:10],
                'values': [float(v) for v in numeric_df.loc[iqr_outlier_indices, col].tolist()[:10]],
                'bounds': {'lower': lower_bound, 'upper': upper_bound}
            }
    
    # Isolation Forest
    iso_forest = None
    if numeric_df.shape[1] >= 2 and len(numeric_df) > 10:
        try:
            iso_forest = IsolationForest(contamination=0.05, random_state=42)
            iso_forest.fit(numeric_df)
            scores = iso_forest.decision_function(numeric_df)
            outlier_mask = iso_forest.predict(numeric_df) == -1
            iso_outlier_indices = df.index[outlier_mask].tolist()
            
            if iso_outlier_indices:
                iso_outliers = {
                    'count': len(iso_outlier_indices),
                    'indices': iso_outlier_indices[:10],
                    'score_quantiles': {
                        '10%': float(np.quantile(scores, 0.1)),
                        '25%': float(np.quantile(scores, 0.25)),
                        '50%': float(np.quantile(scores, 0.5)),
                        '75%': float(np.quantile(scores, 0.75)),
                        '90%': float(np.quantile(scores, 0.9))
                    }
                }
            else:
                iso_outliers = {'count': 0}
        except:
            iso_outliers = {'error': 'Failed to run Isolation Forest'}
    else:
        iso_outliers = {'message': 'Not enough data for Isolation Forest'}
    
    outliers['z_score'] = z_score_outliers
    outliers['iqr'] = iqr_outliers
    outliers['isolation_forest'] = iso_outliers
    
    return outliers

def analyze_correlations(df):
    """Correlation analysis with Plotly"""
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty or numeric_df.shape[1] < 2:
        return {'message': 'Not enough numeric columns for correlation analysis'}
    
    corr_matrix = numeric_df.corr().round(3)
    
    corr_pairs = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            col1 = corr_matrix.columns[i]
            col2 = corr_matrix.columns[j]
            corr = corr_matrix.iloc[i, j]
            if not np.isnan(corr):
                corr_pairs.append({
                    'column1': col1,
                    'column2': col2,
                    'correlation': float(corr)
                })
    
    corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
    
    # Fix: Added closing parenthesis for Heatmap and Figure
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale='Blues',
        zmin=-1, zmax=1,
        text=np.round(corr_matrix.values, 2),
        texttemplate='%{text}',
        colorbar=dict(title='Correlation')
    ))
    
    fig.update_layout(
        title='Correlation Heatmap',
        height=450,
        width=600,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return {
        'pairs': corr_pairs[:10],
        'heatmap_plotly': json.dumps(fig.to_dict(), cls=CustomJSONEncoder)
    }

def generate_visualizations(df):
    """Generate simplified Plotly visualizations with clean layout and improved readability"""
    import numpy as np
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    from scipy import stats
    import statsmodels.api as sm
    import json
    
    # Simplified color palette with fewer colors
    COLORS = {
        'primary': '#4285F4',    # Google Blue
        'secondary': '#34A853',  # Google Green  
        'accent': '#EA4335',     # Google Red
        'dark': '#202124',       # Dark gray for text
        'light': '#E8EAED'       # Light gray for backgrounds
    }
    
    # Simplified chart layout with minimalist approach
    def get_base_layout(title, height=None, width=None):
        layout = {
            'template': 'plotly_white',
            'margin': dict(l=30, r=30, t=50, b=30),  # Reduced margins
            'font': dict(family='Arial, sans-serif', color=COLORS['dark'], size=10),
            'title': dict(
                text=title,
                font=dict(size=14, color=COLORS['dark']),
                x=0.5,
                xanchor='center',
                y=0.95
            ),
            'legend': dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=9),
                bgcolor='rgba(255,255,255,0.8)',
            ),
            'plot_bgcolor': 'white',
            'paper_bgcolor': 'white',
            'width': width if width else 550,  # Slightly reduced width
            'xaxis': dict(
                automargin=True,
                showgrid=False,  # Remove gridlines for cleaner look
                linecolor='lightgray',
                linewidth=1
            ),
            'yaxis': dict(
                automargin=True,
                showgrid=True,    # Keep y-grid for reference but make it lighter
                gridcolor='rgba(0,0,0,0.05)',
                linecolor='lightgray',
                linewidth=1
            ),
        }
        
        if height:
            layout['height'] = height
            
        return layout
    
    # Simplified annotations (fewer stats, cleaner presentation)
    def create_stat_annotation(text, x=0.5, y=0.02):
        return dict(
            x=x, y=y,
            xref="paper", yref="paper",
            text=text,
            showarrow=False,
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.85)",
            borderwidth=0,  # Remove border
            borderpad=4,
            align="center",
            xanchor="center"
        )
    
    visualizations = []
    
    # Identify numeric and categorical columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=['string', 'category', 'object']).columns.tolist()
    
    # 1. NUMERICAL DISTRIBUTIONS - SIMPLIFIED
    if numeric_cols:
        for i, col in enumerate(numeric_cols[:3]):
            size_config = "small" if i == 0 else "xsmall"
            
            # Create simple histogram instead of combined chart
            fig = go.Figure()
            
            hist_data = df[col].dropna()
            hist_data = hist_data.to_numpy().tolist()
            
            if len(hist_data) > 0:
                # Add simplified histogram
                fig.add_trace(
                    go.Histogram(
                        x=hist_data,
                        marker_color=COLORS['primary'],
                        opacity=0.7,
                        nbinsx=min(20, len(set(hist_data)) // 2 + 1),  # Fewer bins
                    )
                )
                
                # Add KDE curve if we have enough data
                if len(hist_data) > 5:
                    try:
                        kde_x = np.linspace(min(hist_data), max(hist_data), 100).tolist()
                        kde = stats.gaussian_kde(hist_data)
                        kde_y = kde(kde_x).tolist()
                        
                        # Scale the KDE to match histogram height
                        hist_max = max(np.histogram(hist_data, bins=20)[0])
                        scale_factor = hist_max / max(kde_y)
                        
                        fig.add_trace(
                            go.Scatter(
                                x=kde_x,
                                y=[y * scale_factor for y in kde_y],
                                mode='lines',
                                line=dict(color=COLORS['accent'], width=2),
                                name='Density'
                            )
                        )
                    except:
                        pass
                
                # Calculate minimal statistics
                hist_numpy = np.array(hist_data)
                mean_val = np.mean(hist_numpy)
                median_val = np.median(hist_numpy)
                
                # Add vertical lines for mean and median
                fig.add_shape(
                    type="line",
                    x0=mean_val, x1=mean_val,
                    y0=0, y1=1,
                    yref="paper",
                    line=dict(color=COLORS['secondary'], width=2, dash="solid"),
                    name="Mean"
                )
                
                fig.add_shape(
                    type="line",
                    x0=median_val, x1=median_val,
                    y0=0, y1=1,
                    yref="paper",
                    line=dict(color=COLORS['accent'], width=2, dash="dash"),
                    name="Median"
                )
                
                # Add legend for mean and median lines
                fig.add_trace(
                    go.Scatter(
                        x=[None], y=[None],
                        mode="lines",
                        line=dict(color=COLORS['secondary'], width=2),
                        name=f"Mean: {mean_val:.2f}"
                    )
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=[None], y=[None],
                        mode="lines",
                        line=dict(color=COLORS['accent'], width=2, dash="dash"),
                        name=f"Median: {median_val:.2f}"
                    )
                )
                
                # Set appropriate size
                height = 350 if size_config == "small" else 300
                width = 550 if size_config == "small" else 450
                
                # Update layout with simplified settings
                base_layout = get_base_layout(f'Distribution of {col}', height=height, width=width)
                fig.update_layout(**base_layout)
                fig.update_layout(
                    bargap=0.05,  # Tighter bars
                    showlegend=True,
                    xaxis_title=col,
                    yaxis_title="Count"
                )
                
                try:
                    fig_json = json.dumps(fig.to_dict(), cls=CustomJSONEncoder)


                    visualizations.append({
                        'title': f'Distribution of {col}',
                        'type': 'histogram',
                        'size': size_config,
                        'plotly_figure': fig_json
                    })
                except (TypeError, ValueError) as e:
                    visualizations.append({
                        'title': f'Distribution of {col}',
                        'type': 'histogram',
                        'size': size_config,
                        'error': f"Could not serialize plot: {str(e)}"
                    })
    
    # 2. CATEGORICAL VISUALIZATIONS - SIMPLIFIED
    if cat_cols:
        for i, col in enumerate(cat_cols[:3]):
            size_config = "small" if i == 0 else "xsmall"
            card_height = 350 if size_config == "small" else 300
            
            if df[col].nunique() <= 10:  # Reduced from 15 to 10 for simplicity
                value_counts = df[col].value_counts().reset_index()
                value_counts.columns = [col, 'Count']
                value_counts = value_counts.sort_values('Count', ascending=False).head(8)  # Limit to top 8
                
                # Convert to Python native types
                x_values = value_counts[col].astype(str).tolist()
                y_values = value_counts['Count'].tolist()
                
                # Create a horizontal bar chart
                fig = go.Figure()
                
                # Add bars with simpler style
                fig.add_trace(go.Bar(
                    y=x_values[::-1],  # Reverse for highest at top
                    x=y_values[::-1],
                    orientation='h',
                    marker_color=COLORS['primary'],
                    textposition='outside',
                    name='Count'
                ))
                
                width = 550 if size_config == "small" else 450
                base_layout = get_base_layout(f'Distribution of {col}', height=card_height, width=width)
                base_layout.update(
                    xaxis_title='Count',
                    yaxis_title=None,
                    showlegend=False,
                    margin=dict(l=120, r=30, t=50, b=30)  # Adjusted left margin for labels
                )
                fig.update_layout(**base_layout)
                
                try:
                    fig_json = json.dumps(fig.to_dict(), cls=CustomJSONEncoder)


                    visualizations.append({
                        'title': f'Distribution of {col}',
                        'type': 'horizontal_bar',
                        'size': size_config,
                        'plotly_figure': fig_json
                    })
                except (TypeError, ValueError) as e:
                    visualizations.append({
                        'title': f'Distribution of {col}',
                        'type': 'horizontal_bar',
                        'size': size_config,
                        'error': f"Could not serialize plot: {str(e)}"
                    })
            else:
                # For high cardinality, show top categories
                top_n = 5  # Reduced from 6 to 5
                value_counts = df[col].value_counts()
                top_values = value_counts.head(top_n)
                
                # Group the rest as "Others"
                others_sum = value_counts.iloc[top_n:].sum()
                
                # Combine top values with "Others"
                labels = [str(x) for x in list(top_values.index)] + ['Others']
                values = list(top_values.values) + [others_sum]
                values = [float(v) for v in values]
                
                # Create simple pie chart
                fig = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,  # Donut chart for modern look
                    marker_colors=px.colors.qualitative.Pastel,  # Pastel colors are less cluttered
                    textinfo='percent',
                    insidetextorientation='radial',
                    sort=False
                )])
                
                width = 550 if size_config == "small" else 450
                base_layout = get_base_layout(
                    f'Top {top_n} Values in {col}',
                    height=card_height,
                    width=width
                )
                fig.update_layout(**base_layout)
                
                try:
                    fig_json = json.dumps(fig.to_dict(), cls=CustomJSONEncoder)


                    visualizations.append({
                        'title': f'Top Values in {col}',
                        'type': 'pie',
                        'size': size_config,
                        'plotly_figure': fig_json
                    })
                except (TypeError, ValueError) as e:
                    visualizations.append({
                        'title': f'Top Values in {col}',
                        'type': 'pie',
                        'size': size_config,
                        'error': f"Could not serialize plot: {str(e)}"
                    })
    
    # 3. CORRELATION ANALYSIS - SIMPLIFIED
    numeric_df = df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) >= 2:
        size_config = "medium"
        
        # Find highest correlation pair
        corr_matrix = numeric_df.corr().abs()
        np.fill_diagonal(corr_matrix.values, 0)
        
        max_corr_idx = np.argmax(corr_matrix.values)
        i, j = np.unravel_index(max_corr_idx, corr_matrix.shape)
        col1, col2 = corr_matrix.columns[i], corr_matrix.columns[j]
        actual_corr = numeric_df[[col1, col2]].corr().iloc[0,1]
        
        # Create scatter plot with regression line
        x_data = df[col1].dropna().tolist()
        y_data = df[col2].dropna().tolist()
        
        if len(x_data) > 3 and len(y_data) > 3:
            fig = go.Figure()
            
            try:
                # Convert to numpy arrays for regression
                x_array = np.array(x_data)
                y_array = np.array(y_data)
                
                # Create matching arrays
                mask = ~np.isnan(x_array) & ~np.isnan(y_array)
                x_clean = x_array[mask]
                y_clean = y_array[mask]
                
                if len(x_clean) > 3:
                    # Add scatter plot with simple styling
                    fig.add_trace(
                        go.Scatter(
                            x=x_clean.tolist(),
                            y=y_clean.tolist(),
                            mode='markers',
                            marker=dict(
                                color=COLORS['primary'],
                                opacity=0.6,
                                size=6,
                            ),
                            name='Data Points'
                        )
                    )
                    
                    # Add regression line
                    X = sm.add_constant(x_clean)
                    model = sm.OLS(y_clean, X).fit()
                    slope = model.params[1]
                    intercept = model.params[0]
                    
                    # Generate points for regression line
                    x_line = np.linspace(min(x_clean), max(x_clean), 100)
                    y_line = intercept + slope * x_line
                    
                    # Add trend line
                    fig.add_trace(
                        go.Scatter(
                            x=x_line.tolist(),
                            y=y_line.tolist(),
                            mode='lines',
                            name=f'r = {actual_corr:.2f}',
                            line=dict(color=COLORS['accent'], width=2)
                        )
                    )
                    
                    base_layout = get_base_layout(
                        f'{col1} vs {col2}',
                        height=400,
                        width=550
                    )
                    base_layout.update(
                        xaxis_title=dict(text=col1, font=dict(size=11)),
                        yaxis_title=dict(text=col2, font=dict(size=11))
                    )
                    fig.update_layout(**base_layout)
                    
                    try:
                        fig_json = json.dumps(fig.to_dict(), cls=CustomJSONEncoder)


                        visualizations.append({
                            'title': f'{col1} vs {col2}',
                            'type': 'scatter_regression',
                            'size': size_config,
                            'plotly_figure': fig_json
                        })
                    except (TypeError, ValueError) as e:
                        visualizations.append({
                            'title': f'{col1} vs {col2}',
                            'type': 'scatter_regression',
                            'size': size_config,
                            'error': f"Could not serialize plot: {str(e)}"
                        })
            except Exception as e:
                visualizations.append({
                    'title': f'{col1} vs {col2}',
                    'type': 'scatter_regression',
                    'size': size_config,
                    'error': f"Error creating plot: {str(e)}"
                })
    
    
    # 4. DATA COMPLETENESS - SIMPLIFIED
    size_config = "small"
    
    try:
        # Calculate missing values percentage
        missing_data = df.isnull().sum().astype(int).sort_values(ascending=False)
        missing_percent = (missing_data / len(df) * 100).round(1)
        
        # Filter to include only columns with missing values
        missing_percent = missing_percent[missing_percent > 0]
        
        if not missing_percent.empty:
            # Get top 8 columns with missing values (reduced from 15)
            missing_percent = missing_percent.head(8)
            
            # Convert to Python native types
            x_values = missing_percent.values.tolist()
            y_values = missing_percent.index.tolist()
            
            # Create horizontal bar chart with simpler style
            fig = go.Figure()
            
            # Add bars
            fig.add_trace(go.Bar(
                y=y_values,
                x=x_values,
                orientation='h',
                text=[f"{v:.1f}%" for v in x_values],
                textposition='auto',
                marker_color=COLORS['primary'],
                hovertemplate='%{y}: %{x:.1f}%<extra></extra>'
            ))
            
            base_layout = get_base_layout('Missing Values', height=350, width=550)
            base_layout.update(
                xaxis_title='Missing (%)',
                yaxis_title=None,
                margin=dict(l=120, r=30, t=50, b=30),
                showlegend=False
            )
            fig.update_layout(**base_layout)
            
            try:
                fig_json = json.dumps(fig.to_dict(), cls=CustomJSONEncoder)


                visualizations.append({
                    'title': 'Missing Values',
                    'type': 'missing_values',
                    'size': size_config,
                    'plotly_figure': fig_json
                })
            except (TypeError, ValueError) as e:
                visualizations.append({
                    'title': 'Missing Values',
                    'type': 'missing_values',
                    'size': size_config,
                    'error': f"Could not serialize plot: {str(e)}"
                })
    except Exception as e:
        visualizations.append({
            'title': 'Missing Values',
            'type': 'missing_values',
            'size': size_config,
            'error': f"Error analyzing missing values: {str(e)}"
        })
    
    return visualizations
def perform_clustering(df):
    """Clustering analysis with Plotly"""
    numeric_df = df.select_dtypes(include=[np.number])
    
    if len(numeric_df.columns) < 2 or len(numeric_df) < 20:
        return {'message': 'Not enough numerical data for clustering'}
    
    numeric_df = numeric_df.fillna(numeric_df.median())
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(numeric_df)
    
    result = {}
    
    # Elbow method
    inertia = []
    k_range = range(2, min(10, len(numeric_df) // 5 + 1))
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(scaled_data)
        inertia.append(kmeans.inertia_)
    
    fig = go.Figure(data=go.Scatter(
        x=list(k_range), 
        y=inertia, 
        mode='lines+markers',
        marker=dict(color=BLUE_PALETTE['primary'], size=8),
        line=dict(color=BLUE_PALETTE['primary'], width=2)
    ))
    
    fig.update_layout(
        title='Elbow Method for Optimal k',
        height=350,
        width=500,
        template='plotly_white',
        margin=dict(l=40, r=40, t=50, b=40)
    )
    
    result['elbow_curve_plotly'] = json.dumps(fig.to_dict(), cls=CustomJSONEncoder)
    
    # Optimal clusters detection
    from scipy.signal import argrelextrema
    n_clusters = 3
    
    if len(inertia) > 3:
        diffs = np.diff(inertia)
        second_diffs = np.diff(diffs)
        
        if len(second_diffs) > 1:
            inflection_points = argrelextrema(np.array(second_diffs), np.less)[0]
            if inflection_points.size > 0:
                n_clusters = k_range[inflection_points[0] + 2]
    
    # KMeans clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(scaled_data)
    
    # PCA visualization
    if len(numeric_df.columns) > 2:
        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(scaled_data)
        
        cluster_df_pca = pd.DataFrame({
            'PCA1': pca_result[:, 0],
            'PCA2': pca_result[:, 1],
            'Cluster': clusters
        })
        
        fig = px.scatter(
            cluster_df_pca, 
            x='PCA1', 
            y='PCA2', 
            color='Cluster',
            color_continuous_scale='Blues',
            title=f'Cluster Visualization using PCA (K={n_clusters})'
        )
        
        fig.update_layout(
            height=450,
            width=600,
            template='plotly_white',
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        result['cluster_visualization_plotly'] = json.dumps(fig.to_dict(), cls=CustomJSONEncoder)
        result['pca_variance'] = {
            'pc1': float(pca.explained_variance_ratio_[0]),
            'pc2': float(pca.explained_variance_ratio_[1])
        }
    
    # Cluster statistics
    cluster_df = numeric_df.copy()
    cluster_df['cluster'] = clusters
    
    cluster_stats = {}
    for i in range(n_clusters):
        cluster_data = cluster_df[cluster_df['cluster'] == i].drop('cluster', axis=1)
        cluster_stats[f'Cluster_{i}'] = {
            'size': int(len(cluster_data)),
            'percentage': float(round(len(cluster_data) / len(cluster_df) * 100, 2)),
            'mean': {k: float(v) for k, v in cluster_data.mean().items()}
        }
    
    result['optimal_clusters'] = n_clusters
    result['cluster_stats'] = cluster_stats
    
    return result

def generate_insights(df):
    """Generate automated insights"""
    insights = []
    
    # Dataset size insights
    if len(df) < 10:
        insights.append({
            'type': 'warning',
            'message': 'The dataset is very small (less than 10 records). Results may not be statistically significant.'
        })
    elif len(df) > 10000:
        insights.append({
            'type': 'info',
            'message': f'Large dataset with {len(df)} records - analysis may take longer but should be more reliable.'
        })
    
    # Missing values
    missing_counts = df.isna().sum()
    missing_cols = missing_counts[missing_counts > 0]
    
    if len(missing_cols) > 0:
        if (missing_cols / len(df) > 0.5).any():
            insights.append({
                'type': 'warning',
                'message': f'Some columns have more than 50% missing values: {missing_cols[missing_cols / len(df) > 0.5].index.tolist()}'})
        else:
            insights.append({
                'type': 'info',
                'message': f'{len(missing_cols)} columns have missing values. Consider imputation for better analysis.'})
    else:
        insights.append({
            'type': 'success',
            'message': 'No missing values found in the dataset - good data quality!'})
    
    # Column types
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['string', 'category']).columns.tolist()
    
    insights.append({
        'type': 'info',
        'message': f'Dataset has {len(numeric_cols)} numeric columns and {len(categorical_cols)} categorical columns.'})
    
    # Numeric distributions
    for col in numeric_cols[:5]:  # Check first 5 numeric columns
        # Convert to numpy dtype for skew calculation
        col_data = df[col].astype('float64')
        skew = col_data.skew()
        
        if abs(skew) > 1:
            skew_direction = 'right' if skew > 0 else 'left'
            insights.append({
                'type': 'info',
                'message': f"'{col}' has a {skew_direction}-skewed distribution (skew = {round(skew, 2)}). Consider transformation for analysis."
            })
    # Categorical insights
    for col in categorical_cols[:5]:
        unique_count = df[col].nunique()
        if unique_count == 1:
            insights.append({
                'type': 'warning',
                'message': f"'{col}' has only one unique value - may not be useful for analysis."})
        elif unique_count > 100:
            insights.append({
                'type': 'info',
                'message': f"'{col}' has high cardinality ({unique_count} unique values). Consider grouping or encoding."})
    
    # Duplicates
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        insights.append({
            'type': 'warning',
            'message': f'Found {dup_count} duplicate rows ({round(dup_count/len(df)*100, 2)}% of data). Consider removing duplicates.'})
    
    return insights

if __name__ == '__main__':
    app.run(debug=True, port=5000)
