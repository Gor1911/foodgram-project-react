from django.http import HttpResponse
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)

from users.models import Follow, User
from recipes.models import (Favorite,
                            Ingredient,
                            IngredientsAmount,
                            Recipe,
                            ShoppingCart,
                            Tag)

from api.filters import RecipeFilter
from api.pagination import Pagination
from api.serializers import (FollowSerializer,
                             IngredientSerializer,
                             RecipeCreateSerializer,
                             RecipeSerializer,
                             TagSerializer,
                             UsersSerializer)


class UsersViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer
    pagination_class = Pagination
    filter_backends = (SearchFilter,)
    search_fields = ('username', 'email')
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
        if request.method == 'POST':
            follower = self.get_object()
            user = request.user
            follow = Follow.objects.create(user=user,
                                           author=follower,)
            serializer = FollowSerializer(follow)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            follower = self.get_object()
            user = request.user
            Follow.objects.filter(user=user,
                                  author=follower).delete()
            return Response({'message': 'Вы отписались'},
                            status=status.HTTP_204_NO_CONTENT)


class TagViewSet(ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = None


class IngredientViewSet(ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (SearchFilter,)
    pagination_class = None


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = Pagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeSerializer
        else:
            if self.request.method == 'POST' or self.request.method == 'PATCH':
                return RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            created = Favorite.objects.get_or_create(
                user=user,
                recipe=recipe)
            if created:
                return Response(
                    {'message': 'Рецепт добавлен в избранное'},
                    status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            deleted = Favorite.objects.filter(user=user,
                                              recipe=recipe).delete()
            if deleted:
                return Response(
                    {'message': 'Рецепт удален из избранного'},
                    status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            if not ShoppingCart.objects.filter(user=user,
                                               recipe=recipe
                                               ).exists():
                ShoppingCart.objects.create(
                    user=user, recipe=recipe)
                return Response(
                    {'message': 'Рецепт добавлен в список покупок'},
                    status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
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
        filename = 'Список покупок'
        with open(filename, 'w') as file:
            for item in shopping_cart_items:
                file.write(f'Рецепт: {item.recipe.name}\n')
                ingredients_amounts = IngredientsAmount.objects.filter(
                    recipe=item.recipe)
                for ingredient_amount in ingredients_amounts:
                    file.write(f'''
                               Ингридиенты: {ingredient_amount.ingredient.name}
                               Количество: {ingredient_amount.amount}\n''')
        with open(filename, 'r') as file:
            response = file.read()
        response = HttpResponse(response, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
