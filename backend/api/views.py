from django.http import HttpResponse
from djoser.views import UserViewSet
from django.contrib.auth import get_user_model
from django.db.models import Sum

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
from api.pagination import LimitPagePagination
from api.serializers import (
    FollowSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeReadSerializer,
    TagSerializer,
    UsersSerializer,
    FavoriteRecipeSerializer,
    ShoppingListSerializer,
    # FollowingSerializer
)

User = get_user_model()


class CustomUsersViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer
    pagination_class = LimitPagePagination
    permission_classes = (AllowAny,)

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        pages = self.paginate_queryset(request.user.follower.all())
        serializer = FollowSerializer(pages,
                                      many=True,
                                      context={'request': self.request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id):
        follower = self.get_object()
        user = request.user
        if request.method == 'POST':
            follow = Follow.objects.create(user=user,
                                           author=follower,)
            # не могу с этим разобраться (
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
    pagination_class = LimitPagePagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in ('POST', 'PATCH'):
            return RecipeCreateSerializer
        return RecipeReadSerializer

    def create_item(self, request, pk, serializer_class, success_message):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        data = {'user': user.id, 'recipe': recipe.id}
        serializer = serializer_class(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': success_message},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def delete_item(self, request, pk, model_class, success_message,
                    not_found_message):
        user = request.user
        try:
            recipe = Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            return Response({'message': not_found_message},
                            status=status.HTTP_400_BAD_REQUEST)
        item = get_object_or_404(model_class, user=user, recipe=recipe)
        item.delete()
        return Response({'message': success_message},
                        status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        if request.method == 'POST':
            return self.create_item(request, pk, FavoriteRecipeSerializer,
                                    'Рецепт добавлен в избранное')
        return self.delete_item(request, pk, Favorite,
                                'Рецепт удален из избранного',
                                'Рецепт не существует')

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self.create_item(request, pk, ShoppingListSerializer,
                                    'Рецепт добавлен в список покупок')
        return self.delete_item(request, pk, ShoppingCart,
                                'Рецепт удален из списка покупок',
                                'Рецепт не существует')

    def generate_shopping_cart_file(self, user):
        shopping_cart_items = ShoppingCart.objects.filter(user=user)
        filename = 'Список покупок.txt'
        with open(filename, 'w') as file:
            for item in shopping_cart_items:
                file.write(f'Рецепт: {item.recipe.name}\n')
                ingredients_amounts = IngredientsAmount.objects.filter(
                    recipe=item.recipe
                ).values(
                    'ingredient__name',
                    'ingredient__measurement_unit').annotate(
                    total_amount=Sum('amount'))
                for ingr_amount in ingredients_amounts:
                    file.write(
                        f'Ингр.: {ingr_amount["ingredient__name"]}\n'
                        f'Кол.: {ingr_amount["total_amount"]} '
                        f'{ingr_amount["ingredient__measurement_unit"]}\n\n')
        return filename

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        filename = self.generate_shopping_cart_file(user)
        with open(filename, 'r') as file:
            response = file.read()
        response = HttpResponse(response, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
