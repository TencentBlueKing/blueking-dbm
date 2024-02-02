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
  <div class="replica-set-list">
    <div class="header-action">
      <BkButton
        class="mr-8 mb-8"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </BkButton>
      <BkButton
        class="mr-8 mb-8"
        :disabled="!hasSelected"
        @click="handleShowClusterAuthorize">
        {{ t('批量授权') }}
      </BkButton>
      <span
        v-bk-tooltips="{
          disabled: hasData,
          content: t('请先申请集群')
        }"
        class="inline-block">
        <BkButton
          class="mr-8 mb-8"
          :disabled="!hasData"
          @click="handleShowExcelAuthorize">
          {{ t('导入授权') }}
        </BkButton>
      </span>
      <DropdownExportExcel
        class="mr-8 mb-8 export-excel-button"
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="mongodb" />
      <DbSearchSelect
        v-model="searchValues"
        class="header-action-search-select"
        :data="searchSelectData"
        :placeholder="t('输入集群名_IP_访问入口关键字')"
        unique-select
        @change="fetchData" />
    </div>
    <DbTable
      ref="tableRef"
      class="replica-set-list-table"
      :columns="columns"
      :data-source="getMongoList"
      :row-class="setRowClass"
      selectable
      :settings="tableSetting"
      show-overflow-tips
      @clear-search="handleClearSearch"
      @selection="handleSelection"
      @setting-change="updateTableSettings" />
    <ClusterAuthorize
      v-model="clusterAuthorizeShow"
      :account-type="AccountTypes.MONGODB"
      :cluster-types="[ClusterTypes.MONGO_REPLICA_SET]"
      :selected="selected"
      @success="handleClearSelected" />
    <ExcelAuthorize
      v-model:is-show="excelAuthorizeShow"
      :cluster-type="ClusterTypes.MONGO_REPLICA_SET"
      :ticket-type="TicketTypes.MONGODB_EXCEL_AUTHORIZE" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import {
    getMongoInstancesList,
    getMongoList,
  } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import {
    useCopy,
    useInfoWithIcon,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    AccountTypes,
    ClusterTypes,
    TicketTypes,
    UserPersonalSettings,
  } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';
  import ExcelAuthorize from '@components/cluster-common/ExcelAuthorize.vue';
  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderNodeInstance from '@components/cluster-common/RenderNodeInstance.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import DbTable from '@components/db-table/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import RenderTextEllipsisOneLine from '@components/text-ellipsis-one-line/index.vue';

  import { getSearchSelectorParams } from '@utils';

  import { useDisableCluster } from '../../hooks/useDisableCluster';

  const clusterId = defineModel<number>('clusterId');

  const { t } = useI18n();
  const copy = useCopy();
  const route = useRoute();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();
  const disableCluster = useDisableCluster();

  const searchSelectData = [
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

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchValues = ref([]);
  const clusterAuthorizeShow = ref(false);
  const excelAuthorizeShow = ref(false);
  const selected = shallowRef<MongodbModel[]>([]);

  const hasData = computed(() => (tableRef.value?.getData() || []).length > 0);
  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const columns = computed(() => [
    {
      label: t('集群名称'),
      field: 'cluster_name',
      minWidth: 300,
      fixed: 'left',
      showOverflowTooltip: false,
      render: ({ data }: { data: MongodbModel }) => {
        const content = (
          <>
            {
              data.isNew && (
                <MiniTag
                  content='NEW'
                  class="new-tag"
                  theme='success'>
                </MiniTag>
              )
            }
            {
              data.isStructCluster && (
                <bk-popover
                  theme="light"
                  placement="top"
                  width={280}>
                  {{
                    default: () => (
                      <db-icon
                        type="clone"
                        class='ml-4 mr-4'
                        style="color: #1CAB88;margin-left: 5px;cursor: pointer;"/>
                    ),
                    content: () => (
                      <div class="struct-cluster-source-popover">
                        <div class="struct-cluster-title">{t('构造集群')}</div>
                        <div class="item-row">
                          <div class="item-row-label">{t('构造源集群')}：</div>
                          <bk-overflow-title type="tips">
                            {data.temporary_info?.source_cluster}
                          </bk-overflow-title>
                        </div>
                        <div class="item-row">
                          <div class="item-row-label">{t('关联单据')}：</div>
                          <bk-button
                            text
                            theme="primary"
                            onClick={() => handleClickRelatedTicket(data.temporary_info.ticket_id)}>
                            {data.temporary_info.ticket_id}
                          </bk-button>
                        </div>
                      </div>
                    ),
                  }}
                </bk-popover>
              )
            }
            {
              data.operationTagTips.map(item => (
                <RenderOperationTag
                  class="cluster-tag ml-4"
                  data={item}/>
              ))
            }
            {
              data.isDisabled && (
                <db-icon
                  svg
                  type="yijinyong"
                  class="disabled-tag" />
              )
            }
          </>
        );

        return (
          <div>
            <RenderTextEllipsisOneLine
              text={data.cluster_name}
              textStyle={{
                fontWeight: '700',
                minWidth: '50px',
              }}
              onClick={() => handleToDetails(data.id)}>
              {content}
            </RenderTextEllipsisOneLine>
            <span class="cluster-alias">{ data.cluster_alias }</span>
          </div>
        );
      },
    },
    {
      label: t('域名'),
      field: 'master_domain',
      render: ({ data }: { data: MongodbModel }) => <span>{data.master_domain || '--'}</span>,
    },
    {
      label: t('状态'),
      field: 'status',
      width: 100,
      render: ({ data }: { data: MongodbModel }) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('MongoDB版本'),
      field: 'major_version',
      minWidth: 100,
      render: ({ data }: { data: MongodbModel }) => <span>{data.major_version || '--'}</span>,
    },
    {
      label: t('地域'),
      field: 'bk_cloud_name',
      minWidth: 100,
      render: ({ data }: { data: MongodbModel }) => <span>{data.bk_cloud_name || '--'}</span>,
    },
    {
      label: t('节点'),
      field: 'mongodb',
      width: 180,
      showOverflowTooltip: false,
      render: ({ data }: { data: MongodbModel }) => (
        <RenderNodeInstance
          role="mongodb"
          title={`【${data.master_domain}】Mongos`}
          clusterId={data.id}
          originalList={data.mongodb}
          dataSource={getMongoInstancesList}
        />
      ),
    },
    {
      label: t('操作'),
      width: 300,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: { data: MongodbModel }) => {
        const baseButtons = [
          <bk-button
            text
            theme="primary"
            onclick={() => handleCopyMasterDomainDisplayName(data)}>
            { t('复制访问地址') }
          </bk-button>,
        ];
        const onlineButtons = [
          <OperationBtnStatusTips data={data}>
            <bk-button
              text
              theme="primary"
              class="ml-16"
              disabled={data.operationDisabled}
              onclick={() => handleDisableCluster(data)}>
              { t('禁用') }
            </bk-button>
          </OperationBtnStatusTips>,
        ];
        const offlineButtons = [
          <OperationBtnStatusTips data={data}>
            <bk-button
              text
              theme="primary"
              class="ml-16"
              disabled={data.operationDisabled}
              onclick={() => handleEnableCluster(data)}>
              { t('启用') }
            </bk-button>
          </OperationBtnStatusTips>,
        ];
        const deleteButton = (
          <OperationBtnStatusTips data={data}>
            <bk-button
              text
              theme="primary"
              class="ml-16"
              disabled={data.operationDisabled}
              onclick={() => handleDeleteCluster(data)}>
              { t('删除') }
            </bk-button>
          </OperationBtnStatusTips>
        );

        if (data.isStructCluster) {
          return [...baseButtons, deleteButton];
        }

        if (data.isOnline) {
          return [...baseButtons, ...onlineButtons];
        }
        return [...baseButtons, ...offlineButtons, deleteButton];
      },
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['cluster_name'].includes(item.field as string),
    })),
    checked: [
      'cluster_name',
      'master_domain',
      'status',
      'major_version',
      'bk_cloud_name',
      'mongodb',
    ],
    showLineHeight: false,
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.MONGODB_REPLICA_SET_SETTINGS, defaultSettings);

  const setRowClass = (row: MongodbModel) => {
    const classList = [];
    if (row.isNew) {
      classList.push('is-new');
    }
    if (!row.isOnline) {
      classList.push('is-offline');
    }
    if (row.id === clusterId.value) {
      classList.push('is-selected-row');
    }

    return classList.join(' ');
  };

  const handleApply = () => {
    router.push({
      name: 'MongoDBReplicaSetApply',
      query: {
        bizId: currentBizId,
        from: route.name as string,
      },
    });
  };

  const handleSelection = (key: number[], list: Record<any, any>[]) => {
    selected.value = list as MongodbModel[];
  };

  const handleShowClusterAuthorize = () => {
    clusterAuthorizeShow.value = true;
  };

  const handleShowExcelAuthorize = () => {
    excelAuthorizeShow.value = true;
  };

  const handleClearSelected = () => {
    selected.value = [];
  };

  const handleClearSearch = () => {
    searchValues.value = [];
  };

  const handleCopyMasterDomainDisplayName = (row: MongodbModel) => {
    copy(row.masterDomainDisplayName);
  };

  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  const handleClickRelatedTicket = (billId: number) => {
    const route = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        id: billId,
      },
    });
    window.open(route.href);
  };

  const handleEnableCluster = (row: MongodbModel) => {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确定启用该集群'),
      content: () => (
        <p>
          { t('集群') }：
          <span class='info-box-cluster-name'>
            { row.cluster_name }
          </span>
        </p>
      ),
      confirmTxt: t('启用'),
      onConfirm: async () => {
        try {
          await createTicket({
            bk_biz_id: currentBizId,
            ticket_type: TicketTypes.MONGODB_ENABLE,
            details: {
              cluster_ids: [row.id],
            },
          })
            .then((res) => {
              ticketMessage(res.id);
            });
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };

  const handleDisableCluster = (row: MongodbModel) => {
    disableCluster(row);
  };

  const handleDeleteCluster = (row: MongodbModel) => {
    const { cluster_name: name } = row;
    useInfoWithIcon({
      type: 'warnning',
      title: t('确定删除该集群'),
      confirmTxt: t('删除'),
      confirmTheme: 'danger',
      props: {
        contentAlign: 'left',
      },
      content: () => (
        <div class="cluster-delete-content">
          <p>{t('集群【name】被删除后_将进行以下操作', { name })}</p>
          <p>{t('1_删除xx集群', { name })}</p>
          <p>{t('2_删除xx实例数据_停止相关进程', { name })}</p>
          <p>3. {t('回收主机')}</p>
        </div>
      ),
      onConfirm: async () => {
        try {
          await createTicket({
            bk_biz_id: currentBizId,
            ticket_type: TicketTypes.MONGODB_DESTROY,
            details: {
              cluster_ids: [row.id],
            },
          })
            .then((res) => {
              ticketMessage(res.id);
            });
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };

  const fetchData = () => {
    tableRef.value!.fetchData({
      ...getSearchSelectorParams(searchValues.value),
      cluster_type: ClusterTypes.MONGO_REPLICA_SET,
    }, {});
  };
</script>

<style>
  .info-box-cluster-name {
    color: #313238;
  }

  .cluster-delete-content {
    padding-left: 16px;
    text-align: left;
    word-break: all;
  }
</style>

<style lang="less" scoped>
  .replica-set-list {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 8px;

      .export-excel-button {
        margin-left: 0 !important;
      }

      .header-action-search-select {
        width: 500px;
        margin-left: auto;
      }

      .header-action-deploy-time {
        width: 300px;
        margin-left: 8px;
      }
    }

    :deep(.replica-set-list-table) {
      .is-new {
        td {
          background-color: #F3FCF5 !important;
        }
      }

      .is-offline {
        .cell {
          color: #C4C6CC !important;
        }
      }

      .new-tag {
        height: 19px;
      }

      .disabled-tag {
        width: 38px;
        height: 16px;
        margin-left: 4px;
      }

      .cluster-alias {
        color: #979BA5 !important
      }

      .db-icon-copy {
        display: none;
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
  }
</style>

<style lang="less">
  .struct-cluster-source-popover {
    display: flex;
    width: 100%;
    flex-direction: column;
    gap: 12px;
    padding: 2px 0;

    .struct-cluster-title {
      font-size: 12px;
      font-weight: 700;
      color: #313238;
    }

    .item-row {
      display: flex;
      width: 100%;
      align-items: center;
      overflow: hidden;

      .item-row-bel {
        width: 72px;
        text-align: right;
      }
    }
  }
</style>
