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
  <div class="hdfs-list-page">
    <div class="header-action">
      <AuthButton
        action-id="hdfs_apply"
        class="mb16"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DropdownExportExcel
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="hdfs" />
      <DbSearchSelect
        v-model="searchValues"
        class="mb16"
        :data="serachData"
        :placeholder="t('输入集群名_IP_访问入口关键字')"
        unique-select
        @change="handleSearch" />
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
        @clear-search="handleClearSearch"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      quick-close
      :title="t('xx扩容【name】', { title: 'HDFS', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      quick-close
      :title="t('xx缩容【name】', { title: 'HDFS', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :cluster-id="operationData.id"
        :data="operationData"
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
    <BkSideslider
      v-model:is-show="isShowSettings"
      class="settings-sideslider"
      quick-close
      :title="t('查看访问配置')"
      :width="960">
      <ClusterSettings
        v-if="operationData"
        :cluster-id="operationData.id" />
    </BkSideslider>
  </div>
  <EditEntryConfig
    :id="clusterId"
    v-model:is-show="showEditEntryConfig"
    :get-detail-info="getHdfsDetail" />
</template>
<script setup lang="tsx">
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

  import HdfsModel from '@services/model/hdfs/hdfs';
  import {
    getHdfsDetail,
    getHdfsInstanceList,
    getHdfsList,
  } from '@services/source/hdfs';
  import { createTicket  } from '@services/source/ticket';

  import {
    useCopy,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderNodeInstance from '@components/cluster-common/RenderNodeInstance.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import RenderPassword from '@components/cluster-common/RenderPassword.vue';
  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import EditEntryConfig from '@components/cluster-entry-config/Index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterExpansion from '@views/hdfs-manage/common/expansion/Index.vue';
  import ClusterShrink from '@views/hdfs-manage/common/shrink/Index.vue';

  import {
    getSearchSelectorParams,
    isRecentDays,
  } from '@utils';

  import {
    useTimeoutPoll,
  } from '@vueuse/core';

  import ClusterSettings from './components/ClusterSettings.vue';

  const clusterId = defineModel<number>('clusterId');

  const route = useRoute();
  const { t, locale } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const ticketMessage = useTicketMessage();

  const copy = useCopy();
  const { currentBizId } = useGlobalBizs();
  const router = useRouter();

  const dataSource = getHdfsList;

  const tableRef = ref();
  const tableDataActionLoadingMap = shallowRef<Record<number, boolean>>({});

  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isShowSettings = ref(false);
  const isInit = ref(true);
  const showEditEntryConfig = ref(false);
  const searchValues = ref([]);

  const operationData = shallowRef<HdfsModel>();
  const selected = shallowRef<HdfsModel[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const isCN = computed(() => locale.value === 'zh-cn');
  const paginationExtra = computed(() => {
    if (isStretchLayoutOpen.value) {
      return { small: false };
    }

    return {
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });

  const serachData = [
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('集群名'),
      id: 'name',
    },
    {
      name: t('域名'),
      id: 'domain',
    },
    {
      name: 'IP',
      id: 'ip',
    },
  ];

  const getRowClass = (data: HdfsModel) => {
    const classList = [data.isOnline ? '' : 'is-offline'];
    const newClass = isRecentDays(data.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 350 : 520;
    }
    return 100;
  });

  const columns = computed(() => [
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 100,
    },
    {
      label: t('访问入口'),
      field: 'domain',
      width: 220,
      minWidth: 200,
      fixed: 'left',
      render: ({ data }: {data: HdfsModel}) => (
          <TextOverflowLayout>
            {{
              default: () => (
                <auth-button
                  action-id="hdfs_view"
                  resource={data.id}
                  permission={data.permission.hdfs_view}
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
                    resource="hdfs"
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
      field: 'cluster_name',
      width: 200,
      minWidth: 200,
      fixed: 'left',
      showOverflowTooltip: false,
      render: ({ data }: {data: HdfsModel}) => (
        <div style="line-height: 14px; display: flex;">
          <div>
            <span>
              {data.cluster_name}
            </span>
            <div style='color: #C4C6CC;'>
              {data.cluster_alias || '--'}
            </div>
          </div>
          {
            data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag ml-4" data={item}/>)
          }
          <db-icon
            v-show={!data.isOnline}
            svg
            type="yijinyong"
            style="width: 38px; height: 16px; margin-left: 4px;" />
          {
            isRecentDays(data.create_at, 24 * 3)
            && <span class="glob-new-tag cluster-tag ml-4" data-text="NEW" />
          }
            <db-icon
              class="mt-2"
              v-bk-tooltips={t('复制集群名称')}
              type="copy"
              onClick={() => copy(data.cluster_name)} />
        </div>
      ),
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
    },
    {
      label: t('状态'),
      field: 'status',
      render: ({ data }: {data: HdfsModel}) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      render: ({ data }: {data: HdfsModel}) => <span>{data?.region || '--'}</span>,
    },
    {
      label: 'NameNode',
      field: 'hdfs_namenode',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: HdfsModel}) => (
        <RenderNodeInstance
          role="hdfs_namenode"
          title={`【${data.domain}】NameNode`}
          clusterId={data.id}
          originalList={data.hdfs_namenode}
          dataSource={getHdfsInstanceList} />
      ),
    },
    {
      label: 'Zookeeper',
      field: 'hdfs_zookeeper',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: HdfsModel}) => (
        <RenderNodeInstance
          role="hdfs_zookeeper"
          title={`【${data.domain}】Zookeeper`}
          clusterId={data.id}
          originalList={data.hdfs_zookeeper}
          dataSource={getHdfsInstanceList} />
      ),
    },
    {
      label: 'Journalnode',
      field: 'hdfs_journalnode',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: HdfsModel}) => (
        <RenderNodeInstance
          role="hdfs_journalnode"
          title={`【${data.domain}】Journalnode`}
          clusterId={data.id}
          originalList={data.hdfs_journalnode}
          dataSource={getHdfsInstanceList} />
      ),
    },
    {
      label: 'DataNode',
      field: 'hdfs_datanode',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: HdfsModel}) => (
        <RenderNodeInstance
          role="hdfs_datanode"
          title={`【${data.domain}】DataNode`}
          clusterId={data.id}
          originalList={data.hdfs_datanode}
          dataSource={getHdfsInstanceList} />
      ),
    },
    {
      label: t('创建人'),
      field: 'creator',
    },
    {
      label: t('部署时间'),
      width: 160,
      field: 'create_at',
      render: ({ data }: {data: HdfsModel}) => <span>{data.createAtDisplay}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
    },
    {
      label: t('操作'),
      width: tableOperationWidth.value,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: {data: HdfsModel}) => {
        const renderAction = (theme = 'primary') => {
          const baseAction = [
          <auth-button
              text
              theme="primary"
              action-id="hdfs_view"
              permission={data.permission.hdfs_view}
              resource={data.id}
              class="mr8"
              onClick={() => handleShowPassword(data)}>
              { t('获取访问方式') }
            </auth-button>,
          <auth-button
              text
              theme="primary"
              action-id="hdfs_view"
              permission={data.permission.hdfs_view}
              resource={data.id}
              class="mr8"
              onClick={() => handleShowSettings(data)}>
              { t('查看访问配置') }
            </auth-button>,
          ];
          if (data.isOffline) {
            return [
              <auth-button
                text
                theme="primary"
                action-id="hdfs_enable_disable"
                permission={data.permission.hdfs_enable_disable}
                resource={data.id}
                class="mr8"
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handleEnable(data)}>
                { t('启用') }
              </auth-button>,
              <auth-button
                text
                theme="primary"
                action-id="hdfs_destroy"
                permission={data.permission.hdfs_destroy}
                resource={data.id}
                disabled={Boolean(data.operationTicketId)}
                class="mr8"
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handleRemove(data)}>
                { t('删除') }
              </auth-button>,
              ...baseAction,
            ];
          }
          return [
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                class="mr8"
                theme="primary"
                action-id="hdfs_scale_up"
                permission={data.permission.hdfs_scale_up}
                resource={data.id}
                disabled={data.operationDisabled}
                onClick={() => handleShowExpansion(data)}>
                { t('扩容') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                class="mr8"
                theme="primary"
                action-id="hdfs_shrink"
                permission={data.permission.hdfs_shrink}
                resource={data.id}
                disabled={data.operationDisabled}
                onClick={() => handleShowShrink(data)}>
                { t('缩容') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                class="mr8"
                theme="primary"
                action-id="hdfs_enable_disable"
                permission={data.permission.hdfs_enable_disable}
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
      'domain',
      'cluster_name',
      'bk_cloud_name',
      'major_version',
      'region',
      'status',
      'hdfs_namenode',
      'hdfs_zookeeper',
      'hdfs_journalnode',
      'hdfs_datanode',
      'cluster_time_zone',
    ],
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.HDFS_TABLE_SETTINGS, defaultSettings);

  const handleOpenEntryConfig = (row: HdfsModel) => {
    showEditEntryConfig.value  = true;
    clusterId.value = row.id;
  };

  const fetchTableData = (loading?:boolean) => {
    const searchParams = getSearchSelectorParams(searchValues.value);
    tableRef.value?.fetchData(searchParams, {}, loading);
    isInit.value = false;
  };

  const handleSelection = (data: HdfsModel, list: HdfsModel[]) => {
    selected.value = list;
  };

  const {
    resume: resumeFetchTableData,
  } = useTimeoutPoll(() => fetchTableData(isInit.value), 5000, {
    immediate: false,
  });

  // 集群提单
  const handleGoApply = () => {
    router.push({
      name: 'HdfsApply',
      query: {
        bizId: currentBizId,
        from: route.name as string,
      },
    });
  };

  // 搜索
  const handleSearch = () => {
    fetchTableData();
  };
  // 清空搜索
  const handleClearSearch = () => {
    searchValues.value = [];
    fetchTableData();
  };

  /**
   * 查看详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  // 扩容
  const handleShowExpansion = (clusterData: HdfsModel) => {
    isShowExpandsion.value = true;
    operationData.value = clusterData;
  };

  // 缩容
  const handleShowShrink = (clusterData: HdfsModel) => {
    isShowShrink.value = true;
    operationData.value = clusterData;
  };

  // 禁用
  const handlDisabled =  (clusterData: HdfsModel) => {
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
          ticket_type: 'HDFS_DISABLE',
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

  const handleEnable =  (clusterData: HdfsModel) => {
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
          ticket_type: 'HDFS_ENABLE',
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

  const handleRemove =  (clusterData: HdfsModel) => {
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
          ticket_type: 'HDFS_DESTROY',
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

  const handleShowPassword = (clusterData: HdfsModel) => {
    operationData.value = clusterData;
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };

  const handleShowSettings = (clusterData: HdfsModel) => {
    operationData.value = clusterData;
    isShowSettings.value = true;
  };

  onMounted(() => {
    resumeFetchTableData();
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>
<style lang="less" scoped>
  .settings-sideslider {
    :deep(.bk-modal-content) {
      height: 100%;
    }
  }

  .hdfs-list-page {
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
<style lang="less">
  .hdfs-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 320px;
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
