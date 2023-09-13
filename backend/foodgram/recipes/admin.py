from django.contrib import admin

from .models import (Tag, 
                     Ingredient, 
                     Recipe,
                     IngredientsAmount,
                     Favorite,
                     ShoppingCart)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')


class IngredientInRecipe(admin.TabularInline): 
    model = Recipe.ingredients.through


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'cooking_time')
    list_filter = ('author', 'tags')
    search_fields = ('name', 'author__username')
    filter_horizontal = ('ingredients', 'tags')
    inlines = [IngredientInRecipe]
    

@admin.register(IngredientsAmount)
class IngredientsAmountAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')