import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, RobustScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score, precision_score, recall_score, confusion_matrix, classification_report, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.cluster import KMeans, AgglomerativeClustering
import pickle
import os

MODELS_DIR = 'models'
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)

def preprocess_data(df, target, features):
    df_clean = df.copy()
    
    for col in df_clean.columns:
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df_clean = df_clean[(df_clean[col] >= lower_bound) & (df_clean[col] <= upper_bound)]
    
    X = df_clean[features]
    y = df_clean[target]
    
    return X, y

def train_model(X, y, technique='linear'):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    if technique == 'linear':
        pipeline = Pipeline([
            ('scaler', RobustScaler()),
            ('feature_selection', SelectKBest(f_regression, k='all')), 
            ('model', LinearRegression())
        ])
        
    elif technique == 'svr':
        pipeline = Pipeline([
            ('scaler', RobustScaler()),
            ('feature_selection', SelectKBest(f_regression, k='all')),
            ('model', SVR(kernel='rbf'))
        ])
        
        param_grid = {
            'model__C': [0.1, 1, 10, 100],
            'model__gamma': ['scale', 'auto', 0.1, 0.01],
            'model__epsilon': [0.01, 0.1, 0.2]
        }
        
        if len(X_train) > 100:
            pipeline = GridSearchCV(pipeline, param_grid, cv=5, scoring='neg_mean_squared_error', n_jobs=-1)
    
    pipeline.fit(X_train, y_train)
    
    if isinstance(pipeline, GridSearchCV):
        best_params = pipeline.best_params_
        pipeline = pipeline.best_estimator_
    
    train_pred = pipeline.predict(X_train)
    test_pred = pipeline.predict(X_test)
    
    r2 = r2_score(y_test, test_pred)
    
    return {
        'pipeline': pipeline,
        'train_actual': y_train,
        'train_pred': train_pred,
        'test_actual': y_test,
        'test_pred': test_pred,
        'r2': r2
    }

def save_model(model_data, target, features, technique, model_id):
    model_path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
    
    with open(model_path, 'wb') as f:
        pickle.dump({
            'pipeline': model_data['pipeline'],
            'features': features,
            'target': target,
            'technique': technique,
            'r2': model_data['r2']
        }, f)
    
    return model_id

def load_model(model_id):
    model_path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
    
    if not os.path.exists(model_path):
        return None
    
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    return model_data

def predict(inputs, model_data):
    features = model_data['features']
    pipeline = model_data['pipeline']
    
    input_values = [inputs[feature] for feature in features]
    input_df = pd.DataFrame([input_values], columns=features)
    
    prediction = float(pipeline.predict(input_df)[0])
    return prediction

def preprocess_classification_data(df, target, features):
    df_clean = df.copy()
    
    categorical_features = [f for f in features if f == 'brand']
    numerical_features = [f for f in features if f != 'brand']
    
    X = df_clean[features].copy()
    y = df_clean[target]
    
    classes = sorted(y.unique())
    
    for col in numerical_features:
        if col in df_clean.columns:
            Q1 = df_clean[col].quantile(0.05)  
            Q3 = df_clean[col].quantile(0.95) 
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            df_clean = df_clean[(df_clean[col] >= lower_bound) & (df_clean[col] <= upper_bound)]
    
    X = df_clean[features].copy()
    y = df_clean[target]
    
    return X, y, classes

def train_classification_model(X, y, classes, technique='decision_tree'):
    categorical_mask = [col == 'brand' for col in X.columns]
    categorical_indices = [i for i, x in enumerate(categorical_mask) if x]
    numerical_indices = [i for i, x in enumerate(categorical_mask) if not x]
    
    if any(categorical_mask):
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_indices),
                ('num', RobustScaler(), numerical_indices)
            ],
            remainder='passthrough'
        )
    else:
        preprocessor = RobustScaler()
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    if technique == 'decision_tree':
        classifier = DecisionTreeClassifier(random_state=42)
        pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', classifier)
        ])
        
        param_grid = {
            'classifier__max_depth': [None, 10, 20, 30],
            'classifier__min_samples_split': [2, 5, 10],
            'classifier__min_samples_leaf': [1, 2, 4]
        }
        
    elif technique == 'svm':
        classifier = SVC(probability=True, random_state=42)
        pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', classifier)
        ])
        
        param_grid = {
            'classifier__C': [0.1, 1, 10, 100],
            'classifier__gamma': ['scale', 'auto'],
            'classifier__kernel': ['rbf', 'linear']
        }
    
    grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring='accuracy', n_jobs=-1)
    grid_search.fit(X_train, y_train)
    
    best_model = grid_search.best_estimator_
    
    y_train_pred = best_model.predict(X_train)
    y_test_pred = best_model.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_test_pred)
    
    precision = precision_score(y_test, y_test_pred, average='weighted', zero_division=0)
    recall = recall_score(y_test, y_test_pred, average='weighted', zero_division=0)
    
    cm = confusion_matrix(y_test, y_test_pred, labels=classes)
    
    print(classification_report(y_test, y_test_pred, target_names=classes))
    
    return {
        'pipeline': best_model,
        'X_train': X_train,
        'X_test': X_test,
        'y_train': y_train,
        'y_test': y_test,
        'y_train_pred': y_train_pred,
        'y_test_pred': y_test_pred,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'confusion_matrix': cm
    }

