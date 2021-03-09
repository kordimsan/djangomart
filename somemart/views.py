import json

from django.http import HttpResponse, JsonResponse
from django.views import View

from .models import Item, Review
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# from jsonschema import validate
# from jsonschema.exceptions import ValidationError

# schema = {
#     "type" : "object",
#     "properties" : {
#         "title" : {"type" : "string"},
#         "description" : {"type" : "string"},
#         "price" : {"type" : "number"},
#     },
# }

from marshmallow import Schema, fields
from marshmallow import ValidationError
from marshmallow.validate import Length, Range

class ItemSchema(Schema):
    title = fields.Str(validate=Length(1,64),required=True)
    description = fields.Str(validate=Length(1,1024),required=True)
    price = fields.Int(validate=Range(1,1000000),required=True)

class ReviewSchema(Schema):
    text = fields.Str(validate=Length(1,1024),required=True)
    grade = fields.Int(validate=Range(1,10),required=True)


@method_decorator(csrf_exempt, name='dispatch')
class AddItemView(View):
    """View для создания товара."""

    def post(self, request):
        try:
            document = json.loads(request.body)
            schema = ItemSchema(strict=True)
            data = schema.load(document)
            item = Item.objects.create(**data.data)
            return JsonResponse({'id': item.id}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'errors': 'Invalid JSON'}, status=400)
        except ValidationError:
            return JsonResponse({'errors': 'Запрос не прошел валидацию'}, status=400)
        except Exception as e:
            return JsonResponse({'errors': e}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PostReviewView(View):
    """View для создания отзыва о товаре."""

    def post(self, request, item_id):
        try:
            document = json.loads(request.body)
            schema = ReviewSchema(strict=True)
            data = schema.load(document)
            item = Item.objects.get(pk=item_id)
            text = data.data.get('text')
            grade = data.data.get('grade')
            review = Review.objects.create(
                text=text,
                grade=grade,
                item=item
            )
            return JsonResponse({'id': review.id}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'errors': 'Invalid JSON'}, status=400)
        except ValidationError:
            return JsonResponse({'errors': 'Запрос не прошел валидацию'}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({'errors': f'товара с таким {item_id} не существует.'}, status=404)
        except Exception as e:
            return JsonResponse({'errors': e}, status=500)


class GetItemView(View):
    """View для получения информации о товаре.

    Помимо основной информации выдает последние отзывы о товаре, не более 5
    штук.
    """

    def get(self, request, item_id):
        try:
            item = Item.objects.get(pk=item_id)
            data = {      
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "price": item.price,
                "reviews": [{
                    'id': r.id,
                    'text': r.text,
                    'grade': r.grade
                } for r in Review.objects.filter(item__pk=item_id).order_by('-id')[:5]]
            }
            return JsonResponse(data, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'errors': 'Invalid JSON'}, status=400)
        except ValidationError:
            return JsonResponse({'errors': 'Запрос не прошел валидацию'}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({'errors': f'товара с таким {item_id} не существует.'}, status=404)
        except Exception as e:
            return JsonResponse({'errors': e}, status=500)
