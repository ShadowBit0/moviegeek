import uuid
import json

from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse

from moviegeeks.models import Movie, Genre, ItemDetail

# All 20 real categories from the dataset, translated to Russian.
CATEGORIES_RU = {
    'Binders & Binding Systems': 'Папки и переплётные системы',
    'Book Covers & Book Accessories': 'Обложки для книг',
    'Calendars, Planners & Personal Organizers': 'Календари и ежедневники',
    'Carrying Cases': 'Сумки и чехлы',
    'Cutting & Measuring Devices': 'Режущие и измерительные инструменты',
    'Desk Accessories & Workspace Organizers': 'Настольные аксессуары и органайзеры',
    'Education & Crafts': 'Обучение и рукоделие',
    'Envelopes, Mailers & Shipping Supplies': 'Конверты и почтовые принадлежности',
    'Filing Products': 'Файловые принадлежности',
    'Forms, Recordkeeping & Money Handling': 'Бланки, учёт и кассовые принадлежности',
    'Labels, Indexes & Stamps': 'Этикетки, индексы и штампы',
    'Office & School Supplies': 'Канцелярские и школьные товары',
    'Office Storage Supplies': 'Принадлежности для хранения',
    'Paper': 'Бумага',
    'Presentation Boards': 'Презентационные доски',
    'Staplers & Punches': 'Степлеры и дыроколы',
    'Store Signs & Displays': 'Вывески и стенды',
    'Tape, Adhesives & Fasteners': 'Лента, клей и крепёж',
    'Time Clocks & Cards': 'Табельные часы и карты',
    'Writing & Correction Supplies': 'Письменные и корректирующие принадлежности',
}

ALLOWED_CATEGORIES = set(CATEGORIES_RU.keys())


@ensure_csrf_cookie
def index(request):
    genre_selected = request.GET.get('genre')

    page_title = 'Школьные товары'
    if genre_selected:
        selected = Genre.objects.filter(name=genre_selected).first()
        movies = selected.movies.order_by('movie_id') if selected else Movie.objects.none()
        if selected:
            page_title = CATEGORIES_RU.get(selected.name, selected.name)
    else:
        movies = Movie.objects.filter(genres__name__in=ALLOWED_CATEGORIES).distinct().order_by('movie_id')
    genres = get_genres()

    page_number = request.GET.get("page", 1)
    page, page_end, page_start = handle_pagination(movies, page_number)

    items_with_details = _attach_details(page)

    context_dict = {
        'movies': page,
        'items_with_details': items_with_details,
        'genres': genres,
        'session_id': session_id(request),
        'user_id': user_id(request),
        'pages': range(page_start, page_end),
        'page_title': page_title,
    }

    return render(request, 'moviegeek/index.html', context_dict)


def handle_pagination(movies, page_number):
    paginate_by = 60
    paginator = Paginator(movies, paginate_by)

    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page_number = 1
        page = paginator.page(page_number)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    page_number = int(page_number)
    page_start = 1 if page_number < 5 else page_number - 3
    page_end = 6 if page_number < 5 else page_number + 2
    return page, page_end, page_start


@ensure_csrf_cookie
def genre(request, genre_id):
    page_title = 'Школьные товары'
    if genre_id:
        selected = Genre.objects.filter(name=genre_id).first()
        movies = selected.movies.all().order_by('movie_id') if selected else Movie.objects.none()
        if selected:
            page_title = CATEGORIES_RU.get(selected.name, selected.name)
    else:
        movies = Movie.objects.filter(genres__name__in=ALLOWED_CATEGORIES).distinct().order_by('movie_id')

    genres = get_genres()

    page_number = request.GET.get("page", 1)
    page, page_end, page_start = handle_pagination(movies, page_number)

    items_with_details = _attach_details(page)

    context_dict = {
        'movies': page,
        'items_with_details': items_with_details,
        'genres': genres,
        'session_id': session_id(request),
        'user_id': user_id(request),
        'pages': range(page_start, page_end),
        'genre_selected': genre_id,
        'page_title': page_title,
    }

    return render(request, 'moviegeek/index.html', context_dict)


def detail(request, movie_id):
    genres = get_genres()
    movie = Movie.objects.filter(movie_id=movie_id).first()
    genre_names = []
    item = None

    if movie is not None:
        movie_genres = movie.genres.filter(name__in=ALLOWED_CATEGORIES)
        genre_names = [{'name': CATEGORIES_RU.get(g.name, g.name)} for g in movie_genres]
        item = ItemDetail.objects.filter(item_id=movie_id).first()

    # Use title_ru for display, fallback to title_en
    display_title = ''
    if movie:
        display_title = movie.title_ru if movie.title_ru else movie.title

    context_dict = {
        'movie_id': movie_id,
        'genres': genres,
        'movie_genres': genre_names,
        'movie': movie,
        'display_title': display_title,
        'item': item,
        'session_id': session_id(request),
        'user_id': user_id(request),
    }

    return render(request, 'moviegeek/detail.html', context_dict)


def item_detail_api(request, item_id):
    movie = Movie.objects.filter(movie_id=item_id).first()
    if movie is None:
        return JsonResponse({'error': 'Not found'}, status=404)

    det = ItemDetail.objects.filter(item_id=item_id).first()
    category = ''
    genre_obj = movie.genres.filter(name__in=ALLOWED_CATEGORIES).first()
    if genre_obj:
        category = CATEGORIES_RU.get(genre_obj.name, genre_obj.name)

    # Return title_ru for display
    title = movie.title_ru if movie.title_ru else movie.title

    data = {
        'id': item_id,
        'title': title,
        'title_en': movie.title,
        'category': category,
        'price': det.price if det else None,
        'average_rating': det.average_rating if det else None,
        'rating_number': det.rating_number if det else 0,
        'description_en': det.description_en if det else '',
    }
    return JsonResponse(data)


def search_for_movie(request):
    search_term = request.GET.get('q', None)

    if search_term is None:
        return redirect('/movies/')

    # Search in both title (en) and title_ru
    from django.db.models import Q
    mov = Movie.objects.filter(
        Q(title__icontains=search_term) | Q(title_ru__icontains=search_term)
    )[:60]
    genres = get_genres()

    items_with_details = _attach_details(mov)

    context_dict = {
        'genres': genres,
        'movies': mov,
        'items_with_details': items_with_details,
    }

    return render(request, 'moviegeek/search_result.html', context_dict)


def _attach_details(movies):
    """Attach price/rating from ItemDetail to a list of Movie objects."""
    movie_ids = [m.movie_id for m in movies]
    details = {d.item_id: d for d in ItemDetail.objects.filter(item_id__in=movie_ids)}
    result = []
    for m in movies:
        d = details.get(m.movie_id)
        # Use title_ru for display
        title = m.title_ru if m.title_ru else m.title
        result.append({
            'movie_id': m.movie_id,
            'title': title,
            'price': d.price if d else None,
            'average_rating': d.average_rating if d else None,
        })
    return result


def get_genres():
    """Return only curated categories with Russian names."""
    genres = Genre.objects.filter(name__in=ALLOWED_CATEGORIES).order_by('name')
    result = []
    for g in genres:
        result.append({
            'name': g.name,
            'name_ru': CATEGORIES_RU.get(g.name, g.name),
        })
    return result


def session_id(request):
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid1())
    return request.session["session_id"]


def user_id(request):
    uid = request.GET.get("user_id")

    if uid:
        request.session['user_id'] = uid

    if "user_id" not in request.session:
        request.session['user_id'] = 'AFKZENTNBQ7A7V7UXW5JJI6UGRYQ'

    return request.session['user_id']
