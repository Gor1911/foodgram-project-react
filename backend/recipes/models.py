from colorfield.fields import ColorField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(max_length=settings.MAX_CHAR_LENGTH,
                            unique=True)
    color = ColorField(unique=True)
    slug = models.SlugField(max_length=settings.MAX_SLUG_LENGTH,
                            unique=True)

    class Meta:
        ordering = ('name',)


class Ingredient(models.Model):
    name = models.CharField(
        max_length=settings.MAX_CHAR_LENGTH, unique=True)
    measurement_unit = models.CharField(
        max_length=settings.MAX_CHAR_LENGTH, )

    class Meta:
        ordering = ('name',)
        unique_together = ('name', 'measurement_unit')


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
    )
    name = models.CharField(max_length=settings.MAX_CHAR_LENGTH)
    image = models.ImageField(
        upload_to='food/recipe',
        default=None,
    )
    text = models.TextField()
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
    )
    pub_date = models.DateTimeField(auto_now_add=True)
    cooking_time = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(
                limit_value=settings.MIN_SMALL_INT_VALUE),
            MaxValueValidator(
                limit_value=settings.MAX_SMALL_INT_VALUE)
        ]
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientsAmount',
        related_name="recipes",
    )

    class Meta:
        ordering = ('-pub_date',)


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
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(
                limit_value=settings.MIN_SMALL_INT_VALUE),
            MaxValueValidator(
                limit_value=settings.MAX_SMALL_INT_VALUE)
        ]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient')
        ]


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe')
        ]


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe_cart')
        ]
