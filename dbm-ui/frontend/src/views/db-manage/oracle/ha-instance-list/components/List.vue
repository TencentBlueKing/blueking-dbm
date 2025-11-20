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
  <div class="oracle-ha-instance-list-page">
    <div class="operation-box mb-12">
      <DbSearchSelect
        :data="searchSelectData"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="getOracleHaInstanceList"
      releate-url-query
      :row-class="setRowClass"
      :settings="settings"
      show-settings
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @setting-change="updateTableSettings">
      <BkTableColumn
        field="id"
        fixed="left"
        label="ID"
        :width="80">
      </BkTableColumn>
      <BkTableColumn
        field="instance_address"
        fixed="left"
        :label="t('实例')"
        :min-width="200">
        <template #default="{ data }: { data: OraclehaInstanceModel }">
          <TextOverflowLayout>
            <AuthButton
              action-id="oracle_view"
              :permission="data.permission.oracle_view"
              :resource="data.cluster_id"
              text
              theme="primary"
              @click="() => handleToDetails(data)">
              {{ data.instance_address }}
            </AuthButton>
            <template #append>
              <BkTag
                v-if="data.isNew"
                class="ml-4"
                size="small"
                theme="success">
                NEW
              </BkTag>
            </template>
          </TextOverflowLayout>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="status"
        :label="t('状态')"
        :width="140">
        <template #default="{ data }: { data: OraclehaInstanceModel }">
          <DbStatus :theme="data.statusInfo.theme">{{ data.statusInfo.text }}</DbStatus>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="role"
        :label="t('部署角色')"
        :width="140">
      </BkTableColumn>
      <BkTableColumn
        field="bk_sub_zone"
        :label="t('所在园区')"
        :width="140">
        <template #default="{ data }: { data: OraclehaInstanceModel }">
          {{ data.bk_sub_zone || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="master_domain"
        :label="t('所属集群')"
        :min-width="250">
        <template #default="{ data }: { data: OraclehaInstanceModel }">
          <TextOverflowLayout>
            {{ data.master_domain }}
            <template #append>
              <DbIcon
                v-bk-tooltips="t('复制所属集群')"
                class="copy-btn"
                type="copy"
                @click="() => execCopy(data.master_domain, t('复制成功，共n条', { n: 1 }))" />
            </template>
          </TextOverflowLayout>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="cluster_name"
        :label="t('集群名称')"
        :min-width="180">
        <template #default="{ data }: { data: OraclehaInstanceModel }">
          <TextOverflowLayout>
            <AuthButton
              action-id="oracle_view"
              :permission="data.permission.oracle_view"
              :resource="data.cluster_id"
              text
              theme="primary"
              @click="() => handleToClusterDetails(data)">
              {{ data.cluster_name }}
            </AuthButton>
            <template #append>
              <DbIcon
                v-bk-tooltips="t('复制集群名称')"
                class="copy-btn"
                type="copy"
                @click="() => execCopy(data.cluster_name, t('复制成功，共n条', { n: 1 }))" />
            </template>
          </TextOverflowLayout>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="create_at"
        :label="t('部署时间')"
        :width="240">
        <template #default="{ data }: { data: OraclehaInstanceModel }">
          {{ data.createAtDisplay || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        v-if="!isStretchLayoutOpen"
        fixed="right"
        :label="t('操作')"
        :width="100">
        <template #default="{ data }: { data: OraclehaInstanceModel }">
          <AuthButton
            action-id="oracle_view"
            :permission="data.permission.oracle_view"
            :resource="data.cluster_id"
            text
            theme="primary"
            @click="() => handleToDetails(data)">
            {{ t('查看详情') }}
          </AuthButton>
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import OraclehaInstanceModel from '@services/model/oracle/oracle-ha-instance';
  import { getOracleHaInstanceList } from '@services/source/oracleHaCluster';

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings } from '@hooks';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, getSearchSelectorParams } from '@utils';

  const instanceData = defineModel<{ clusterId: number; instanceAddress: string }>('instanceData');

  let isInit = true;
  const fetchData = (loading?: boolean) => {
    const params = getSearchSelectorParams(searchValue.value);
    tableRef.value.fetchData(params, { ...sortValue }, loading);
    isInit = false;
  };

  const router = useRouter();
  const { t } = useI18n();
  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const {
    clearSearchValue,
    // columnAttrs,
    // columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
    sortValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['role'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    fetchDataFn: () => fetchData(isInit),
    isCluster: false,
    searchType: ClusterTypes.ORACLE_PRIMARY_STANDBY,
  });

  const searchSelectData = computed(() => [
    {
      id: 'instance',
      multiple: true,
      name: t('IP 或 IP:Port'),
    },
    {
      id: 'domain',
      multiple: true,
      name: t('访问入口'),
    },
    {
      id: 'name',
      name: t('集群名称'),
    },
    {
      children: [
        {
          id: 'running',
          name: t('正常'),
        },
        {
          id: 'unavailable',
          name: t('异常'),
        },
        {
          id: 'loading',
          name: t('重建中'),
        },
      ],
      id: 'status',
      multiple: true,
      name: t('状态'),
    },
    {
      children: searchAttrs.value.role,
      id: 'role',
      multiple: true,
      name: t('部署角色'),
    },
    {
      id: 'port',
      name: t('端口'),
    },
  ]);

  const tableRef = ref();

  // 设置行样式
  const setRowClass = (row: OraclehaInstanceModel) => {
    const classList = [row.isNew ? 'is-new-row' : ''];

    if (
      row.cluster_id === instanceData.value?.clusterId &&
      row.instance_address === instanceData.value.instanceAddress
    ) {
      classList.push('is-selected-row');
    }

    return classList.filter((cls) => cls).join(' ');
  };

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.ORACLE_HA_INSTANCE_SETTINGS, {
    checked: ['id', 'instance_address', 'status', 'role', 'bk_sub_zone', 'master_domain', 'cluster_name', 'create_at'],
    disabled: ['instance_address', 'master_domain'],
  });

  /**
   * 查看实例详情
   */
  const handleToDetails = (data: OraclehaInstanceModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      clusterId: data.cluster_id,
      instanceAddress: data.instance_address,
    };
  };

  /**
   * 查看集群详情
   */
  const handleToClusterDetails = (data: OraclehaInstanceModel) => {
    router.push({
      name: 'OracleHaClusterList',
      query: {
        id: data.cluster_id,
      },
    });
  };
</script>

<style lang="less">
  @import '@styles/mixins.less';

  .oracle-ha-instance-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .vxe-cell {
      .copy-btn {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    tr:hover {
      .copy-btn {
        display: inline-block !important;
      }
    }

    .operation-box {
      display: flex;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }
  }
</style>
