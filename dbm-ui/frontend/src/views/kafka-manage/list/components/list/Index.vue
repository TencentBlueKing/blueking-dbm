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
  <div class="kafka-list-page">
    <div class="header-action">
      <AuthButton
        action-id="kafka_apply"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterIpInstanceCopy
        :data-list="tableDataList"
        :role-list="['zookeeper', 'broker']"
        :selected="selected" />
      <DropdownExportExcel
        :ids="selectedIds"
        type="kafka" />
      <DbSearchSelect
        :data="serachData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <div
      class="table-wrapper"
      :class="{ 'is-shrink-table': isStretchLayoutOpen }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="dataSource"
        :pagination-extra="paginationExtra"
        releate-url-query
        :row-class="getRowClass"
        selectable
        :settings="tableSetting"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      quick-close
      :title="t('xx扩容【name】', { title: 'Kafka', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      quick-close
      :title="t('xx缩容【name】', { title: 'Kafka', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :data="operationData"
        :node-list="[]"
        @change="fetchTableData" />
    </DbSideslider>
    <BkDialog
      v-model:is-show="isShowPassword"
      :title="t('获取访问方式')">
      <RenderPassword
        v-if="operationData"
        :cluster-id="operationData.id" />
      <template #footer>
        <BkButton @click="handleHidePassword">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
  </div>
  <EditEntryConfig
    :id="clusterId"
    v-model:is-show="showEditEntryConfig"
    :get-detail-info="getKafkaDetail" />
