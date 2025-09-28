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
      action-id="mysql_openarea_config_create"
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
    :data-source="getList"
    @column-sort="columnSortChange">
    <BkTableColumn
      field="config_name"
      :label="t('模板名称')" />
    <BkTableColumn
      field="cluster_type"
      :label="t('类型')">
      <template #default="{ data }: { data: OpenareaTemplateModel }">
        {{ data.cluster_type === 'tendbha' ? t('主从') : t('单节点') }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="source_cluster.immute_domain"
      :label="t('源集群')" />
    <BkTableColumn
      field="updater"
      :label="t('更新人')" />
    <BkTableColumn
      field="update_at"
      :label="t('更新时间')"
      sort
      :width="180">
      <template #default="{ data }: { data: OpenareaTemplateModel }">
        {{ data.updateAtDisplay || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('操作')"
      :width="140">
      <template #default="{ data }: { data: OpenareaTemplateModel }">
        <RouterLink
          :to="{
            name: 'mysqlOpenareaCreate',
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
          action-id="mysql_openarea_config_update"
          class="ml-16"
          :permission="data.permission.mysql_openarea_config_update"
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
          action-id="mysql_openarea_config_destroy"
          :permission="data.permission.mysql_openarea_config_destroy"
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
    </BkTableColumn>
  </DbTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';
  import { type Mysql } from '@services/model/ticket/ticket';
  import { getList, remove } from '@services/source/openarea';

  import { useDebouncedRef, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

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
        name: 'mysqlOpenareaCreate',
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
      tableRef.value.fetchData(
        {
          config_name: searchKey.value,
        },
        baseParams,
      );
    });
  });

  const fetchData = () => {
    tableRef.value.fetchData({}, baseParams);
  };

  // 表头排序
  const columnSortChange = (data: {
    column: {
      field: string;
      label: string;
    };
    index: number;
    type: 'asc' | 'desc' | 'null';
  }) => {
    let desc = '';
    if (data.type === 'asc') {
      desc = data.column.field;
    } else if (data.type === 'desc') {
      desc = `-${data.column.field}`;
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
</script>

<style lang="less" scoped>
  .header-action {
    display: flex;
    justify-content: space-between;
  }
</style>
