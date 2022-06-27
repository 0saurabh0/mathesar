from django_filters import rest_framework as filters

from rest_framework import status, viewsets
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.decorators import action

from mathesar.api.pagination import DefaultLimitOffsetPagination
from mathesar.api.serializers.queries import QuerySerializer
from mathesar.models.query import Query

class QueryViewSet(CreateModelMixin, UpdateModelMixin, RetrieveModelMixin, ListModelMixin, viewsets.GenericViewSet):
    serializer_class = QuerySerializer
    pagination_class = DefaultLimitOffsetPagination
    filter_backends = (filters.DjangoFilterBackend,)

    def get_queryset(self):
        return Query.objects.all().order_by('-created_at')

    @action(methods=['get'], detail=True)
    def columns(self, request, pk=None):
        query = self.get_object()
        output_cols = query.get_output_columns_described()
        return Response(output_cols)

    @action(methods=['get'], detail=True)
    def records(self, request, pk=None):
        query = self.get_object()
        records = query.get_records()
        return Response(records)
