"""
Train ALS, BPR (via implicit library) and SVD models.
Saves trained models to ./models/ directory.
"""
import os
import pickle

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prs_project.settings")
import django
django.setup()

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import svds
import implicit

from analytics.models import Rating


def check_gpu():
    try:
        import implicit.gpu
        return True
    except Exception:
        return False


def load_ratings():
    print("Loading ratings from DB...")
    data = list(Rating.objects.all().values('user_id', 'movie_id', 'rating'))
    df = pd.DataFrame(data)
    print(f"Loaded {len(df)} ratings")

    df['user_id'] = df['user_id'].astype('category')
    df['movie_id'] = df['movie_id'].astype('category')

    user_map = dict(enumerate(df['user_id'].cat.categories))
    item_map = dict(enumerate(df['movie_id'].cat.categories))
    user_to_idx = {v: k for k, v in user_map.items()}
    item_to_idx = {v: k for k, v in item_map.items()}

    sparse_item_user = coo_matrix(
        (df['rating'].astype(float),
         (df['movie_id'].cat.codes, df['user_id'].cat.codes))
    ).tocsr()

    sparse_user_item = coo_matrix(
        (df['rating'].astype(float),
         (df['user_id'].cat.codes, df['movie_id'].cat.codes))
    ).tocsr()

    return sparse_item_user, sparse_user_item, user_map, item_map, user_to_idx, item_to_idx


def train_als(sparse_item_user, save_dir, use_gpu=False):
    print("\n=== Training ALS ===")
    os.makedirs(save_dir, exist_ok=True)

    model = implicit.als.AlternatingLeastSquares(
        factors=64,
        regularization=0.1,
        iterations=15,
        use_gpu=use_gpu,
    )
    confidence = (sparse_item_user * 1.0).astype(np.float32)
    model.fit(confidence)

    # Convert GPU model to CPU for serialization
    if use_gpu:
        model = model.to_cpu()

    with open(os.path.join(save_dir, 'als_model.pkl'), 'wb') as f:
        pickle.dump(model, f)
    print(f"ALS model saved to {save_dir}")
    return model


def train_bpr(sparse_item_user, save_dir, use_gpu=False):
    print("\n=== Training BPR ===")
    os.makedirs(save_dir, exist_ok=True)

    model = implicit.bpr.BayesianPersonalizedRanking(
        factors=64,
        learning_rate=0.05,
        regularization=0.01,
        iterations=50,
        use_gpu=use_gpu,
    )
    binary = (sparse_item_user > 0).astype(np.float32)
    model.fit(binary)

    if use_gpu:
        model = model.to_cpu()

    with open(os.path.join(save_dir, 'bpr_model.pkl'), 'wb') as f:
        pickle.dump(model, f)
    print(f"BPR model saved to {save_dir}")
    return model


def train_svd(sparse_user_item, save_dir, k=64):
    print("\n=== Training SVD ===")
    os.makedirs(save_dir, exist_ok=True)

    U, sigma, Vt = svds(sparse_user_item.astype(float), k=min(k, min(sparse_user_item.shape) - 1))

    np.save(os.path.join(save_dir, 'U.npy'), U)
    np.save(os.path.join(save_dir, 'sigma.npy'), sigma)
    np.save(os.path.join(save_dir, 'Vt.npy'), Vt)

    user_ratings_mean = np.array(sparse_user_item.mean(axis=1)).flatten()
    np.save(os.path.join(save_dir, 'user_ratings_mean.npy'), user_ratings_mean)

    print(f"SVD model saved to {save_dir} (k={U.shape[1]})")


def save_mappings(user_map, item_map, user_to_idx, item_to_idx, save_dir):
    os.makedirs(save_dir, exist_ok=True)
    with open(os.path.join(save_dir, 'user_map.pkl'), 'wb') as f:
        pickle.dump(user_map, f)
    with open(os.path.join(save_dir, 'item_map.pkl'), 'wb') as f:
        pickle.dump(item_map, f)
    with open(os.path.join(save_dir, 'user_to_idx.pkl'), 'wb') as f:
        pickle.dump(user_to_idx, f)
    with open(os.path.join(save_dir, 'item_to_idx.pkl'), 'wb') as f:
        pickle.dump(item_to_idx, f)
    print(f"Mappings saved ({len(user_map)} users, {len(item_map)} items)")


if __name__ == '__main__':
    use_gpu = check_gpu()
    print(f"GPU available: {use_gpu}")

    sparse_item_user, sparse_user_item, user_map, item_map, user_to_idx, item_to_idx = load_ratings()

    base_dir = './models'
    save_mappings(user_map, item_map, user_to_idx, item_to_idx, base_dir)

    train_als(sparse_item_user, os.path.join(base_dir, 'als'), use_gpu=use_gpu)
    train_bpr(sparse_item_user, os.path.join(base_dir, 'bpr'), use_gpu=use_gpu)
    train_svd(sparse_user_item, os.path.join(base_dir, 'svd'))

    print("\n=== All models trained! ===")
