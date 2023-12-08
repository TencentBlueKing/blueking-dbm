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
  <div class="mysql-ha-instance-list-page">
    <div class="operation-box">
      <AuthButton
        action-id="resource_manage"
        class="mb-16"
        theme="primary"
        @click="handleApply">
        {{ t('实例申请') }}
      </AuthButton>
      <DbSearchSelect
        v-model="searchSelectValue"
        class="mb-16"
        :data="searchSelectData"
        :placeholder="t('实例_域名_IP_端口_状态')"
        unique-select
        @change="handleSearchChnage" />
    </div>
    <div
      class="table-wrapper"
      :class="{'is-shrink-table': isStretchLayoutOpen}">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getTendbhaInstanceList"
        releate-url-query
        :row-class="setRowClass"
        :settings="settings"
        @clear-search="handleClearSearch"
        @setting-change="updateTableSettings" />
    </div>
  </div>
</template>

<script setup lang="tsx">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import { getTendbhaInstanceList } from '@services/source/tendbha';

  import {
    useCopy,
    useStretchLayout,
    useTableSettings,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
    UserPersonalSettings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import {
    getSearchSelectorParams,
    isRecentDays,
  } from '@utils';

  interface ColumnData {
    cell: string,
    data: TendbhaInstanceModel
  }

  const instanceData = defineModel<{instanceAddress: string, clusterId: number}>('instanceData');

  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const copy = useCopy();
  const { t } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const searchSelectData = [
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('实例'),
      id: 'instance_address',
    },
    {
      name: t('域名'),
      id: 'domain',
    },
    {
      name: 'IP',
      id: 'ip',
    },
    {
      name: t('端口'),
      id: 'port',
    },
    {
      name: t('状态'),
      id: 'status',
      children: Object.values(clusterInstStatus).map(item => ({ id: item.key, name: item.text })),
    },
  ];

  const tableRef = ref();
  const searchSelectValue = ref<ISearchValue[]>([]);

  const columns = computed(() => {
    const list = [
      {
        label: t('实例'),
        field: 'instance_address',
        fixed: 'left',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell, data }: ColumnData) => (
        <div style="display: flex; align-items: center;">
          <div class="text-overflow" v-overflow-tips>
            <auth-button
              action-id="mysql_view"
              resource={data.cluster_id}
              permission={data.permission.mysql_view}
              text
              theme="primary"
              onClick={() => handleToDetails(data)}>
              {cell}
            </auth-button>
          </div>
          {
            isRecentDays(data.create_at, 24 * 3)
            && <span class="glob-new-tag ml-4" data-text="NEW" />
          }
        </div>
      ),
      },
      {
        label: t('集群名称'),
        field: 'cluster_name',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell, data }: ColumnData) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <bk-button
                text
                theme="primary"
                onClick={() => handleToClusterDetails(data)}>
                {cell}
              </bk-button>
            ),
            append: () => (
              <db-icon
                v-bk-tooltips={t('复制集群名称')}
                type="copy"
                class="copy-btn"
                onClick={() => copy(cell)} />
            ),
          }}
        </TextOverflowLayout>
      ),
      },
      {
        label: t('状态'),
        field: 'status',
        width: 140,
        render: ({ cell }: { cell: ClusterInstStatus }) => {
          const info = clusterInstStatus[cell] || clusterInstStatus.unavailable;
          return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
        },
      },
      {
        label: t('主访问入口'),
        field: 'master_domain',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell }: ColumnData) => (
          <TextOverflowLayout>
            {{
              default: () => cell,
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制主访问入口')}
                  type="copy"
                  class="copy-btn"
                  onClick={() => copy(cell)} />
              ),
            }}
          </TextOverflowLayout>
        ),
      },
      {
        label: t('从访问入口'),
        field: 'slave_domain',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell }: ColumnData) => (
          <TextOverflowLayout>
            {{
              default: () => cell,
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制主访问入口')}
                  type="copy"
                  class="copy-btn"
                  onClick={() => copy(cell)} />
              ),
            }}
          </TextOverflowLayout>
        ),
      },
      {
        label: t('部署角色'),
        field: 'role',
      },
      {
        label: t('部署时间'),
        field: 'create_at',
        width: 200,
      },
      {
        label: t('操作'),
        fixed: 'right',
        width: 140,
        render: ({ data }: { data: TendbhaInstanceModel }) => (
          <auth-button
            action-id="mysql_view"
            permission={data.permission.mysql_view}
            resource={data.cluster_id}
            theme="primary"
            text
            onClick={() => handleToDetails(data)}>
            { t('查看详情') }
          </auth-button>
        ),
      },
    ];

    if (isStretchLayoutOpen.value) {
      list.pop();
    }

    return list;
  });

  // 设置行样式
  const setRowClass = (row: TendbhaInstanceModel) => {
    const classList = [isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : ''];

    if (
      row.cluster_id === instanceData.value?.clusterId
      && row.instance_address === instanceData.value.instanceAddress
    ) {
      classList.push('is-selected-row');
    }

    return classList.filter(cls => cls).join(' ');
  };

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: columns.value.filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: ['instance_address', 'master_domain'].includes(item.field as string),
    })),
    checked: columns.value.map(item => item.field).filter(key => !!key) as string[],
    showLineHeight: false,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.TENDBHA_INSTANCE_SETTINGS, defaultSettings);

  let isInit = true;
  const fetchData = (loading?:boolean) => {
    const params = getSearchSelectorParams(searchSelectValue.value);
    tableRef.value.fetchData(params, {}, loading);
    isInit = false;
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyHa',
      query: {
        bizId: globalBizsStore.currentBizId,
      },
    });
  };

  /**
   * 按条件过滤
   */
  const handleSearchChnage = () => {
    fetchData(isInit);
  };

  const handleClearSearch = () => {
    searchSelectValue.value = [];
  };

  /**
   * 查看实例详情
   */
  const handleToDetails = (data: TendbhaInstanceModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      instanceAddress: data.instance_address,
      clusterId: data.cluster_id,
    };
  };

  /**
   * 查看集群详情
   */
  const handleToClusterDetails = (data: TendbhaInstanceModel) => {
    router.push({
      name: 'DatabaseTendbha',
      query: {
        id: data.cluster_id,
      },
    });
  };
</script>

<style lang="less">
  @import "@styles/mixins.less";

  .mysql-ha-instance-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .cell {
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

    .is-shrink-table {
      .bk-table-body {
        overflow: hidden auto;
      }
    }

    .operation-box {
      display: flex;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 320px;
        min-width: 320px;
        margin-left: auto;
      }
    }
  }


</style>
