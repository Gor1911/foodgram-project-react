from django.db import transaction

from django.core.validators import MaxValueValidator, MinValueValidator
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework.exceptions import ValidationError

from django.contrib.auth import get_user_model

from rest_framework.serializers import (
    CharField,
    IntegerField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    ReadOnlyField,
    SerializerMethodField,
)

from recipes.models import (
    Ingredient,
    IngredientsAmount,
    Recipe,
    Tag,
    Favorite,
    ShoppingCart
)
from users.models import Follow

User = get_user_model()


class IsSubscribedMixin:
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.author.follower.filter(user=obj.user).exists()
        return False


class UsersSerializer(UserSerializer):

    is_subscribed = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user,
                author=obj).exists()
        return False


class CreateUserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'first_name',
            'last_name',
            'username',
            'email',
            'password',
        )
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class FollowRecipeSerializer(ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class FollowSerializer(IsSubscribedMixin, ModelSerializer):
    id = IntegerField(source='author.id')
    email = ReadOnlyField(source='author.email')
    username = CharField(source='author.username')
    first_name = CharField(source='author.first_name')
    last_name = CharField(source='author.last_name')
    is_subscribed = SerializerMethodField()
    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'recipes',
            'is_subscribed',
            'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        # if request: AttributeError:
        # 'NoneType' object has no attribute 'GET'
        recipes_limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj.author)
        if recipes_limit:
            recipes = recipes[:(int(recipes_limit))]
        return FollowRecipeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()


class TagSerializer(ModelSerializer):

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class ShowIngredientsInRecipeSerializer(ModelSerializer):

    id = ReadOnlyField(source="ingredient.id")
    name = ReadOnlyField(source="ingredient.name")
    measurement_unit = ReadOnlyField(source="ingredient.measurement_unit")

    class Meta:
        model = IngredientsAmount
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount',
        )


class RecipeReadSerializer(ModelSerializer):

    author = UsersSerializer(read_only=True)
    ingredients = ShowIngredientsInRecipeSerializer(
        many=True,
        source='ingredient_amount',
    )
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = SerializerMethodField()
    # image = Base64ImageField()
    is_in_shopping_cart = SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'ingredients',
            'tags',
            'is_favorited',
            'name',
            'image',
            'text',
            'cooking_time',
            'is_in_shopping_cart',
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        user = (request.user if request
                and request.user.is_authenticated else None)
        return bool(
            request and user and obj.favorite.filter(user=user).exists())

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        user = (request.user if request
                and request.user.is_authenticated else None)
        return bool(
            request and user
            and obj.shopping_cart.filter(user=user).exists())


class IngredientCreateSerializer(ModelSerializer):

    id = IntegerField()
    # id = PrimaryKeyRelatedField(
    # queryset=Ingredient.objects.all(), many=True)
    # рецепт не создается
    amount = IntegerField(min_value=1, max_value=100)

    class Meta:
        model = IngredientsAmount
        fields = ('id', 'amount',)


class RecipeCreateSerializer(ModelSerializer):

    author = UserSerializer(read_only=True)
    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    ingredients = IngredientCreateSerializer(many=True)
    image = Base64ImageField()
    cooking_time = IntegerField(validators=[
        MinValueValidator(1,
                          message='''Время приготовления
                          должно быть не менее 1 минуты'''),
        MaxValueValidator(600,
                          message='''Время приготовления
                          не должно превышать 600 минут''')
    ])

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'author',
            'tags',
            'ingredients',
            'image',
            'text',
            'cooking_time',
        )

    def validate(self, data):
        image = data.get('image')
        tags = data.get('tags')
        ingredients = data.get('ingredients')
        if not image:
            raise ValidationError(
                'Необходимо изображение блюда')
        if not tags:
            raise ValidationError(
                'Необходим хотя бы один тег')
        if len(tags) != len(set(tags)):
            raise ValidationError(
                'Нельзя добавлять дублирующиеся теги')
        if not ingredients or len(ingredients) == 0:
            raise ValidationError(
                'Необходимо указать хотя бы один ингредиент.')
        ingredient_ids = set()
        for ingredient_data in ingredients:
            ingredient_id = ingredient_data.get('id')
            if ingredient_id in ingredient_ids:
                raise ValidationError(
                    f'''Ингредиент с id
                    {ingredient_id} уже добавлен в этот рецепт.''')
            ingredient_ids.add(ingredient_id)
        return data

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        validated_data['author'] = self.context['request'].user
        recipe = Recipe.objects.create(**validated_data)
        self.create_recipe_ingredients(recipe, ingredients)
        recipe.tags.set(tags)
        return recipe

    def create_recipe_ingredients(self, recipe, ingredients):
        ingredients_to_create = []
        for ingredient_data in ingredients:
            ingredient_id = ingredient_data.get('id')
            amount = ingredient_data.get('amount')
            if amount < 1:
                raise ValidationError(
                    f'''Количество ингредиента с id {ingredient_id}
                    должно быть больше 0.''')
            try:
                ingredient = Ingredient.objects.get(id=ingredient_id)
            except Ingredient.DoesNotExist:
                raise ValidationError(
                    f'''Ингредиент с id {ingredient_id}
                    не существует.''')

            ingredients_to_create.append(
                IngredientsAmount(recipe=recipe,
                                  ingredient=ingredient,
                                  amount=amount))
        with transaction.atomic():
            IngredientsAmount.objects.bulk_create(ingredients_to_create)

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_recipe_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class FavoriteRecipeSerializer(ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('id',
                  'user',
                  'recipe')


class ShoppingListSerializer(ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('id',
                  'user',
                  'recipe')
