from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework.serializers import (CharField,
                                        IntegerField,
                                        ModelSerializer,
                                        PrimaryKeyRelatedField,
                                        ReadOnlyField,
                                        SerializerMethodField,
                                        )

from recipes.models import (Ingredient,
                            IngredientsAmount,
                            Recipe,
                            Tag,
                            )
from users.models import User, Follow


class UsersSerializer(UserSerializer):

    is_subscribed = SerializerMethodField()

    class Meta:
        model = User
        fields = ('email',
                  'id',
                  'username',
                  'first_name',
                  'last_name',
                  'is_subscribed',
                  )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, author=obj).exists()


class CreateUserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ('id',
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
        user = User.objects.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            )
        return user


class FollowRecipeSerializer(ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id',
                  'name',
                  'image',
                  'cooking_time',
                  )


class FollowSerializer(ModelSerializer):
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
        fields = ('email',
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
        if request:
            recipes_limit = request.GET.get('recipes_limit')
            recipes = Recipe.objects.filter(author=obj.author)
            if recipes_limit:
                recipes_limit = int(recipes_limit)
                recipes = recipes[:recipes_limit]
            return FollowRecipeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()

    def get_is_subscribed(self, obj):
        return obj.author.follower.filter(user=obj.user).exists()


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


class RecipeSerializer(ModelSerializer):

    author = UsersSerializer(read_only=True)
    ingredients = ShowIngredientsInRecipeSerializer(
        many=True,
        source='ingredient_amount',)
    tags = TagSerializer(many=True)
    is_favorited = SerializerMethodField()
    image = Base64ImageField()
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
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.favorite.filter(user=user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.shopping_cart.filter(user=user).exists()


class IngredientCreateSerializer(ModelSerializer):

    id = IntegerField()

    class Meta:
        model = IngredientsAmount
        fields = ('id', 'amount',)


class RecipeCreateSerializer(ModelSerializer):

    name = CharField(max_length=200)
    author = UserSerializer(read_only=True)
    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    ingredients = IngredientCreateSerializer(many=True)
    image = Base64ImageField()
    cooking_time = IntegerField()

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

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        for ingredient_data in ingredients:
            ingredient = Ingredient.objects.get(id=ingredient_data['id'])
            IngredientsAmount.objects.create(recipe=recipe,
                                             ingredient=ingredient,
                                             amount=ingredient_data['amount'])
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get('cooking_time',
                                                   instance.cooking_time)
        if 'image' in validated_data:
            instance.image = validated_data['image']
        if 'tags' in validated_data:
            tags = validated_data.pop('tags')
            instance.tags.set(tags)
        if 'ingredients' in validated_data:
            ingredients_data = validated_data.pop('ingredients')
            instance.ingredients.clear()
            for ingredient_data in ingredients_data:
                ingredient = Ingredient.objects.get(id=ingredient_data['id'])
                IngredientsAmount.objects.create(
                    recipe=instance,
                    ingredient=ingredient,
                    amount=ingredient_data['amount'])
        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeSerializer(instance,
                                context=self.context).data
