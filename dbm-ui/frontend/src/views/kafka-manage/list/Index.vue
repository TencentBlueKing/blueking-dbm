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
    <div
      class="header-action"
      :class="{'is-flex': isFlexHeader}">
      <DbSearchSelect
        v-model="searchValues"
        class="mb16"
        :data="serachData"
        :placeholder="$t('输入集群名_IP_域名关键字')"
        unique-select
        @change="handleSearch" />
      <BkButton
        class="mb16"
        theme="primary"
        @click="handleGoApply">
        {{ $t('申请实例') }}
      </BkButton>
    </div>
    <div
      class="table-wrapper"
      :class="{'is-shrink-table': !isFullWidth}"
      :style="{ height: tableHeight }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="dataSource"
        fixed-pagination
        :pagination-extra="paginationExtra"
        :row-class="getRowClass"
        :settings="tableSetting"
        @clear-search="handleClearSearch"
        @setting-change="handleSettingChange" />
    </div>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      quick-close
      :title="$t('xx扩容【name】', { title: 'Kafka', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      quick-close
      :title="$t('xx缩容【name】', { title: 'Kafka', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :cluster-id="operationData.id"
        :data="{}"
        :node-list="[]"
        @change="fetchTableData" />
    </DbSideslider>
    <BkDialog
      v-model:is-show="isShowPassword"
      :title="$t('获取访问方式')">
      <RenderPassword
        v-if="operationData"
        :cluster-id="operationData.id" />
      <template #footer>
        <BkButton @click="handleHidePassword">
          {{ $t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
  </div>
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
  import { useRouter } from 'vue-router';

  import {
    getList,
    getListInstance,
  } from '@services/kafka';
  import type KafkaModel from '@services/model/kafka/kafka';
  import { createTicket } from '@services/ticket';

  import { useCopy, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import OperationStatusTips from '@components/cluster-common/OperationStatusTips.vue';
  import RenderNodeInstance from '@components/cluster-common/RenderNodeInstance.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import RenderPassword from '@components/cluster-common/RenderPassword.vue';
  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';

  import ClusterExpansion from '@views/kafka-manage/common/Expansion.vue';
  import ClusterShrink from '@views/kafka-manage/common/shrink/Index.vue';

  import {
    getSearchSelectorParams,
    isRecentDays,
  } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  import useTableSetting from './hooks/useTableSetting';

  interface Props {
    width: number,
    isFullWidth: boolean,
    dragTrigger: (isLeft: boolean) => void
  }

  const props = defineProps<Props>();

  const route = useRoute();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t, locale } = useI18n();

  const isCN = computed(() => locale.value === 'zh-cn');
  const dataSource = getList;
  const checkClusterOnline = (data: KafkaModel) => data.phase === 'online';
  const getRowClass = (data: KafkaModel) => {
    const classList = [checkClusterOnline(data) ? '' : 'is-offline'];
    const newClass = isRecentDays(data.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === Number(route.query.cluster_id)) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  const paginationExtra = computed(() => {
    if (props.isFullWidth) {
      return { small: false };
    }

    return {
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });
  const isFlexHeader = computed(() => props.width >= 460);
  const tableHeight = computed(() => `calc(100% - ${isFlexHeader.value ? 48 : 96}px)`);

  const ticketMessage = useTicketMessage();
  const {
    setting: tableSetting,
    handleChange: handleSettingChange,
  } = useTableSetting();

  const copy = useCopy();

  const serachData = [
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

  const tableOperationWidth = computed(() => {
    if (props.isFullWidth) {
      return isCN.value ? 280 : 420;
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
      label: t('集群名称'),
      minWidth: 200,
      fixed: 'left',
      showOverflowTooltip: false,
      render: ({ data }: {data: KafkaModel}) => (
        <div style="line-height: 14px; display: flex;">
          <div>
            <a href="javascript:" onClick={() => handleToDetails(data)}>{data.cluster_name}</a>
            <i class="db-icon-copy" v-bk-tooltips={t('复制集群名称')} onClick={() => copy(data.cluster_name)} />
            <RenderOperationTag data={data} style='margin-left: 3px;' />
            <div style='color: #C4C6CC;'>{data.cluster_alias}</div>
          </div>
          <db-icon v-show={!checkClusterOnline(data)} svg type="yijinyong" style="width: 38px; height: 16px; margin-left: 4px;" />
          {
            isRecentDays(data.create_at, 24 * 3)
              ? <span class="glob-new-tag cluster-tag ml-4" data-text="NEW" />
              : null
          }
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
      render: ({ data }: {data: KafkaModel}) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('域名'),
      field: 'domain',
      minWidth: 200,
      render: ({ data }: {data: KafkaModel}) => data.domain || '--',
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
    },
    {
      label: 'Zookeeper',
      field: 'zookeeper',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: KafkaModel}) => (
        <RenderNodeInstance
          role="zookeeper"
          title={`【${data.domain}】Zookeeper`}
          clusterId={data.id}
          originalList={data.zookeeper}
          dataSource={getListInstance} />
      ),
    },
    {
      label: 'Broker',
      field: 'broker',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: {data: KafkaModel}) => (
        <RenderNodeInstance
          role="broker"
          title={`【${data.domain} Broker`}
          clusterId={data.id}
          originalList={data.broker}
          dataSource={getListInstance} />
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
    },
    {
      label: t('操作'),
      width: tableOperationWidth.value,
      fixed: props.isFullWidth ? 'right' : false,
      render: ({ data }: {data: KafkaModel}) => {
        const renderAction = (theme = 'primary') => {
          const baseAction = [
            <bk-button
              text
              theme={theme}
              class="mr8"
              onClick={() => handleShowPassword(data)}>
              { t('获取访问方式') }
            </bk-button>,
          ];
          if (!checkClusterOnline(data)) {
            return [
              <bk-button
                text
                theme={theme}
                class="mr8"
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handleEnable(data)}>
                { t('启用') }
              </bk-button>,
              <bk-button
                text
                theme={theme}
                class="mr8"
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handleRemove(data)}>
                { t('删除') }
              </bk-button>,
              ...baseAction,
            ];
          }
          return [
            <OperationStatusTips
              data={data}
              class="mr8">
              <bk-button
                text
                theme={theme}
                disabled={data.operationDisabled}
                onClick={() => handleShowExpansion(data)}>
                { t('扩容') }
              </bk-button>
            </OperationStatusTips>,
            <OperationStatusTips
              data={data}
              class="mr8">
              <bk-button
                text
                theme={theme}
                disabled={data.operationDisabled}
                onClick={() => handleShowShrink(data)}>
                { t('缩容') }
              </bk-button>
            </OperationStatusTips>,
            // <OperationStatusTips
            //   data={data}
            //   style="display:none"
            //   class="mr8">
            //   <bk-button
            //     text
            //     theme={theme}>
            //     { t('Topic管理') }
            //   </bk-button>
            // </OperationStatusTips>,
            <OperationStatusTips
              data={data}
              class="mr8">
              <bk-button
                text
                theme={theme}
                disabled={data.operationDisabled}
                loading={tableDataActionLoadingMap.value[data.id]}
                onClick={() => handlDisabled(data)}>
                { t('禁用') }
              </bk-button>
            </OperationStatusTips>,
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

        if (props.isFullWidth) {
          return renderAction();
        }

        return (
          <bk-dropdown class="operations__more">
            {{
              default: () => <i class="db-icon-more"></i>,
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

  const tableRef = ref();
  const tableDataActionLoadingMap = shallowRef<Record<number, boolean>>({});
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isInit = ref(true);
  const searchValues = ref([]);
  const operationData = shallowRef<KafkaModel>();

  const fetchTableData = (loading?:boolean) => {
    const searchParams = getSearchSelectorParams(searchValues.value);
    tableRef.value?.fetchData(searchParams, {}, loading);
    isInit.value = false;
  };

  const {
    resume: resumeFetchTableData,
  } = useTimeoutPoll(() => fetchTableData(isInit.value), 5000, {
    immediate: false,
  });
  // 申请实例
  const handleGoApply = () => {
    router.push({
      name: 'KafkaApply',
      query: {
        bizId: currentBizId,
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
  const handleToDetails = (row: KafkaModel) => {
    if (props.isFullWidth) {
      props.dragTrigger(true);
    }
    router.replace({
      query: { cluster_id: row.id },
    });
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
    resumeFetchTableData();
  });

</script>
<style lang="less">
  .kafka-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      &.is-flex {
        display: flex;
        align-items: center;
        justify-content: space-between;

        .bk-search-select {
          order: 2;
          flex: 1;
          max-width: 320px;
          margin-left: 8px;
        }
      }
    }

    .table-wrapper {
      background-color: white;

      .audit-render-list,
      .bk-nested-loading {
        height: 100%;
      }

      .bk-table {
        height: 100%;
      }

      .bk-table-body {
        max-height: calc(100% - 100px);
      }
    }

    .is-shrink-table {
      .bk-table-body {
        overflow-x: hidden;
        overflow-y: auto;
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
