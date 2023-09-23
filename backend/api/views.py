from django.http import HttpResponse

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import LimitPagePagination
from api.permissions import IsOwnerOrReadOnly
from api.serializers import (
    FavoriteRecipeSerializer,
    FollowSerializer,
    FollowingSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeReadSerializer,
    ShoppingListSerializer,
    TagSerializer,
    UsersSerializer,
)
from recipes.models import (
    Favorite,
    Ingredient,
    IngredientsAmount,
    Recipe,
    ShoppingCart,
    Tag,
)
from users.models import Follow

User = get_user_model()


class UsersViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer
    pagination_class = LimitPagePagination
    permission_classes = (AllowAny,)

    def get_permissions(self):
        if self.action == 'me':
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        pages = self.paginate_queryset(User.objects.filter(
            following__user=request.user))
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
            data = {'user': user.id, 'author': follower.id}
            serializer = FollowingSerializer(data=data,
                                             context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            instance = FollowSerializer(
                follower,
                context={'request': request}
            )
            return Response(instance.data,
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
    permission_classes = (IsOwnerOrReadOnly,
                          IsAuthenticatedOrReadOnly)
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
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({serializer.data},
                        status=status.HTTP_201_CREATED)

    def delete_item(self, request, pk, model_class,):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted_items_count, _ = model_class.objects.filter(
            user=user, recipe=recipe).delete()
        if deleted_items_count > 0:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'message': 'Item not found'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        if request.method == 'POST':
            return self.create_item(request, pk, FavoriteRecipeSerializer,
                                    'Рецепт добавлен в избранное')
        return self.delete_item(request, pk, Favorite,
                                'Рецепт удален из избранного',
                                'Рецепт не существует')

    def generate_shopping_cart_data(self, user):
        shopping_cart_items = ShoppingCart.objects.filter(user=user)
        data = ""
        for item in shopping_cart_items:
            data += f'Рецепт: {item.recipe.name}\n'
            ingredients_amounts = IngredientsAmount.objects.filter(
                recipe=item.recipe
            ).values(
                'ingredient__name',
                'ingredient__measurement_unit'
            ).annotate(
                total_amount=Sum('amount')
            )
            for ingr_amount in ingredients_amounts:
                data += (
                    f'Ингр.: {ingr_amount["ingredient__name"]}\n'
                    f'Кол.: {ingr_amount["total_amount"]} '
                    f'{ingr_amount["ingredient__measurement_unit"]}\n\n'
                )
        return data

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self.create_item(request,
                                    pk,
                                    ShoppingListSerializer,
                                    'Рецепт добавлен в список покупок')
        return self.delete_item(request,
                                pk,
                                ShoppingCart,
                                'Рецепт удален из списка покупок',
                                'Рецепт не существует')

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        data = self.generate_shopping_cart_data(user)
        response = HttpResponse(data,
                                content_type='text/plain')
        filename = "Список"
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