</template>
<script setup lang="tsx">
  import type { Table } from 'bkui-vue';
  import { InfoBox } from 'bkui-vue';
  import {
    onMounted,
    ref,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import KafkaModel from '@services/model/kafka/kafka';
  import {
    getKafkaDetail,
    getKafkaInstanceList,
    getKafkaList,
  } from '@services/source/kafka';
  import { createTicket } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import {
    useCopy,
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderNodeInstance from '@components/cluster-common/RenderNodeInstance.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import RenderPassword from '@components/cluster-common/RenderPassword.vue';
  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import EditEntryConfig from '@components/cluster-entry-config/Index.vue';
  import ClusterIpInstanceCopy from '@components/cluster-ip-instance-copy/Index.vue';
  import DbTable from '@components/db-table/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterExpansion from '@views/kafka-manage/common/expansion/Index.vue';
  import ClusterShrink from '@views/kafka-manage/common/shrink/Index.vue';

  import {
    getMenuListSearch,
    getSearchSelectorParams,
    isRecentDays,
  } from '@utils';

  import type {
    SearchSelectData,
    SearchSelectItem,
  } from '@/types/bkui-vue';

  const clusterId = defineModel<number>('clusterId');

  const route = useRoute();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t, locale } = useI18n();
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
    batchSearchIpInatanceList,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach(ClusterTypes.KAFKA, [
    'bk_cloud_id',
    'db_module_id',
    'major_version',
    'region',
    'time_zone',
  ], () => fetchTableData());

  const dataSource = getKafkaList;
  const getRowClass = (data: KafkaModel) => {
    const classList = [data.isOnline ? '' : 'is-offline'];
    const newClass = isRecentDays(data.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const tableDataActionLoadingMap = shallowRef<Record<number, boolean>>({});
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isInit = ref(true);
  const showEditEntryConfig = ref(false);

  const operationData = shallowRef<KafkaModel>();
  const selected = shallowRef<KafkaModel[]>([]);

  const selectedIds = computed(() => selected.value.map(item => item.id));
  const tableDataList = computed(() => tableRef.value?.getData() || [])
  const isCN = computed(() => locale.value === 'zh-cn');
  const paginationExtra = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return { small: false };
    }

    return {
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });

  const ticketMessage = useTicketMessage();

  const copy = useCopy();

  const serachData = computed(() => [
    {
      name: t('IP 或 IP:Port'),
      id: 'instance',
    },
    {
      name: t('访问入口'),
      id: 'domain',
    },
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('集群名称'),
      id: 'name',
    },
    {
      name: t('管控区域'),
      id: 'bk_cloud_id',
      multiple: true,
      children: searchAttrs.value.bk_cloud_id,
    },
    {
      name: t('创建人'),
      id: 'creator',
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
      children: [
        {
          id: 'normal',
          name: t('正常'),
        },
        {
          id: 'abnormal',
          name: t('异常'),
        },
      ],
    },
    {
      name: t('版本'),
      id: 'major_version',
      multiple: true,
      children: searchAttrs.value.major_version,
    },
    {
      name: t('地域'),
      id: 'region',
      multiple: true,
      children: searchAttrs.value.region,
    },
    {
      name: t('时区'),
      id: 'time_zone',
      multiple: true,
      children: searchAttrs.value.time_zone,
    },
  ] as SearchSelectData);

  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 270 : 420;
    }
    return 100;
  });
  const columns = computed<InstanceType<typeof Table>['$props']['columns']>(() => [
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 100,
    },
    {
      label: t('访问入口'),
      field: 'domain',
      width: 200,
      minWidth: 200,
      fixed: 'left',
      render: ({ data }: {data: KafkaModel}) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="kafka_view"
                resource={data.id}
                permission={data.permission.kafka_view}
                text
                theme="primary"
                onClick={() => handleToDetails(data.id)}>
                {data.domainDisplayName}
              </auth-button>
            ),
            append: () => (
              <>
                {data.domain && (
                  <db-icon
                    type="copy"
                    v-bk-tooltips={t('复制访问入口')}
                    onClick={() => copy(data.domainDisplayName)} />
                )}
                <auth-button
                  v-bk-tooltips={t('修改入口配置')}
                  action-id="access_entry_edit"
                  resource="kafka"
                  permission={data.permission.access_entry_edit}
                  text
                  theme="primary"
                  onClick={() => handleOpenEntryConfig(data)}>
                  <db-icon type="edit" />
                </auth-button>
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('集群名称'),
      minWidth: 200,
      fixed: 'left',
      showOverflowTooltip: false,
      render: ({ data }: {data: KafkaModel}) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <div>
                <div>
                  <div>
                    {data.cluster_name}
                  </div>
                  <div style='color: #C4C6CC;'>{data.cluster_alias || '--'}</div>
                </div>
                {
                  data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag ml-4" data={item}/>)
                }
                <db-icon
                  v-show={!data.isOnline && !data.isStarting}
                  svg
                  type="yijinyong"
                  style="width: 38px; height: 16px; margin-left: 4px;" />
                {data.isNew && <span class="glob-new-tag cluster-tag ml-4" data-text="NEW" />}
              </div>
            ),
            append: () => (
              <db-icon
                class="mt-2"
                v-bk-tooltips={t('复制集群名称')}
                type="copy"
                onClick={() => copy(data.cluster_name)} />
            )
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_id',
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      render: ({ data }: {data: KafkaModel}) => <span>{data.bk_cloud_name ?? '--'}</span>,
    },
    {
      label: t('状态'),
      field: 'status',
      filter: {
        list: [
          {
            value: 'normal',
            text: t('正常'),
          },
          {
            value: 'abnormal',
            text: t('异常'),
          },
        ],
        checked: columnCheckedMap.value.status,
      },
      render: ({ data }: {data: KafkaModel}) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.major_version,
        checked: columnCheckedMap.value.major_version,
      },
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.region,
        checked: columnCheckedMap.value.region,
      },
      render: ({ data }: {data: KafkaModel}) => <span>{data?.region || '--'}</span>,
    },
    {
      label: 'Zookeeper',
      field: 'zookeeper',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: KafkaModel}) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="zookeeper"
          title={`【${data.domain}】Zookeeper`}
          clusterId={data.id}
          originalList={data.zookeeper}
          dataSource={getKafkaInstanceList} />
      ),
    },
    {
      label: 'Broker',
      field: 'broker',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: KafkaModel}) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="broker"
          title={`【${data.domain} Broker`}
          clusterId={data.id}
          originalList={data.broker}
          dataSource={getKafkaInstanceList} />
      ),
    },
    {
      label: t('创建人'),
      field: 'creator',
    },
    {
      label: t('部署时间'),
      width: 160,
      sort: true,
      field: 'create_at',
      render: ({ data }: {data: KafkaModel}) => <span>{data.createAtDisplay}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
      filter: {
        list: columnAttrs.value.time_zone,
        checked: columnCheckedMap.value.time_zone,
      },
    },
    {
      label: t('操作'),
      width: tableOperationWidth.value,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: {data: KafkaModel}) => {
        const renderAction = (theme = 'primary') => {
          const baseAction = [
            <auth-button
              text
              theme="primary"
              action-id="kafka_access_entry_view"
              permission={data.permission.kafka_access_entry_view}
              resource={data.id}
              class="mr8"
              onClick={() => handleShowPassword(data)}>
              { t('获取访问方式') }
            </auth-button>,
          ];
          if (data.isOffline) {
            return [
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                theme="primary"
                action-id="kafka_enable_disable"
                permission={data.permission.kafka_enable_disable}
                resource={data.id}
                disabled={data.isStarting}
                class="mr8"
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handleEnable(data)}>
                { t('启用') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                theme="primary"
                action-id="kafka_destroy"
                permission={data.permission.kafka_destroy}
                disabled={Boolean(data.operationTicketId)}
                resource={data.id}
                class="mr8"
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handleRemove(data)}>
                { t('删除') }
              </auth-button>
            </OperationBtnStatusTips>,
              ...baseAction,
            ];
          }
          return [
            <OperationBtnStatusTips
              data={data}
              disabled={!data.isOffline}>
              <auth-button
                text
                class="mr8"
                theme="primary"
                action-id="kafka_scale_up"
                permission={data.permission.kafka_scale_up}
                resource={data.id}
                disabled={data.isOffline}
                onClick={() => handleShowExpansion(data)}>
                { t('扩容') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips
              data={data}
              disabled={!data.isOffline}>
              <auth-button
                text
                class="mr8"
                theme="primary"
                action-id="kafka_shrink"
                permission={data.permission.kafka_shrink}
                resource={data.id}
                disabled={data.isOffline}
                onClick={() => handleShowShrink(data)}>
                { t('缩容') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                class="mr8"
                theme="primary"
                action-id="kafka_enable_disable"
                permission={data.permission.kafka_enable_disable}
                resource={data.id}
                disabled={data.operationDisabled}
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handlDisabled(data)}>
                { t('禁用') }
              </auth-button>
            </OperationBtnStatusTips>,
            <a
              class="mr8"
              style={[theme === '' ? 'color: #63656e' : '']}
              href={data.access_url}
              target="_blank">
              { t('管理') }
            </a>,
            ...baseAction,
          ];
        };

        return (
          <>
            {renderAction()}
          </>
        );
      },
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['domain'].includes(item.field as string),
    })),
    checked: [
      'cluster_name',
      'bk_cloud_id',
      'domain',
      'major_version',
      'region',
      'status',
      'zookeeper',
      'broker',
      'cluster_time_zone',
    ],
    trigger: 'manual' as const,
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.KAFKA_TABLE_SETTINGS, defaultSettings);

  const getMenuList = async (item: SearchSelectItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, serachData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map(value => value.id);
      return serachData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'creator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then(res => res.results.map(item => ({
        id: item.username,
        name: item.username,
      })));
    }

    // 不需要远层加载
    return serachData.value.find(set => set.id === item.id)?.children || [];
  };

  const handleSelection = (data: KafkaModel, list: KafkaModel[]) => {
    selected.value = list;
  };

  const handleOpenEntryConfig = (row: KafkaModel) => {
    showEditEntryConfig.value  = true;
    clusterId.value = row.id;
  };

  const fetchTableData = (loading?:boolean) => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value?.fetchData(searchParams, { ...sortValue }, loading);
    isInit.value = false;
  };

  // 申请实例
  const handleGoApply = () => {
    router.push({
      name: 'KafkaApply',
      query: {
        bizId: currentBizId,
        from: route.name as string,
      },
    });
  };

  /**
   * 查看详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  // 扩容
  const handleShowExpansion = (clusterData: KafkaModel) => {
    isShowExpandsion.value = true;
    operationData.value = clusterData;
  };

  // 缩容
  const handleShowShrink = (clusterData: KafkaModel) => {
    isShowShrink.value = true;
    operationData.value = clusterData;
  };

  const handlDisabled =  (clusterData: KafkaModel) => {
    InfoBox({
      title: t('确认禁用【name】集群', { name: clusterData.cluster_name }),
      subTitle: '',
      confirmText: t('确认'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'KAFKA_DISABLE',
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleEnable =  (clusterData: KafkaModel) => {
    InfoBox({
      title: t('确认启用【name】集群', { name: clusterData.cluster_name }),
      subTitle: '',
      confirmText: t('确认'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'KAFKA_ENABLE',
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleRemove =  (clusterData: KafkaModel) => {
    InfoBox({
      title: t('确认删除【name】集群', { name: clusterData.cluster_name }),
      subTitle: '',
      confirmText: t('确认'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'KAFKA_DESTROY',
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleShowPassword = (clusterData: KafkaModel) => {
    operationData.value = clusterData;
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>
<style lang="less">
  .kafka-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    .table-wrapper {
      background-color: white;

      .db-table,
      .audit-render-list,
      .bk-nested-loading {
        height: 100%;
      }

      .bk-table {
        height: 100% !important;
      }

      .bk-table-body {
        max-height: calc(100% - 100px);
      }
    }

    .is-shrink-table {
      .bk-table-body {
        overflow: hidden auto;
      }
    }

    .is-offline {
      * {
        color: #c4c6cc !important;
      }

      a,
      i,
      .bk-button.bk-button-primary .bk-button-text {
        color: #3a84ff !important;
      }
    }

    .db-icon-copy {
      display: none;
    }

    .db-icon-more {
      display: block;
      font-size: @font-size-normal;
      font-weight: bold;
      color: @default-color;
      cursor: pointer;

      &:hover {
        background-color: @bg-disable;
        border-radius: 2px;
      }
    }

    tr:hover {
      .db-icon-copy {
        display: inline-block !important;
        margin-left: 4px;
        color: #3a84ff;
        vertical-align: middle;
        cursor: pointer;
      }
    }
  }
</style>
<style lang="less" scoped>
  .kafka-list-page {
    :deep(.cell) {
      line-height: normal !important;

      .domain {
        display: flex;
        align-items: center;
      }

      .db-icon-edit {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    :deep(tr:hover) {
      .db-icon-edit {
        display: inline-block !important;
      }
    }
  }
</style>
