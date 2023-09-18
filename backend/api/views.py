from django.http import HttpResponse
from djoser.views import UserViewSet
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly
)

from api.permissions import IsOwnerOrReadOnly
from users.models import Follow
from recipes.models import (
    Favorite,
    Ingredient,
    IngredientsAmount,
    Recipe,
    ShoppingCart,
    Tag
)

from api.filters import RecipeFilter, IngredientFilter
from api.pagination import Pagination
from api.serializers import (
    FollowSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeReadSerializer,
    TagSerializer,
    UsersSerializer
)

User = get_user_model()


class CustomUsersViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer
    pagination_class = Pagination
    permission_classes = (AllowAny,)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        pages = self.paginate_queryset(request.user.follower.all())
        serializer = FollowSerializer(pages,
                                      many=True,
                                      context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id):
        follower = self.get_object()
        user = request.user
        if request.method == 'POST':
            if follower == user:
                return Response({'message':
                                 'Вы не можете подписаться на себя'},
                                status=status.HTTP_400_BAD_REQUEST)
            if Follow.objects.filter(user=user, author=follower).exists():
                return Response({'message':
                                 'Вы уже подписаны на этого пользователя'},
                                status=status.HTTP_400_BAD_REQUEST)
            follow = Follow.objects.create(user=user,
                                           author=follower,)
            serializer = FollowSerializer(follow)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        deleted, _ = Follow.objects.filter(
            user=user,
            author=follower).delete()
        if deleted == 0:
            return Response(
                {'message': 'Объекта подписки не существует'},
                status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Вы отписались'},
                        status=status.HTTP_204_NO_CONTENT)


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (IngredientFilter,)
    search_fields = ('^name',)


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsOwnerOrReadOnly,)
    pagination_class = Pagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in ('POST', 'PATCH'):
            return RecipeCreateSerializer
        return RecipeReadSerializer

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        if request.method == 'POST':
            favorite = Favorite.objects.filter(
                user=user,
                recipe=recipe).first()
            if favorite:
                return Response(
                    {'message': 'Рецепт уже добавлен в избранное'},
                    status=status.HTTP_400_BAD_REQUEST)
            Favorite.objects.create(user=user, recipe=recipe)
            return Response(
                {'message': 'Рецепт добавлен в избранное'},
                status=status.HTTP_201_CREATED)
        deleted, _ = Favorite.objects.filter(
            user=user, recipe=recipe).delete()
        if deleted:
            return Response(
                {'message': 'Рецепт удален из избранного'},
                status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {'message': 'Рецепт не был в избранном'},
                status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        user = request.user
        try:
            recipe = Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            return Response(
                {'message': 'Рецепт не существует'},
                status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'message': 'Рецепт уже добавлен в список покупок'},
                    status=status.HTTP_400_BAD_REQUEST)
            else:
                ShoppingCart.objects.create(user=user, recipe=recipe)
                return Response(
                    {'message': 'Рецепт добавлен в список покупок'},
                    status=status.HTTP_201_CREATED)
        shopping_cart_item = get_object_or_404(
            ShoppingCart,
            user=user,
            recipe=recipe)
        shopping_cart_item.delete()
        return Response(
            {'message': 'Рецепт удален из списка покупок'},
            status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart_items = ShoppingCart.objects.filter(user=user)

        def generate_shopping_cart_data(items):
            data = {}
            for item in items:
                recipe = item.recipe
                if recipe not in data:
                    data[recipe] = []
                ingredients_amounts = IngredientsAmount.objects.filter(
                    recipe=recipe)
                for ingredient_amount in ingredients_amounts:
                    ingredient_data = {
                        'name': ingredient_amount.ingredient.name,
                        'amount': ingredient_amount.amount,
                    }
                    data[recipe].append(ingredient_data)
            return data
        shopping_cart_data = generate_shopping_cart_data(shopping_cart_items)

        def generate_response_text(data):
            lines = []
            for recipe, ingredients in data.items():
                lines.append(f'Рецепт: {recipe.name}')
                for ingredient in ingredients:
                    lines.append(f'  Ингредиенты: {ingredient["name"]}')
                    lines.append(f'  Количество: {ingredient["amount"]}')
                lines.append('')
            return '\n'.join(lines)
        response_text = generate_response_text(shopping_cart_data)
        filename = 'Список покупок.txt'
        response = HttpResponse(response_text, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
