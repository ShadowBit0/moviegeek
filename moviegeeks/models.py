from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Movie(models.Model):
    movie_id = models.CharField(max_length=32, unique=True, primary_key=True)
    title = models.CharField(max_length=512)
    title_ru = models.CharField(max_length=512, blank=True, default='')
    year = models.IntegerField(null=True)
    genres = models.ManyToManyField(Genre, related_name='movies', db_table='movie_genre')

    def __str__(self):
        return self.title_ru or self.title


class ItemDetail(models.Model):
    item_id = models.CharField(max_length=32, unique=True, primary_key=True)
    description_en = models.TextField(blank=True)
    features_en = models.TextField(blank=True)
    price = models.FloatField(null=True, blank=True)
    average_rating = models.FloatField(null=True, blank=True)
    rating_number = models.IntegerField(default=0)
    categories_en = models.CharField(max_length=512, blank=True)

    class Meta:
        db_table = 'item_detail'

    def __str__(self):
        return self.item_id
