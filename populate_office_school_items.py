import os
import csv

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prs_project.settings")

import django
django.setup()

from tqdm import tqdm
from moviegeeks.models import Movie, Genre, ItemDetail


def get_category(categories_en):
    """Extract 3rd category from pipe-separated categories string."""
    parts = [p.strip() for p in categories_en.split('|')]
    if len(parts) >= 3:
        return parts[2]
    return parts[-1] if parts else 'Other'


def delete_db():
    print("Truncating existing data...")
    Movie.objects.all().delete()
    Genre.objects.all().delete()
    ItemDetail.objects.all().delete()
    print("Done truncating.")


def populate():
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'office_school_items.csv')

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} items to load.")

    for row in tqdm(rows):
        asin = row['parent_asin']
        title_en = row.get('title_en', '')
        title_ru = row.get('title_ru', '')
        categories_en = row.get('categories_en', '')
        category = get_category(categories_en)

        movie, _ = Movie.objects.get_or_create(movie_id=asin)
        movie.title = title_en
        movie.title_ru = title_ru
        movie.year = None
        movie.save()

        genre, _ = Genre.objects.get_or_create(name=category)
        movie.genres.add(genre)

        try:
            price = float(row['price']) if row.get('price') else None
        except (ValueError, TypeError):
            price = None

        try:
            avg_rating = float(row['average_rating']) if row.get('average_rating') else None
        except (ValueError, TypeError):
            avg_rating = None

        try:
            rating_number = int(row['rating_number']) if row.get('rating_number') else 0
        except (ValueError, TypeError):
            rating_number = 0

        ItemDetail.objects.update_or_create(
            item_id=asin,
            defaults={
                'description_en': row.get('description_en', ''),
                'features_en': row.get('features_en', ''),
                'price': price,
                'average_rating': avg_rating,
                'rating_number': rating_number,
                'categories_en': categories_en,
            }
        )

    print(f"Loaded {Movie.objects.count()} items, {Genre.objects.count()} categories.")


if __name__ == '__main__':
    print("Starting Office & School Items population...")
    delete_db()
    populate()
    print("Done.")
