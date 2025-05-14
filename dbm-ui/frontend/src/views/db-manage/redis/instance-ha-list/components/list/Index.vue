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
  <div class="redis-instance-list-page">
    <div class="operation-box">
      <AuthButton
        action-id="redis_cluster_apply"
        class="mb-16"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DbSearchSelect
        :data="searchSelectData"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        @change="handleSearchValueChange" />
    </div>
    <div
      class="table-wrapper"
      :class="{ 'is-shrink-table': isStretchLayoutOpen }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getRedisInstances"
        releate-url-query
        :row-class="setRowClass"
        :settings="settings"
        show-settings
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @setting-change="updateTableSettings" />
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import { getRedisInstances } from '@services/source/redis';

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, getSearchSelectorParams } from '@utils';

  const instanceData = defineModel<{ clusterId: number; clusterType: string; instanceAddress: string }>('instanceData');

  const fetchData = (loading?: boolean) => {
    const params = {
      ...getSearchSelectorParams(searchValue.value),
      cluster_type: ClusterTypes.REDIS_INSTANCE,
    };
    tableRef.value.fetchData(params, { ...sortValue }, loading);
    isInit = false;
  };

  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();
  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const {
    clearSearchValue,
    columnAttrs,
    columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
    sortValue,
  } = useLinkQueryColumnSerach({
    attrs: ['role'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    fetchDataFn: () => fetchData(isInit),
    isCluster: false,
    searchType: ClusterTypes.REDIS,
  });

  let isInit = true;

  const searchSelectData = computed(() => [
    {
      id: 'instance',
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
          text: t('正常'),
          value: 'running',
        },
        {
          text: t('异常'),
          value: 'unavailable',
        },
        {
          text: t('重建中'),
          value: 'restoring',
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

  const columns = computed(() => {
    const list = [
      {
        field: 'id',
        fixed: 'left',
        label: 'ID',
        width: 80,
      },
      {
        field: 'instance_address',
        fixed: 'left',
        label: t('实例'),
        minWidth: 200,
        render: ({ data }: { data: RedisInstanceModel }) => (
          <TextOverflowLayout>
            {{
              append: () =>
                !data.isNew && (
                  <bk-tag
                    class='ml-4'
                    size='small'
                    theme='success'>
                    NEW
                  </bk-tag>
                ),
              default: () => (
                <auth-button
                  action-id='redis_view'
                  permission={data.permission.redis_view}
                  resource={data.cluster_id}
                  theme='primary'
                  text
                  onClick={() => handleToDetails(data)}>
                  {data.instance_address}
                </auth-button>
              ),
            }}
          </TextOverflowLayout>
        ),
      },
      {
        field: 'cluster_name',
        label: t('集群名称'),
        minWidth: 200,
        render: ({ data }: { data: RedisInstanceModel }) => (
          <TextOverflowLayout>
            {{
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制集群名称')}
                  class='copy-btn'
                  type='copy'
                  onClick={() => execCopy(data.cluster_name, t('复制成功，共n条', { n: 1 }))}
                />
              ),
              default: () => (
                <auth-button
                  action-id='redis_view'
                  permission={data.permission.redis_view}
                  resource={data.cluster_id}
                  theme='primary'
                  text
                  onClick={() => handleToClusterDetails(data)}>
                  {data.cluster_name}
                </auth-button>
              ),
            }}
          </TextOverflowLayout>
        ),
      },
      {
        field: 'status',
        filter: {
          checked: columnCheckedMap.value.status,
          list: [
            {
              text: t('正常'),
              value: 'running',
            },
            {
              text: t('异常'),
              value: 'unavailable',
            },
            {
              text: t('重建中'),
              value: 'restoring',
            },
          ],
        },
        label: t('状态'),
        render: ({ data }: { data: RedisInstanceModel }) => {
          const info = data.getStatusInfo;
          return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
        },
        width: 140,
      },
      {
        field: 'master_domain',
        label: t('主访问入口'),
        minWidth: 200,
        render: ({ data }: { data: RedisInstanceModel }) => (
          <TextOverflowLayout>
            {{
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制主访问入口')}
                  class='copy-btn'
                  type='copy'
                  onClick={() => execCopy(data.master_domain, t('复制成功，共n条', { n: 1 }))}
                />
              ),
              default: () => data.master_domain,
            }}
          </TextOverflowLayout>
        ),
        showOverflowTooltip: false,
      },
      // {
      //   label: t('从访问入口'),
      //   field: 'slave_domain',
      //   minWidth: 200,
      //   showOverflowTooltip: false,
      //   render: ({ data }: { data: RedisInstanceModel }) => (
      //     <TextOverflowLayout>
      //       {{
      //         default: () => data.slave_domain,
      //         append: () => (
      //           <db-icon
      //             v-bk-tooltips={t('复制主访问入口')}
      //             type="copy"
      //             class="copy-btn"
      //             onClick={() => copy(data.slave_domain)} />
      //         ),
      //       }}
      //     </TextOverflowLayout>
      //   ),
      // },
      {
        field: 'bk_sub_zone',
        label: t('所在园区'),
        render: ({ data }: { data: RedisInstanceModel }) => data.bk_sub_zone || '--',
        width: 140,
      },
      {
        field: 'role',
        filter: {
          checked: columnCheckedMap.value.role,
          list: columnAttrs.value.role,
        },
        label: t('部署角色'),
        width: 140,
      },
      {
        field: 'create_at',
        label: t('部署时间'),
        render: ({ data }: { data: RedisInstanceModel }) => data.createAtDisplay || '--',
        sort: true,
        width: 160,
      },
      {
        fixed: 'right',
        label: t('操作'),
        render: ({ data }: { data: RedisInstanceModel }) => (
          <auth-button
            action-id='redis_view'
            permission={data.permission.redis_view}
            resource={data.cluster_id}
            theme='primary'
            text
            onClick={() => handleToDetails(data)}>
            {t('查看详情')}
          </auth-button>
        ),
        width: 140,
      },
    ];

    if (isStretchLayoutOpen.value) {
      list.pop();
    }

    return list;
  });

  // 设置行样式
  const setRowClass = (row: RedisInstanceModel) => {
    const classList = [row.isNew ? 'is-new-row' : ''];

    if (
      row.cluster_id === instanceData.value?.clusterId &&
      row.instance_address === instanceData.value.instanceAddress
    ) {
      classList.push('is-selected-row');
    }

    return classList.filter((classItem) => classItem).join(' ');
  };

  // 设置用户个人表头信息
  const defaultSettings = {
    checked: columns.value.map((item) => item.field).filter((key) => !!key) as string[],
    fields: columns.value
      .filter((item) => item.field)
      .map((item) => ({
        disabled: ['instance_address', 'master_domain'].includes(item.field as string),
        field: item.field,
        label: item.label,
      })),
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const { settings, updateTableSettings } = useTableSettings(
    UserPersonalSettings.REDIS_HA_TABLE_SETTINGS,
    defaultSettings,
  );

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyRedisHa',
      query: {
        bizId: globalBizsStore.currentBizId,
      },
    });
  };

  /**
   * 查看实例详情
   */
  const handleToDetails = (data: RedisInstanceModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      clusterId: data.cluster_id,
      clusterType: data.cluster_type,
      instanceAddress: data.instance_address,
    };
  };

  /**
   * 查看集群详情
   */
  const handleToClusterDetails = (data: RedisInstanceModel) => {
    router.push({
      name: 'DatabaseRedisHaList',
      query: {
        id: data.cluster_id,
      },
    });
  };
</script>

<style lang="less">
  @import '@styles/mixins.less';

  .redis-instance-list-page {
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
