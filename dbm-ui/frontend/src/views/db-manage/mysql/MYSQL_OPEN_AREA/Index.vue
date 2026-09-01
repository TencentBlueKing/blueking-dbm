<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkAlert
    closable
    :title="t('开区模板：通过开区模板，可以快速创建集群开区')" />
  <div class="header-action mt-16 mb-16">
    <AuthButton
      action-id="mysql_openarea_manage"
      class="w-88"
      theme="primary"
      @click="handleGoCreate">
      {{ t('新建') }}
    </AuthButton>
    <BkInput
      v-model="searchKey"
      clearable
      :placeholder="t('请输入模板关键字')"
      style="width: 390px" />
  </div>
  <DbTable
    ref="tableRef"
    :custom-sort-method="columnSortChange"
    :data-source="getList"
    row-key="id">
    <TableColumn
      col-key="config_name"
      :title="t('模板名称')" />
    <TableColumn
      col-key="cluster_type"
      :title="t('类型')">
      <template #default="{ row: data }: { row: OpenareaTemplateModel }">
        {{ data.cluster_type === 'tendbha' ? t('主从') : t('单节点') }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="source_cluster.immute_domain"
      :title="t('源集群')" />
    <TableColumn
      col-key="updater"
      :title="t('更新人')" />
    <TableColumn
      col-key="update_at"
      sorter
      :title="t('更新时间')"
      :width="180">
      <template #default="{ row: data }: { row: OpenareaTemplateModel }">
        {{ data.updateAtDisplay || '--' }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="operation"
      :title="t('操作')"
      :width="140">
      <template #default="{ row: data }: { row: OpenareaTemplateModel }">
        <RouterLink
          :to="{
            name: 'MySQLOpenareaCreate',
            params: {
              id: data.id,
            },
            query: {
              from: route.name as string,
            },
          }">
          {{ t('开区') }}
        </RouterLink>
        <AuthRouterLink
          action-id="mysql_openarea_manage"
          class="ml-16"
          :permission="data.permission.mysql_openarea_manage"
          :resource="data.id"
          :to="{
            name: 'MySQLOpenareaTemplateEdit',
            params: {
              id: data.id,
            },
            query: {
              from: route.name as string,
            },
          }">
          {{ t('编辑') }}
        </AuthRouterLink>
        <AuthTemplate
          action-id="mysql_openarea_manage"
          :permission="data.permission.mysql_openarea_manage"
          :resource="data.id">
          <DbPopconfirm
            :confirm-handler="() => handleRemove(data)"
            :content="t('删除操作无法撤回，请谨慎操作！')"
            :title="t('确认删除该模板？')">
            <BkButton
              class="ml-16"
              text
              theme="primary">
              {{ t('删除') }}
            </BkButton>
          </DbPopconfirm>
        </AuthTemplate>
      </template>
    </TableColumn>
  </DbTable>
</template>

<script setup lang="ts">
  import type { TableSort } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';
  import { type Mysql } from '@services/model/ticket/ticket';
  import { getList, remove } from '@services/source/openarea';

  import { useDebouncedRef, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { messageSuccess } from '@utils';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const searchKey = useDebouncedRef(route.query.config_name as string);
  const tableRef = ref();
  const baseParams = {
    cluster_type: [ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE].join(','),
  };

  useTicketDetail<Mysql.OpenArea>(TicketTypes.MYSQL_OPEN_AREA, {
    onSuccess(ticketDetail) {
      router.push({
        name: 'MySQLOpenareaCreate',
        params: {
          id: ticketDetail.details.config_id,
        },
        query: {
          from: route.name as string,
          ticketId: route.query.ticketId,
        },
      });
    },
  });

  watch(searchKey, () => {
    nextTick(() => {
      tableRef.value.fetchData({
        ...baseParams,
        config_name: searchKey.value,
      });
    });
  });

  const fetchData = () => {
    tableRef.value.fetchData({
      ...baseParams,
    });
  };

  // 表头排序
  const columnSortChange = (sort: TableSort) => {
    let desc = '';
    if (!Array.isArray(sort) && sort) {
      desc = sort.descending ? `-${sort.sortBy}` : sort.sortBy;
    }
    tableRef.value.fetchData({
      ...baseParams,
      desc,
    });
  };

  const handleGoCreate = () => {
    router.push({
      name: 'MySQLOpenareaTemplateCreate',
    });
  };

  const handleRemove = (data: OpenareaTemplateModel) =>
    remove(data).then(() => {
      messageSuccess(t('删除成功'));
      fetchData();
    });

  onMounted(() => {
    fetchData();
  });

  defineExpose({
    routerBack() {
      router.push({
        name: 'MysqlToolboxIndex',
      });
    },
  });
</script>

<style lang="less" scoped>
  .header-action {
    display: flex;
    justify-content: space-between;
  }
</style>
