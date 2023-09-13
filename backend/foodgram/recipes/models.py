from django.db import models

from users.models import User


class Tag(models.Model):

    name = models.CharField(max_length=150)
    color = models.CharField(max_length=15)
    slug = models.SlugField(max_length=150, unique=True)


class Ingredient(models.Model):

    name = models.CharField(max_length=200,)
    measurement_unit = models.CharField(max_length=200,)


class Recipe(models.Model):

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        )
    name = models.CharField(max_length=200,)
    image = models.ImageField(upload_to='food/recipe',
                              null=True, default=None,
                              )
    text = models.TextField()
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        )
    pub_date = models.DateTimeField(auto_now_add=True,)
    cooking_time = models.PositiveIntegerField()
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientsAmount',
        related_name="recipes",)


class IngredientsAmount(models.Model):

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_amount',
        )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_amount',
        )
    amount = models.PositiveIntegerField()


class Favorite(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite',
        )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorite',
        )


class ShoppingCart(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        )
