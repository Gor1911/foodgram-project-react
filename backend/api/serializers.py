from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction

from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserSerializer
from rest_framework.exceptions import ValidationError
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
    ShoppingCart,
)

from users.models import Follow

User = get_user_model()


class IsSubscribedMixin:

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and obj.author.follower.filter(user=obj.user).exists())


class UsersSerializer(UserSerializer, IsSubscribedMixin):

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
        return False  # не работает с миксином выше


class FollowRecipeSerializerShortInfo(ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class FollowSerializer(IsSubscribedMixin, ModelSerializer,):
    id = IntegerField(source='author.id')
    email = ReadOnlyField(source='author.email')
    username = CharField(source='author.username')
    first_name = CharField(source='author.first_name')
    last_name = CharField(source='author.last_name')
    # не работает если удалить
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
        recipes_limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj.author)
        if recipes_limit:
            recipes = recipes[:(int(recipes_limit))]
        return FollowRecipeSerializerShortInfo(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()

    def validate(self, data):
        user = self.context['request'].user
        author = self.instance.author if self.instance else None
        if author == user:
            raise ValidationError(
                {'message': 'Вы не можете подписаться на себя'})
        if Follow.objects.filter(user=user, author=author).exists():
            raise ValidationError(
                {'message': 'Вы уже подписаны на этого пользователя'})
        return data


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
        return (
            request and request.user
            and obj.favorite.filter(user=request.user).exists())

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (
            request and request.user
            and obj.shopping_cart.filter(user=request.user).exists())


class IngredientCreateSerializer(ModelSerializer):

    id = PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = IntegerField(min_value=1, max_value=32767)

    class Meta:
        model = IngredientsAmount
        fields = ('id',
                  'amount',)


class RecipeCreateSerializer(ModelSerializer):

    author = UserSerializer(read_only=True)
    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    ingredients = IngredientCreateSerializer(many=True)
    image = Base64ImageField()
    cooking_time = IntegerField(validators=[
        MinValueValidator(1, message=('Время должно быть не менее 1 минуты')),
        MaxValueValidator(32767,
                          message=('Время не должно превышать 32767 минут')
                          )])

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
        if not ingredients:
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
        self.create_recipe_ingredients(recipe=recipe, ingredients=ingredients)
        recipe.tags.set(tags)
        return recipe

    @transaction.atomic
    def create_recipe_ingredients(self, ingredients, recipe):
        ingredients_to_create = []
        for ingredient in ingredients:
            ingredients_to_create.append(
                IngredientsAmount(
                    ingredient=ingredient['id'],
                    recipe=recipe,
                    amount=ingredient['amount'],
                )
            )
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


class FollowerSerializer(ModelSerializer):
    class Meta:
        model = Follow
        fields = ('user', 'author')

    def create(self, validated_data):
        user = validated_data['user']
        author = validated_data['author']
        if Follow.objects.filter(user=user, author=author).exists():
            raise ValidationError("Вы уже подписаны на этого пользователя")
        subscription = Follow.objects.create(user=user, author=author)
        return subscription


class UserShowFollowigSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = ('id',
                  'username',
                  'email',
                  'first_name',
                  'last_name')

    subscriptions = SerializerMethodField()

    def get_subscriptions(self, obj):
        user = self.context['request'].user
        subscriptions = Follow.objects.filter(
            user=user).values_list(
                'author_id', flat=True)
        return User.objects.filter(id__in=subscriptions)


class FavoriteRecipeSerializer(ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user',
                  'recipe')

    def to_representation(self, instance):
        recipe = FollowRecipeSerializerShortInfo(instance.recipe).data
        return recipe

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError("Этот рецепт уже есть в вашем избранном.")
        return data


class ShoppingListSerializer(ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user',
                  'recipe')

    def to_representation(self, instance):
        recipe = FollowRecipeSerializerShortInfo(instance.recipe).data
        return recipe

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError("Этот рецепт уже есть в вашей корзине.")
        return data


class FollowingSerializer(ModelSerializer):
    class Meta:
        model = Follow
        fields = '__all__'

    def validate(self, data):
        user = self.context['request'].user
        author = data.get('author')
        if user == author:
            raise ValidationError("Вы не можете подписаться на себя.")
        return data
