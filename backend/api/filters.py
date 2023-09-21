from django.contrib.auth import get_user_model
from django_filters.rest_framework import (
    FilterSet,
    BooleanFilter,
    AllValuesMultipleFilter
)
from rest_framework.filters import SearchFilter

from recipes.models import Recipe


User = get_user_model()


class RecipeFilter(FilterSet):

    tags = AllValuesMultipleFilter(field_name='tags__slug',
                                   label='tags')
    is_favorited = BooleanFilter(method='get_is_favorited')
    is_in_shopping_cart = BooleanFilter(method='get_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('author',
                  'tags',
                  'is_favorited',
                  'is_in_shopping_cart',)

    def get_is_favorited(self, queryset, name, value):
        if value and not self.request.user.is_anonymous:
            return queryset.filter(favorite__user=self.request.user)
        return queryset

    def get_is_in_shopping_cart(self, queryset, name, value):
        if value and not self.request.user.is_anonymous:
            return queryset.filter(shopping_cart__user=self.request.user)
        return queryset


class IngredientFilter(SearchFilter):
    search_param = 'name'
