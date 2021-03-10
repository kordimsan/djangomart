import json
import base64
from functools import wraps

from django.http import HttpResponse, JsonResponse
from django.views import View

from .models import Item, Review
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate, login



from marshmallow import Schema, ValidationError, fields, post_load
from marshmallow.validate import Length, Range

class ItemSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True, validate=Length(1, 64))
    description = fields.Str(required=True, validate=Length(1, 1024))
    price = fields.Int(required=True, validate=Range(1, 1000000), strict=True)

    @post_load
    def make(self, data):
        return Item(**data)


class ReviewSchema(Schema):
    id = fields.Int(dump_only=True)
    grade = fields.Int(required=True, validate=Range(1, 10), strict=True)
    text = fields.Str(required=True, validate=Length(1, 1024))

    @post_load
    def make(self, data):
        return Review(**data)


def basicauth(view_func):
    """Декоратор реализующий HTTP Basic AUTH."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == 'basic':
                    token = base64.b64decode(auth[1].encode('ascii'))
                    username, password = token.decode('utf-8').split(':')
                    user = authenticate(username=username, password=password)
                    if user is not None and user.is_active:
                        request.user = user
                        return view_func(request, *args, **kwargs)

        response = HttpResponse(status=401)
        response['WWW-Authenticate'] = 'Basic realm="Somemart staff API"'
        return response
    return _wrapped_view

def staff_required(view_func):
    """Декоратор проверяющший наличие флага is_staff у пользователя."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        response = HttpResponse(status=403)
        return response
    return _wrapped_view


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(basicauth, name='dispatch')
@method_decorator(staff_required, name='dispatch')
class AddItemView(View):
    """View для создания товара."""

    def post(self, request):
        try:
            document = json.loads(request.body)
            schema = ItemSchema(strict=True)
            item = schema.load(document).data
            item.save()
        except (json.JSONDecodeError, ValidationError):
            return HttpResponse(status=400)

        return JsonResponse({'id': item.pk}, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class PostReviewView(View):
    """View для создания отзыва о товаре."""

    def post(self, request, item_id):
        try:
            item = Item.objects.get(pk=item_id)
            document = json.loads(request.body)
            schema = ReviewSchema(strict=True)
            review = schema.load(document).data
            review.item = item
            review.save()
        except Item.DoesNotExist:
            return HttpResponse(status=404)
        except (json.JSONDecodeError, ValidationError):
            return HttpResponse(status=400)

        return JsonResponse({'id': review.pk}, status=201)


class GetItemView(View):
    """View для получения информации о товаре.

    Помимо основной информации выдает последние отзывы о товаре, не более 5
    штук.
    """

    def get(self, request, item_id):
        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            return HttpResponse(status=404)

        schema = ItemSchema()
        data = schema.dump(item).data
        query = Review.objects.filter(item=item).order_by('-id')
        reviews = query[:5]
        schema = ReviewSchema(many=True)
        data['reviews'] = schema.dump(reviews).data
        return JsonResponse(data, status=200)
