import os
import json

from django.core.management.base import BaseCommand
from django.conf import settings

from recipes.models import Ingredient


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str)

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        DATA_ROOT = os.path.join(settings.BASE_DIR, 'data')
        full_file_path = os.path.join(DATA_ROOT, file_path)

        with open(full_file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            for ingredient in data:
                ingredient_name = ingredient['name']
                measurement_unit = ingredient['measurement_unit']

                ingredient, created = Ingredient.objects.get_or_create(
                    name=ingredient_name,
                    measurement_unit=measurement_unit
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(
                        f'Created ingredient: {ingredient_name}'))
                else:
                    self.stdout.write(
                        self.style.SUCCESS
                        (f'Ingredient already exists: {ingredient_name}'))
