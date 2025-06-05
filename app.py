from flask import Flask, render_template, request, jsonify
import mysql.connector
import pandas as pd
import numpy as np
import os
from datetime import datetime
import ml

app = Flask(__name__)

db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'myntradb'
}

MODELS_DIR = 'models'
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    chart_type = request.args.get('type')

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        if chart_type == 'price_diff_category':
            cursor.execute("""
                SELECT category, AVG(original_price) as avg_original, AVG(price) as avg_discounted
                FROM cleaned_products
                GROUP BY category
                HAVING COUNT(*) > 5
                ORDER BY avg_original DESC
            """)
            rows = cursor.fetchall()
            result = {
                "original": [{"label": row[0], "y": round(row[1], 2)} for row in rows],
                "discounted": [{"label": row[0], "y": round(row[2], 2)} for row in rows]
            }

        elif chart_type == 'price_diff_subcategory':
            cursor.execute("""
                SELECT subcategory, AVG(original_price) as avg_original, AVG(price) as avg_discounted
                FROM cleaned_products
                GROUP BY subcategory
                HAVING COUNT(*) > 5
                ORDER BY avg_original DESC
                LIMIT 15
            """)
            rows = cursor.fetchall()
            result = {
                "original": [{"label": row[0], "y": round(row[1], 2)} for row in rows],
                "discounted": [{"label": row[0], "y": round(row[2], 2)} for row in rows]
            }

        elif chart_type == 'product_distribution':
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM cleaned_products
                GROUP BY category
                ORDER BY count DESC
            """)
            result = [{"label": row[0], "y": row[1]} for row in cursor.fetchall()]

        elif chart_type == 'correlation_features':
            cursor.execute("""
                SELECT price, rating
                FROM cleaned_products
                WHERE rating IS NOT NULL AND price IS NOT NULL
                ORDER BY RAND()
                LIMIT 300
            """)
            result = [{"x": float(row[0]), "y": float(row[1])} for row in cursor.fetchall()]

        elif chart_type == 'top_selling_brands':
            cursor.execute("""
                SELECT brand, COUNT(*) as count
                FROM cleaned_products
                GROUP BY brand
                ORDER BY count DESC
                LIMIT 10
            """)
            result = [{"label": row[0], "y": row[1]} for row in cursor.fetchall()]

        elif chart_type == 'rating_distribution':
            cursor.execute("""
                SELECT brand, AVG(rating) as avg_rating
                FROM cleaned_products
                WHERE rating IS NOT NULL
                GROUP BY brand
                HAVING COUNT(*) > 10
                ORDER BY avg_rating DESC
                LIMIT 20
            """)
            result = [{"label": row[0], "y": round(row[1], 2)} for row in cursor.fetchall()]

        elif chart_type == 'discount_vs_rating':
            cursor.execute("""
                SELECT brand, AVG(discount) as avg_discount, AVG(rating) as avg_rating
                FROM cleaned_products
                WHERE discount IS NOT NULL AND rating IS NOT NULL
                GROUP BY brand
                HAVING COUNT(*) > 5
            """)
            result = [{"x": round(row[1], 2), "y": round(row[2], 2), "label": row[0]} for row in cursor.fetchall()]

        elif chart_type == 'best_discounted_high_rated':
            cursor.execute("""
                SELECT category, AVG(discount) as avg_discount
                FROM cleaned_products
                WHERE rating > 4 AND price < 1000
                GROUP BY category
                HAVING AVG(discount) > 30 AND COUNT(*) > 5
                ORDER BY avg_discount DESC
            """)
            result = [{"label": row[0], "y": round(row[1], 2)} for row in cursor.fetchall()]

        else:
            result = {"error": "Invalid chart type"}

        cursor.close()
        conn.close()
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/run_regression', methods=['POST'])
def run_regression():
    data = request.get_json()
    target = data.get('target')
    features = data.get('features')
    technique = data.get('technique', 'linear')

    if not target or not features:
        return jsonify({'error': 'Please select both target and feature variables'})

    try:
        query_cols = ', '.join([target] + features)
        conn = mysql.connector.connect(**db_config)
        query = f"""
            SELECT {query_cols}
            FROM cleaned_products
            WHERE {' AND '.join([f'{col} IS NOT NULL' for col in [target] + features])}
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty or len(df) < 10:
            return jsonify({'error': 'Not enough data available for selected columns'})
            
        X, y = ml.preprocess_data(df, target, features)
        
        if len(X) < 10:
            return jsonify({'error': 'Not enough data left after preprocessing'})
            
        model_data = ml.train_model(X, y, technique)
        
        model_id = f"{target}_{'-'.join(features)}_{technique}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        ml.save_model(model_data, target, features, technique, model_id)
        
        app.config['LATEST_MODEL_ID'] = model_id
        app.config['LATEST_MODEL_DATA'] = {
            'pipeline': model_data['pipeline'],
            'features': features,
            'target': target,
            'technique': technique
        }

        return jsonify({
            'features': features,
            'train_actual': model_data['train_actual'].tolist(),
            'train_pred': model_data['train_pred'].tolist(),
            'test_actual': model_data['test_actual'].tolist(),
            'test_pred': model_data['test_pred'].tolist(),
            'r2': model_data['r2'],
            'model_id': model_id
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error during regression: {str(e)}'})

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    inputs = data.get('inputs')  
    target = data.get('target')  
    technique = data.get('technique', 'linear')
    
    if not inputs or not target:
        return jsonify({'error': 'Missing required parameters'})
    
    try:
        model_id = data.get('model_id') or app.config.get('LATEST_MODEL_ID')
        
        if not model_id or 'LATEST_MODEL_DATA' in app.config:
            model_data = app.config.get('LATEST_MODEL_DATA')
            
            if not model_data:
                return jsonify({'error': 'No trained model available'})
            
            missing_features = [f for f in model_data['features'] if f not in inputs]
            if missing_features:
                return jsonify({'error': f'Missing features: {", ".join(missing_features)}'})
            
            prediction = ml.predict(inputs, model_data)
            
        else:
            model_data = ml.load_model(model_id)
            
            if not model_data:
                return jsonify({'error': 'Model not found'})
            
            missing_features = [f for f in model_data['features'] if f not in inputs]
            if missing_features:
                return jsonify({'error': f'Missing features: {", ".join(missing_features)}'})
            
            prediction = ml.predict(inputs, model_data)
        
        return jsonify({
            'predicted': prediction,
            'target': target
        })
        
    except Exception as e:
        return jsonify({'error': f'Prediction error: {str(e)}'})

@app.route('/models', methods=['GET'])
def list_models():
    try:
        models = []
        for filename in os.listdir(ml.MODELS_DIR):
            if filename.endswith('.pkl'):
                model_data = ml.load_model(filename.replace('.pkl', ''))
                if model_data:
                    models.append({
                        'id': filename.replace('.pkl', ''),
                        'target': model_data['target'],
                        'features': model_data['features'],
                        'technique': model_data.get('technique', 'linear'),
                        'r2': model_data['r2']
                    })
        return jsonify({'models': models})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/run_classification', methods=['POST'])
def run_classification():
    data = request.get_json()
    target = data.get('target')
    features = data.get('features')
    technique = data.get('technique', 'decision_tree')  

    if not target or not features:
        return jsonify({'error': 'Please select both target and feature variables'})

    try:
        if target == 'brand_popularity':
            query_cols = ['brand'] + features
            query_cols = [col for col in query_cols if col != 'id']  
            
            conn = mysql.connector.connect(**db_config)
            query = f"""
                SELECT {', '.join(query_cols)}, COUNT(*) as id
                FROM cleaned_products
                GROUP BY {', '.join(query_cols)}
                HAVING COUNT(*) > 1
            """
            df = pd.read_sql(query, conn)
            conn.close()
            
            if df.empty or len(df) < 10:
                return jsonify({'error': 'Not enough data available for selected columns'})
                
            if 'id' in features and 'id' not in df.columns:
                return jsonify({'error': 'id feature selected but not available in data'})
            
            df['rank'] = df['id'].rank(method='first')
            total_rows = len(df)
            df['brand_popularity'] = pd.cut(
                df['rank'], 
                bins=[0, total_rows/3, 2*total_rows/3, total_rows+1],
                labels=['Low', 'Medium', 'High'],
                include_lowest=True
            )
            
        elif target == 'price_category':
            query_cols = features.copy()
            if 'brand' in query_cols:
                query_cols = [col for col in query_cols if col != 'brand'] + ['brand']
                
            conn = mysql.connector.connect(**db_config)
            query = f"""
                SELECT {', '.join(query_cols)}, price
                FROM cleaned_products
            """
            df = pd.read_sql(query, conn)
            conn.close()
            
            if df.empty or len(df) < 10:
                return jsonify({'error': 'Not enough data available for selected columns'})
            
            df['rank'] = df['price'].rank(method='first')
            total_rows = len(df)
            df['price_category'] = pd.cut(
                df['rank'], 
                bins=[0, total_rows/3, 2*total_rows/3, total_rows+1],
                labels=['Low', 'Medium', 'High'],
                include_lowest=True
            )
        else:
            return jsonify({'error': 'Invalid target variable'})

        X, y, classes = ml.preprocess_classification_data(df, target, features)
        
        if len(X) < 10:
            return jsonify({'error': 'Not enough data left after preprocessing'})
            
        model_data = ml.train_classification_model(X, y, classes, technique)
        
        model_id = f"{target}_{'-'.join(features)}_{technique}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        ml.save_classification_model(model_data, target, features, technique, model_id, classes)
        
        app.config['LATEST_CLASS_MODEL_ID'] = model_id
        app.config['LATEST_CLASS_MODEL_DATA'] = {
            'pipeline': model_data['pipeline'],
            'features': features,
            'target': target,
            'technique': technique,
            'classes': classes
        }

        confusion_matrix_data = []
        cm = model_data['confusion_matrix']
        
        class_labels = classes
        for i in range(len(class_labels)):
            for j in range(len(class_labels)):
                confusion_matrix_data.append({
                    'label': f'Actual: {class_labels[i]}, Predicted: {class_labels[j]}',
                    'y': int(cm[i, j]),
                    'color': '#563d7c' if i == j else '#8e79b8'
                })

        return jsonify({
            'features': features,
            'target': target,
            'accuracy': float(model_data['accuracy']),
            'precision': float(model_data['precision']),
            'recall': float(model_data['recall']),
            'confusion_matrix_data': confusion_matrix_data,
            'class_labels': classes,
            'model_id': model_id
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error during classification: {str(e)}'})

@app.route('/predict_class', methods=['POST'])
def predict_class():
    data = request.get_json()
    inputs = data.get('inputs')  
    target = data.get('target')  
    technique = data.get('technique', 'decision_tree')  
    
    if not inputs or not target:
        return jsonify({'error': 'Missing required parameters'})
    
    try:
        model_id = data.get('model_id') or app.config.get('LATEST_CLASS_MODEL_ID')
        
        if not model_id or 'LATEST_CLASS_MODEL_DATA' in app.config:
            model_data = app.config.get('LATEST_CLASS_MODEL_DATA')
            
            if not model_data:
                return jsonify({'error': 'No trained model available'})
            
            missing_features = [f for f in model_data['features'] if f not in inputs]
            if missing_features:
                return jsonify({'error': f'Missing features: {", ".join(missing_features)}'})
            
            prediction = ml.predict_class(inputs, model_data)
            
        else:
            model_data = ml.load_classification_model(model_id)
            
            if not model_data:
                return jsonify({'error': 'Model not found'})
            
            missing_features = [f for f in model_data['features'] if f not in inputs]
            if missing_features:
                return jsonify({'error': f'Missing features: {", ".join(missing_features)}'})
            
            prediction = ml.predict_class(inputs, model_data)
        
        return jsonify({
            'predicted_class': prediction,
            'target': target
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Prediction error: {str(e)}'})

@app.route('/get_brands', methods=['GET'])
def get_brands():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT brand FROM cleaned_products
            ORDER BY brand
            LIMIT 100
        """)
        brands = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'brands': brands})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/run_clustering', methods=['POST'])
def run_clustering():
    data = request.get_json()
    group_by = data.get('group_by')  
    technique = data.get('technique', 'kmeans')  
    n_clusters = data.get('n_clusters', 0)  
    features = data.get('features', ['price', 'discount']) 
    
    if not group_by:
        return jsonify({'error': 'Please select a grouping variable'})
    
    if len(features) < 2:
        return jsonify({'error': 'Please select at least 2 features'})
    
    feature_map = {
        'price': 'AVG(price) AS avg_price',
        'discount': 'AVG(discount) AS avg_discount',
        'rating': 'AVG(rating) AS avg_rating'
    }
    
    try:
        conn = mysql.connector.connect(**db_config)
        query = f"""
            SELECT 
                {group_by},
                {', '.join([feature_map[f] for f in features])}
            FROM cleaned_products
            WHERE {group_by} IS NOT NULL
            GROUP BY {group_by}
            HAVING COUNT(*) > 5
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        if df.empty or len(df) < 2:
            return jsonify({'error': 'Not enough data available for clustering analysis'})
        
        db_features = [f'avg_{f}' for f in features]
        X_scaled, df_clean, scaler = ml.preprocess_clustering_data(df, db_features)
        
        if n_clusters <= 0:
            optimal_clusters_data = ml.find_optimal_clusters(X_scaled, max_clusters=10, technique=technique)
            n_clusters = optimal_clusters_data['optimal_clusters']
            
            elbow_data = []
            silhouette_data = []
            
            if technique == 'kmeans':
                elbow_data = [
                    {"x": k, "y": v} 
                    for k, v in zip(
                        optimal_clusters_data['range_clusters'], 
                        optimal_clusters_data['inertia_values']
                    )
                ]
            
            silhouette_data = [
                {"x": k, "y": v} 
                for k, v in zip(
                    optimal_clusters_data['range_clusters'], 
                    optimal_clusters_data['silhouette_scores']
                )
            ]
        else:
            elbow_data = []
            silhouette_data = []
        
        if technique == 'kmeans':
            model_data = ml.run_kmeans_clustering(X_scaled, n_clusters)
        elif technique == 'hierarchical':
            model_data = ml.run_hierarchical_clustering(X_scaled, n_clusters)
        else:
            return jsonify({'error': 'Invalid clustering technique'})
        
        df_clean['cluster'] = model_data['labels']
        
        centroids_orig = scaler.inverse_transform(model_data['centroids'])
        
        scatter_data = []
        for i, row in df_clean.iterrows():
            point_data = {
                'name': row[group_by],
                'cluster': int(row['cluster'])
            }
            
            for feature in features:
                feature_key = f'avg_{feature}'
                if feature_key in row:
                    point_data[feature] = float(row[feature_key])
            
            scatter_data.append(point_data)
        
        centroids = []
        for i, centroid in enumerate(centroids_orig):
            centroid_data = {
                'cluster': i,
                'isCentroid': True
            }
            
            for j, feature in enumerate(features):
                centroid_data[feature] = float(centroid[j])
            
            centroids.append(centroid_data)
            
        return jsonify({
            'silhouette_score': float(model_data['silhouette_score']),
            'n_clusters': n_clusters,
            'scatter_data': scatter_data,
            'centroids': centroids, 
            'group_by': group_by,
            'technique': technique,
            'elbow_data': elbow_data,
            'silhouette_data': silhouette_data,
            'model_id': f"cluster_{group_by}_{technique}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'features': features  
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error during clustering: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)