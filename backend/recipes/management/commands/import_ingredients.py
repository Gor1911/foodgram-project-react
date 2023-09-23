import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        file_path = 'ingredients.json'
        DATA_ROOT = os.path.join(settings.BASE_DIR, 'data')
        full_file_path = os.path.join(DATA_ROOT, file_path)

        with open(full_file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            ingredients_to_create = []

            for ingredient in data:
                ingredient_name = ingredient['name']
                measurement_unit = ingredient['measurement_unit']
                ingredients_to_create.append(
                    Ingredient(name=ingredient_name,
                               measurement_unit=measurement_unit))
            Ingredient.objects.bulk_create(ingredients_to_create)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Создано{len(ingredients_to_create)} ингредиентов'))