def save_classification_model(model_data, target, features, technique, model_id, classes):
    model_path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
    
    with open(model_path, 'wb') as f:
        pickle.dump({
            'pipeline': model_data['pipeline'],
            'features': features,
            'target': target,
            'technique': technique,
            'accuracy': model_data['accuracy'],
            'precision': model_data['precision'],
            'recall': model_data['recall'],
            'classes': classes
        }, f)
    
    return model_id

def load_classification_model(model_id):
    model_path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
    
    if not os.path.exists(model_path):
        return None
    
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    return model_data

def predict_class(inputs, model_data):
    features = model_data['features']
    pipeline = model_data['pipeline']
    classes = model_data['classes']
    
    input_values = [inputs[feature] for feature in features]
    input_df = pd.DataFrame([input_values], columns=features)
    
    prediction = pipeline.predict(input_df)[0]
    
    return prediction

def preprocess_clustering_data(df, features):
    df_clean = df.copy()
    
    for col in features:
        if col in df_clean.columns:
            Q1 = df_clean[col].quantile(0.05)  
            Q3 = df_clean[col].quantile(0.95)  
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            df_clean = df_clean[(df_clean[col] >= lower_bound) & (df_clean[col] <= upper_bound)]
    
    X = df_clean[features].copy()
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    return X_scaled, df_clean, scaler

def find_optimal_clusters(X, max_clusters=10, technique='kmeans'):
    silhouette_scores = []
    inertia_values = []
    range_clusters = range(2, min(max_clusters + 1, len(X)))
    
    for n_clusters in range_clusters:
        if technique == 'kmeans':
            model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        else:  
            model = AgglomerativeClustering(
                n_clusters=n_clusters,
                metric='euclidean',
                linkage='ward'
            )
            
        labels = model.fit_predict(X)
        
        if len(X) > n_clusters:
            silhouette_scores.append(silhouette_score(X, labels))
            if technique == 'kmeans':
                inertia_values.append(model.inertia_)
    
    optimal_clusters = range_clusters[silhouette_scores.index(max(silhouette_scores))] if silhouette_scores else 3
    
    return {
        'optimal_clusters': optimal_clusters,
        'silhouette_scores': silhouette_scores,
        'inertia_values': inertia_values,
        'range_clusters': list(range_clusters)
    }

def run_kmeans_clustering(X, n_clusters=3):
    n_clusters = min(n_clusters, len(X) - 1)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X)
    
    silhouette_avg = silhouette_score(X, cluster_labels) if len(X) > n_clusters else 0
    
    centroids = kmeans.cluster_centers_
    
    return {
        'labels': cluster_labels,
        'centroids': centroids,
        'silhouette_score': silhouette_avg,
        'inertia': kmeans.inertia_
    }

def run_hierarchical_clustering(X, n_clusters=3):
    n_clusters = min(n_clusters, len(X) - 1)
    
    hierarchical = AgglomerativeClustering(
        n_clusters=n_clusters,
        metric='euclidean', 
        linkage='ward'  
    )
    
    cluster_labels = hierarchical.fit_predict(X)
    silhouette_avg = silhouette_score(X, cluster_labels) if len(X) > n_clusters else 0
    
    centroids = np.zeros((n_clusters, X.shape[1]))
    for i in range(n_clusters):
        mask = cluster_labels == i
        if np.any(mask):
            centroids[i] = np.median(X[mask], axis=0)
    
    return {
        'labels': cluster_labels,
        'centroids': centroids,
        'silhouette_score': silhouette_avg
    }

def save_clustering_model(model_data, features, group_by, technique, model_id):
    model_path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
    
    with open(model_path, 'wb') as f:
        pickle.dump({
            'features': features,
            'group_by': group_by,
            'technique': technique,
            'silhouette_score': model_data['silhouette_score'],
            'labels': model_data['labels'],
            'centroids': model_data['centroids']
        }, f)
    
    return model_id

def load_clustering_model(model_id):
    model_path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
    
    if not os.path.exists(model_path):
        return None
    
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    return model_data