import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from django import forms
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.forms.models import model_to_dict

from .models import Item, Review

GOODS_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'properties': {
        'title': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 64,
        },
        'description': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 1024,
        },
        'price': {
            'type': 'integer',
            'minimum': 1,
            'maximum': 1000000,
        },
    },
    'required': ['title', 'description', 'price'],
}

REVIEW_SCHEMA = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'properties': {
        'text': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 1024,
        },
        'grade': {
            'type': 'integer',
            'minimum': 1,
            'maximum': 10,
        },
    },
    'required': ['text', 'grade'],
}


@method_decorator(csrf_exempt, name='dispatch')
class AddItemView(View):
    """View для создания товара."""

    def post(self, request):

        try:
            document = json.loads(request.body)
            validate(document, GOODS_SCHEMA)
        except (json.JSONDecodeError, ValidationError):
            return HttpResponse(status=400)

        item = Item(title=document['title'],
                    description=document['description'],
                    price=document['price'])
        item.save()
        return JsonResponse({'id': item.pk}, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class PostReviewView(View):
    """View для создания отзыва о товаре."""

    def post(self, request, item_id):

        try:
            document = json.loads(request.body)
            validate(document, REVIEW_SCHEMA)
            item = Item.objects.get(id=item_id)
            review = Review(text=document['text'],
                            grade=document['grade'],
                            item_id=item.pk)
            review.save()
        except Item.DoesNotExist:
            return HttpResponse(status=404)
        except (json.JSONDecodeError, ValidationError):
            return HttpResponse(status=400)

        return JsonResponse({'id': review.id}, status=201)


class GetItemView(View):
    """View для получения информации о товаре.

    Помимо основной информации выдает последние отзывы о товаре, не более 5
    штук.
    """

    def get(self, request, item_id):

        try:
            item = Item.objects.prefetch_related('review_set').get(id=item_id)
        except Item.DoesNotExist:
            return HttpResponse(status=404)

        items = model_to_dict(item)
        reviews = []

        for i in item.review_set.all():
            reviews.append(model_to_dict(i))

        reviews = sorted(reviews, key=lambda review: review['id'], reverse=True)[:5]
        items['reviews'] = reviews
        return JsonResponse(items, status=200)
