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
  <div class="pulsar-list-page">
    <AuthButton
      action-id="pulsar_apply"
      class="mb16"
      theme="primary"
      @click="handleGoApply">
      {{ t('申请实例') }}
    </AuthButton>
    <DropdownExportExcel
      :has-selected="hasSelected"
      :ids="selectedIds"
      type="pulsar" />
    <div
      class="table-wrapper"
      :class="{'is-shrink-table': isStretchLayoutOpen}">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="dataSource"
        :pagination-extra="paginationExtra"
        releate-url-query
        :row-class="getRowClass"
        selectable
        :settings="tableSetting"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      quick-close
      :title="t('xx扩容【name】', { title: 'Pulsar', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      quick-close
      :title="t('xx缩容【name】', { title: 'Pulsar', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <BkDialog
      v-model:is-show="isShowPassword"
      :title="t('获取访问方式')">
      <ManagerPassword
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
    :get-detail-info="getPulsarDetail" />
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

  import PulsarModel from '@services/model/pulsar/pulsar';
  import {
    getPulsarDetail,
    getPulsarInstanceList,
    getPulsarList,
  } from '@services/source/pulsar';
  import { createTicket } from '@services/source/ticket';

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
  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import EditEntryConfig from '@components/cluster-entry-config/Index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterExpansion from '@views/pulsar-manage/common/expansion/Index.vue';
  import ClusterShrink from '@views/pulsar-manage/common/shrink/Index.vue';

  import { useTimeoutPoll } from '@vueuse/core';

  import ManagerPassword from './components/ManagerPassword.vue';

  const clusterId = defineModel<number>('clusterId');

  const route = useRoute();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t, locale } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();
  const ticketMessage = useTicketMessage();

  const copy = useCopy();

  const dataSource = getPulsarList;

  const getRowClass = (data: PulsarModel) => {
    const classStack = [];
    if (data.isOffline) {
      classStack.push('is-offline');
    }
    if (data.isNew) {
      classStack.push('is-new-row');
    }
    if (data.id === clusterId.value) {
      classStack.push('is-selected-row');
    }
    return classStack.join(' ');
  };

  const tableRef = ref();
  const tableDataActionLoadingMap = shallowRef<Record<number, boolean>>({});
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isInit = ref(true);
  const showEditEntryConfig = ref(false);

  const operationData = shallowRef<PulsarModel>();
  const selected = shallowRef<PulsarModel[]>([]);

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
  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 280 : 420;
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
      showOverflowTooltip: false,
      render: ({ data }: {data: PulsarModel}) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="pulsar_view"
                resource={data.id}
                permission={data.permission.pulsar_view}
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
                  resource="pulsar"
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
      minWidth: 100,
      fixed: 'left',
      showOverflowTooltip: false,
      render: ({ data }: {data: PulsarModel}) => (
        <div style="line-height: 14px;">
          <div class="cluster-name-box">
            <span>
              {data.cluster_name}
            </span>
            {
              data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag ml-4" data={item}/>)
            }
            <db-icon
              v-show={data.isOffline}
              svg
              type="yijinyong"
              style="width: 38px; height: 16px; margin-left: 4px; vertical-align: middle;" />
            { data.isNew && <span class="glob-new-tag cluster-tag ml-4" data-text="NEW" /> }
            <db-icon
              type="copy"
              v-bk-tooltips={t('复制集群名称')}
              onClick={() => copy(data.cluster_name)} />
          </div>
          <div style='margin-top: 4px; color: #C4C6CC;'>
            {data.cluster_alias || '--'}
          </div>
        </div>
      ),
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
      render: ({ data }: {data: PulsarModel}) => <span>{data?.region || '--'}</span>,
    },
    {
      label: t('状态'),
      field: 'status',
      render: ({ data }: {data: PulsarModel}) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: 'Bookkeeper',
      field: 'pulsar_bookkeeper',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: PulsarModel}) => (
        <RenderNodeInstance
          role="pulsar_bookkeeper"
          title={`【${data.domain}】Bookkeeper`}
          clusterId={data.id}
          originalList={data.pulsar_bookkeeper}
          dataSource={getPulsarInstanceList} />
      ),
    },
    {
      label: 'Zookeeper',
      field: 'pulsar_zookeeper',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: PulsarModel}) => (
        <RenderNodeInstance
          role="pulsar_zookeeper"
          title={`【${data.domain}】Zookeeper`}
          clusterId={data.id}
          originalList={data.pulsar_zookeeper}
          dataSource={getPulsarInstanceList} />
      ),
    },
    {
      label: 'Broker',
      field: 'pulsar_broker',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: PulsarModel}) => (
        <RenderNodeInstance
          role="pulsar_broker"
          title={`【${data.domain} Broker`}
          clusterId={data.id}
          originalList={data.pulsar_broker}
          dataSource={getPulsarInstanceList} />
      ),
    },
    {
      label: t('创建人'),
      width: 120,
      field: 'creator',
    },
    {
      label: t('部署时间'),
      width: 160,
      field: 'create_at',
      render: ({ data }: {data: PulsarModel}) => <span>{data.createAtDisplay}</span>,
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
      showOverflowTooltip: false,
      render: ({ data }: {data: PulsarModel}) => {
        const renderAction = (theme = 'primary') => {
          const baseAction = [
          <auth-button
              text
              theme="primary"
              action-id="pulsar_view"
              permission={data.permission.pulsar_view}
              resource={data.id}
              class="mr8"
              onClick={() => handleShowPassword(data)}>
              { t('获取访问方式') }
            </auth-button>,
          ];
          if (data.isOffline) {
            return [
              <auth-button
                text
                theme="primary"
                action-id="pulsar_enable_disable"
                permission={data.permission.pulsar_enable_disable}
                resource={data.id}
                class="mr8"
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handleEnable(data)}>
                { t('启用') }
              </auth-button>,
              <auth-button
                text
                theme="primary"
                action-id="pulsar_destroy"
                permission={data.permission.pulsar_destroy}
                disabled={Boolean(data.operationTicketId)}
                resource={data.id}
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
                action-id="pulsar_scale_up"
                permission={data.permission.pulsar_scale_up}
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
                action-id="pulsar_shrink"
                permission={data.permission.pulsar_shrink}
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
                action-id="pulsar_enable_disable"
                permission={data.permission.pulsar_enable_disable}
                resource={data.id}
                disabled={data.operationDisabled}
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handlDisabled(data)}>
                { t('禁用') }
              </auth-button>
            </OperationBtnStatusTips>,
            <a
              class="mr8"
              href={data.access_url}
              style={[theme === '' ? 'color: #63656e' : '']}
              target="_blank">
              { t('管理') }
            </a>,
            ...baseAction,
          ];
        };

        if (!isStretchLayoutOpen.value) {
          return (
            <>
              {renderAction()}
            </>
          );
        }

        return (
          <bk-dropdown class="operations__more">
            {{
              default: () => <db-icon type="more" />,
              content: () => (
                <bk-dropdown-menu>
                  {
                    renderAction('').map(opt => <bk-dropdown-item>{opt}</bk-dropdown-item>)
                  }
                </bk-dropdown-menu>
              ),
            }}
          </bk-dropdown>
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
      'domain',
      'major_version',
      'status',
      'pulsar_bookkeeper',
      'pulsar_zookeeper',
      'pulsar_broker',
      'cluster_time_zone',
    ],
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.PULSAR_TABLE_SETTINGS, defaultSettings);

  const handleSelection = (data: PulsarModel, list: PulsarModel[]) => {
    selected.value = list;
  };

  const handleOpenEntryConfig = (row: PulsarModel) => {
    showEditEntryConfig.value  = true;
    clusterId.value = row.id;
  };

  const fetchTableData = (loading?:boolean) => {
    tableRef.value?.fetchData({}, {}, loading);
    isInit.value = false;
  };

  const {
    resume: resumeFetchTableData,
  } = useTimeoutPoll(() => fetchTableData(isInit.value), 5000, {
    immediate: false,
  });

  const handleGoApply = () => {
    router.push({
      name: 'PulsarApply',
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
  const handleShowExpansion = (clusterData: PulsarModel) => {
    isShowExpandsion.value = true;
    operationData.value = clusterData;
  };

  // 缩容
  const handleShowShrink = (clusterData: PulsarModel) => {
    isShowShrink.value = true;
    operationData.value = clusterData;
  };

  const handlDisabled =  (clusterData: PulsarModel) => {
    InfoBox({
      title: (
        <span title={t('确认禁用【name】集群', { name: clusterData.cluster_name })}>
          {t('确认禁用【name】集群', { name: clusterData.cluster_name })}
        </span>
      ),
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
          ticket_type: 'PULSAR_DISABLE',
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

  const handleEnable =  (clusterData: PulsarModel) => {
    InfoBox({
      title: (
        <span title={t('确认启用【name】集群', { name: clusterData.cluster_name })}>
          {t('确认启用【name】集群', { name: clusterData.cluster_name })}
        </span>
      ),
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
          ticket_type: 'PULSAR_ENABLE',
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

  const handleRemove =  (clusterData: PulsarModel) => {
    InfoBox({
      title: (
        <span title={t('确认删除【name】集群', { name: clusterData.cluster_name })}>
          {t('确认删除【name】集群', { name: clusterData.cluster_name })}
        </span>
      ),
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
          ticket_type: 'PULSAR_DESTROY',
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

  const handleShowPassword = (clusterData: PulsarModel) => {
    operationData.value = clusterData;
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };

  onMounted(() => {
    resumeFetchTableData();
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>
<style lang="less">
  .pulsar-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;

      .bk-search-select {
        max-width: 320px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    .table-wrapper {
      background-color: white;

      .cluster-name-box{
        display: flex;
        align-items: center;

        & > * {
          vertical-align: middle;
        }
      }

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
  .pulsar-list-page {
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
