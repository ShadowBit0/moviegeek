"""ALS recommender using implicit library."""
import os
import pickle
from decimal import Decimal

import numpy as np

from analytics.models import Rating
from recs.base_recommender import base_recommender

MODEL_DIR = './models'


class ALSRecs(base_recommender):

    def __init__(self):
        self.model = None
        self.user_to_idx = None
        self.item_map = None
        self.item_to_idx = None
        self._load()

    def _load(self):
        try:
            with open(os.path.join(MODEL_DIR, 'als', 'als_model.pkl'), 'rb') as f:
                self.model = pickle.load(f)
            with open(os.path.join(MODEL_DIR, 'user_to_idx.pkl'), 'rb') as f:
                self.user_to_idx = pickle.load(f)
            with open(os.path.join(MODEL_DIR, 'item_map.pkl'), 'rb') as f:
                self.item_map = pickle.load(f)
            with open(os.path.join(MODEL_DIR, 'item_to_idx.pkl'), 'rb') as f:
                self.item_to_idx = pickle.load(f)
        except FileNotFoundError:
            self.model = None

    def recommend_items(self, user_id, num=6):
        if self.model is None or user_id not in self.user_to_idx:
            return []

        user_idx = self.user_to_idx[user_id]
        user_vec = self.model.user_factors[user_idx]
        scores = self.model.item_factors @ user_vec

        # Exclude already rated
        rated_indices = set(
            self.item_to_idx[r['movie_id']]
            for r in Rating.objects.filter(user_id=user_id).values('movie_id')
            if r['movie_id'] in self.item_to_idx
        )
        for ri in rated_indices:
            scores[ri] = -999

        top_idx = np.argsort(-scores)[:num]
        return [(self.item_map[idx], {'prediction': Decimal(float(scores[idx]))})
                for idx in top_idx if idx in self.item_map]

    def predict_score(self, user_id, item_id):
        return Decimal(0)
