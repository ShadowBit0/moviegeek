"""SVD recommender using scipy truncated SVD."""
import os
import pickle
from decimal import Decimal

import numpy as np

from analytics.models import Rating
from recs.base_recommender import base_recommender

MODEL_DIR = './models'


class SVDRecs(base_recommender):

    def __init__(self):
        self.U = None
        self.sigma = None
        self.Vt = None
        self.user_ratings_mean = None
        self.user_to_idx = None
        self.item_map = None
        self.item_to_idx = None
        self._load()

    def _load(self):
        try:
            svd_dir = os.path.join(MODEL_DIR, 'svd')
            self.U = np.load(os.path.join(svd_dir, 'U.npy'))
            self.sigma = np.load(os.path.join(svd_dir, 'sigma.npy'))
            self.Vt = np.load(os.path.join(svd_dir, 'Vt.npy'))
            self.user_ratings_mean = np.load(os.path.join(svd_dir, 'user_ratings_mean.npy'))

            with open(os.path.join(MODEL_DIR, 'user_to_idx.pkl'), 'rb') as f:
                self.user_to_idx = pickle.load(f)
            with open(os.path.join(MODEL_DIR, 'item_map.pkl'), 'rb') as f:
                self.item_map = pickle.load(f)
            with open(os.path.join(MODEL_DIR, 'item_to_idx.pkl'), 'rb') as f:
                self.item_to_idx = pickle.load(f)

            # Precompute predicted ratings: U * diag(sigma) * Vt
            self.predicted = self.U @ np.diag(self.sigma) @ self.Vt
        except FileNotFoundError:
            self.predicted = None

    def recommend_items(self, user_id, num=6):
        if self.predicted is None or user_id not in self.user_to_idx:
            return []

        user_idx = self.user_to_idx[user_id]

        # Get predicted scores for this user
        user_scores = self.predicted[user_idx] + self.user_ratings_mean[user_idx]

        # Exclude already rated items
        rated = set(
            Rating.objects.filter(user_id=user_id)
            .values_list('movie_id', flat=True)
        )

        # Get top items
        top_indices = np.argsort(user_scores)[::-1]

        result = []
        for idx in top_indices:
            item_id = self.item_map.get(idx)
            if item_id and item_id not in rated:
                result.append((item_id, {'prediction': Decimal(float(user_scores[idx]))}))
            if len(result) >= num:
                break

        return result

    def predict_score(self, user_id, item_id):
        if self.predicted is None:
            return Decimal(0)
        if user_id not in self.user_to_idx or item_id not in self.item_to_idx:
            return Decimal(0)
        user_idx = self.user_to_idx[user_id]
        item_idx = self.item_to_idx[item_id]
        return Decimal(float(self.predicted[user_idx, item_idx] + self.user_ratings_mean[user_idx]))
