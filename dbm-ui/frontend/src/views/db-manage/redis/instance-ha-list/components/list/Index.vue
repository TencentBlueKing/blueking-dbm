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

  import {
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    UserPersonalSettings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import {
    execCopy,
    getSearchSelectorParams,
  } from '@utils';

  const instanceData = defineModel<{instanceAddress: string, clusterId: number, clusterType: string}>('instanceData');

  const fetchData = (loading?:boolean) => {
    const params = {
      ...getSearchSelectorParams(searchValue.value),
      cluster_type: ClusterTypes.REDIS_INSTANCE,
    }
    tableRef.value.fetchData(params, { ...sortValue }, loading);
    isInit = false;
  };

  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    sortValue,
    columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.REDIS,
    attrs: ['role'],
    isCluster: false,
    fetchDataFn: () => fetchData(isInit),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });

  let isInit = true;

  const searchSelectData = computed(() => [
    {
      name: t('IP 或 IP:Port'),
      id: 'instance',
    },
    {
      name: t('访问入口'),
      id: 'domain',
      multiple: true,
    },
    {
      name: t('集群名称'),
      id: 'name',
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
      children: [
        {
          id: 'running',
          name: t('正常'),
        },
        {
          id: 'unavailable',
          name: t('异常'),
        },
        // {
        //   id: 'loading',
        //   name: t('重建中'),
        // },
      ],
    },
    {
      name: t('部署角色'),
      id: 'role',
      multiple: true,
      children: searchAttrs.value.role,
    },
    {
      name: t('端口'),
      id: 'port',
    },
  ]);

  const tableRef = ref();

  const columns = computed(() => {
    const list = [
      {
        label: 'ID',
        field: 'id',
        fixed: 'left',
        width: 80,
      },
      {
        label: t('实例'),
        field: 'instance_address',
        fixed: 'left',
        minWidth: 200,
        render: ({ data }: { data: RedisInstanceModel }) => (
          <TextOverflowLayout>
            {{
              default: () => (
                <auth-button
                  action-id="redis_view"
                  resource={data.cluster_id}
                  permission={data.permission.redis_view}
                  text
                  theme="primary"
                  onClick={() => handleToDetails(data)}>
                  {data.instance_address}
                </auth-button>
              ),
              append: () => !data.isNew && (
                <bk-tag
                  size="small"
                  theme="success"
                  class="ml-4">
                  NEW
                </bk-tag>
              )
            }}
          </TextOverflowLayout>
        ),
      },
      {
        label: t('集群名称'),
        field: 'cluster_name',
        minWidth: 200,
        render: ({ data }: { data: RedisInstanceModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="redis_view"
                resource={data.cluster_id}
                permission={data.permission.redis_view}
                text
                theme="primary"
                onClick={() => handleToClusterDetails(data)}>
                {data.cluster_name}
              </auth-button>
            ),
            append: () => (
              <db-icon
                v-bk-tooltips={t('复制集群名称')}
                type="copy"
                class="copy-btn"
                onClick={() => execCopy(data.cluster_name, t('复制成功，共n条', { n: 1 }))} />
            ),
          }}
        </TextOverflowLayout>
      ),
      },
      {
        label: t('状态'),
        field: 'status',
        width: 140,
        filter: {
          list: [
            {
              value: 'running',
              text: t('正常'),
            },
            {
              value: 'unavailable',
              text: t('异常'),
            },
            // {
            //   value: 'restoring',
            //   text: t('重建中'),
            // },
          ],
          checked: columnCheckedMap.value.status,
        },
        render: ({ data }: { data: RedisInstanceModel }) => {
          const info = data.getStatusInfo;
          return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
        },
      },
      {
        label: t('主访问入口'),
        field: 'master_domain',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ data }: { data: RedisInstanceModel }) => (
          <TextOverflowLayout>
            {{
              default: () => data.master_domain,
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制主访问入口')}
                  type="copy"
                  class="copy-btn"
                  onClick={() => execCopy(data.master_domain, t('复制成功，共n条', { n: 1 }))} />
              ),
            }}
          </TextOverflowLayout>
        ),
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
        label: t('所在园区'),
        field: 'bk_sub_zone',
        width: 140,
        render: ({ data }: { data: RedisInstanceModel }) => data.bk_sub_zone || '--',
      },
      {
        label: t('部署角色'),
        field: 'role',
        width: 140,
        filter: {
          list: columnAttrs.value.role,
          checked: columnCheckedMap.value.role,
        },
      },
      {
        label: t('部署时间'),
        field: 'create_at',
        width: 160,
        sort: true,
        render: ({ data }: { data: RedisInstanceModel }) => data.createAtDisplay || '--',
      },
      {
        label: t('操作'),
        fixed: 'right',
        width: 140,
        render: ({ data }: { data: RedisInstanceModel }) => (
          <auth-button
            action-id="redis_view"
            permission={data.permission.redis_view}
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
  const setRowClass = (row: RedisInstanceModel) => {
    const classList = [row.isNew ? 'is-new-row' : ''];

    if (
      row.cluster_id === instanceData.value?.clusterId
      && row.instance_address === instanceData.value.instanceAddress
    ) {
      classList.push('is-selected-row');
    }

    return classList.filter(classItem => classItem).join(' ');
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
    trigger: 'manual' as const,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.REDIS_HA_TABLE_SETTINGS, defaultSettings);

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
      instanceAddress: data.instance_address,
      clusterId: data.cluster_id,
      clusterType: data.cluster_type
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
