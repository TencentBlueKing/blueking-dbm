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
  <div class="pulsar-detail-node-list">
    <div class="action-box">
      <OperationBtnStatusTips
        v-db-console="'pulsar.nodeList.scaleUp'"
        :data="operationData">
        <AuthButton
          action-id="pulsar_scale_up"
          :disabled="operationData?.operationDisabled"
          :resource="clusterId"
          theme="primary"
          @click="handleShowExpansion">
          {{ t('扩容') }}
        </AuthButton>
      </OperationBtnStatusTips>
      <OperationBtnStatusTips
        v-db-console="'pulsar.nodeList.scaleDown'"
        :data="operationData">
        <span v-bk-tooltips="batchShrinkDisabledInfo.tooltips">
          <AuthButton
            action-id="pulsar_shrink"
            class="ml8"
            :disabled="batchShrinkDisabledInfo.disabled || operationData?.operationDisabled"
            :resource="clusterId"
            @click="handleShowShrink">
            {{ t('缩容') }}
          </AuthButton>
        </span>
      </OperationBtnStatusTips>
      <OperationBtnStatusTips
        v-db-console="'pulsar.nodeList.replace'"
        :data="operationData">
        <span
          v-bk-tooltips="{
            content: t('请先选中节点'),
            disabled: !isBatchReplaceDisabeld,
          }">
          <AuthButton
            action-id="pulsar_replace"
            class="ml8"
            :disabled="isBatchReplaceDisabeld || operationData?.operationDisabled"
            :resource="clusterId"
            @click="handleShowReplace">
            {{ t('替换') }}
          </AuthButton>
        </span>
      </OperationBtnStatusTips>
      <BkDropdown
        class="ml8"
        @hide="() => (isCopyDropdown = false)"
        @show="() => (isCopyDropdown = true)">
        <BkButton>
          {{ t('复制IP') }}
          <DbIcon
            class="action-copy-icon"
            :class="{
              'action-copy-icon--avtive': isCopyDropdown,
            }"
            type="up-big" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleCopyAll">
              {{ t('复制所有IP') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopeFailed">
              {{ t('复制异常IP') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopeActive">
              {{ t('复制已选IP') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <DbSearchSelect
        :data="searchSelectData"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        style="max-width: 360px; margin-left: 8px; flex: 1"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <BkAlert
      v-if="operationData?.operationStatusText"
      class="mb16"
      theme="warning">
      <I18nT
        keypath="当前集群有xx暂时不能进行其他操作跳转xx查看进度"
        tag="div">
        <span>{{ operationData?.operationStatusText }}</span>
        <AuthRouterLink
          action-id="ticket_view"
          :resource="operationData?.operationTicketId"
          target="_blank"
          :to="{
            name: 'bizTicketManage',
            params: {
              ticketId: operationData?.operationTicketId,
            },
          }">
          {{ t('单据') }}
        </AuthRouterLink>
      </I18nT>
    </BkAlert>
    <BkLoading :loading="isLoading">
      <DbOriginalTable
        :columns="columns"
        :data="tableData"
        :is-anomalies="isAnomalies"
        :is-searching="!!searchValue.length"
        :row-class="rowClassCallback"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @select="handleSelect"
        @select-all="handleSelectAll" />
    </BkLoading>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      quick-close
      :title="t('xx扩容【name】', { title: 'Pulsar', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="handleOperationChange" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      :title="t('xx缩容【name】', { title: 'Pulsar', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :data="operationData"
        :node-list="operationNodeList"
        @change="handleOperationChange" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowReplace"
      :title="t('xx替换【name】', { title: 'Pulsar', name: operationData?.cluster_name })"
      :width="960">
      <ClusterReplace
        v-if="operationData"
        :data="operationData"
        :node-list="operationNodeList"
        @change="handleOperationChange"
        @remove-node="handleRemoveNodeSelect" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowDetail"
      :show-footer="false"
      :title="t('节点详情')"
      :width="960">
      <BigdataInstanceDetail
        v-if="operationNodeData"
        :cluster-id="clusterId"
        :cluster-type="ClusterTypes.PULSAR"
        :data="operationNodeData"
        @close="handleClose" />
    </DbSideslider>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type PulsarModel from '@services/model/pulsar/pulsar';
  import PulsarNodeModel from '@services/model/pulsar/pulsar-node';
  import { getPulsarDetail, getPulsarNodeList } from '@services/source/pulsar';

  import {
    useLinkQueryColumnSerach,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import RenderHostStatus from '@components/render-host-status/Index.vue';

  import BigdataInstanceDetail from '@views/db-manage/common/bigdata-instance-detail/Index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderClusterRole from '@views/db-manage/common/RenderRole.vue';
  import ClusterExpansion from '@views/db-manage/pulsar/common/expansion/Index.vue';
  import ClusterReplace from '@views/db-manage/pulsar/common/replace/Index.vue';
  import ClusterShrink from '@views/db-manage/pulsar/common/shrink/Index.vue';

  import {
    execCopy,
    getSearchSelectorParams,
    messageWarn,
  } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  // import InstanceDetail from './components/InstanceDetail.vue';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const checkNodeShrinkDisable = (node: PulsarNodeModel) => {
    const options = {
      disabled: false,
      tooltips: {
        disabled: true,
        content: '',
      },
    };

    // master 节点不支持缩容
    if (node.isZookeeper) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('节点类型不支持缩容');
    } else {
      // 其它类型的节点数不能全部被缩容，至少保留一个
      let bookkeeperNodeNum = 0;
      let brokerNodeNum = 0;
      totalTableData.forEach((nodeItem) => {
        if (nodeItem.isBookkeeper) {
          bookkeeperNodeNum = bookkeeperNodeNum + 1;
        } else if (nodeItem.isBroker) {
          brokerNodeNum = brokerNodeNum + 1;
        }
      });

      if (node.isBookkeeper && bookkeeperNodeNum < 3) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('Bookkeeper 类型节点至少保留两个');
      } else if (node.isBroker && brokerNodeNum < 2) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('Broker 类型节点至少保留一个');
      }
    }

    return options;
  };

  const globalBizsStore = useGlobalBizs();
  const { t, locale } = useI18n();

  const {
    searchValue,
    sortValue,
    columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.PULSAR,
    attrs: ['bk_cloud_id'],
    fetchDataFn: () => fetchNodeList(),
    defaultSearchItem: {
      id: 'ip',
      name: 'IP',
    }
  });

  let totalTableData: PulsarNodeModel[] = [];

  const isAnomalies = ref(false);
  const isShowReplace = ref(false);
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowDetail = ref(false);
  const isLoading = ref(true);
  const isCopyDropdown = ref(false);

  const operationData = shallowRef<PulsarModel>();
  const operationNodeData = shallowRef<PulsarNodeModel>();
  const operationNodeList = shallowRef<Array<PulsarNodeModel>>([]);
  const tableData = shallowRef<PulsarNodeModel[]>([]);
  const checkedNodeMap = shallowRef<Record<number, PulsarNodeModel>>({});

  const isCN = computed(() => locale.value === 'zh-cn');
  const isBatchReplaceDisabeld = computed(() => Object.keys(checkedNodeMap.value).length < 1);

  const isSelectedAll = computed(() => tableData.value.length > 0
    && Object.keys(checkedNodeMap.value).length >= tableData.value.length);

  const batchShrinkDisabledInfo = computed(() => {
    const options = {
      disabled: false,
      tooltips: {
        disabled: true,
        content: '',
      },
    };
    const selectList = Object.values(checkedNodeMap.value);
    if (selectList.length < 1) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('请先选中节点');
      return options;
    }
    if (_.find(Object.values(checkedNodeMap.value), item => item.isZookeeper)) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('Zookeeper 节点不支持缩容');
      return options;
    }

    // 其它类型的节点数不能全部被缩容，至少保留一个
    let bookkeeperNodeNum = 0;
    let brokerNodeNum = 0;
    totalTableData.forEach((nodeItem) => {
      if (checkedNodeMap.value[nodeItem.bk_host_id]) {
        return;
      }
      if (nodeItem.isBookkeeper) {
        bookkeeperNodeNum = bookkeeperNodeNum + 1;
      } else if (nodeItem.isBroker) {
        brokerNodeNum = brokerNodeNum + 1;
      }
    });

    if (bookkeeperNodeNum < 2) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('Bookkeeper类型节点至少保留两个');
    } else if (brokerNodeNum < 1) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('Broker类型节点至少保留一个');
    }

    return options;
  });

  const columns = computed(() => [
    {
      width: 60,
      fixed: 'left',
      label: () => (
      <bk-checkbox
        label={true}
        model-value={isSelectedAll.value}
        onChange={handleSelectAll}
      />
    ),
      render: ({ data }: { data: PulsarNodeModel }) => (
      <bk-checkbox
        label={true}
        model-value={Boolean(checkedNodeMap.value[data.bk_host_id])}
        onChange={(value: boolean) => handleSelect(value, data)}
      />
    ),
    },
    {
      label: t('节点IP'),
      field: 'ip',
      render: ({ data }: {data: PulsarNodeModel}) => (
        <>
          <span>{data.ip}</span>
          {
            data.isNew && (
              <bk-tag
                theme="success"
                size="small"
                class="ml-4">
                NEW
              </bk-tag>
            )
          }
        </>
      ),
    },
    {
      label: t('实例数量'),
      field: 'node_count',
      sort: true,
      width: 120,
    },
    {
      label: t('类型'),
      field: 'node_type',
      filter: {
        filterFn: () => true,
        list: [
          {
            value: 'pulsar_bookkeeper',
            text: 'Bookkeeper',
          },
          {
            value: 'pulsar_zookeeper',
            text: 'Zookeeper',
          },
          {
            value: 'pulsar_broker',
            text: 'Broker',
          },
        ],
        checked: columnCheckedMap.value.node_type,
      },
      width: 200,
      render: ({ data }: {data: PulsarNodeModel}) => (
        <RenderClusterRole data={[data.role]} />
      ),
    },
    {
      label: t('Agent状态'),
      field: 'status',
      width: 120,
      render: ({ data }: {data: PulsarNodeModel}) => <RenderHostStatus data={data.status} />,
    },
    {
      label: t('部署时间'),
      field: 'create_at',
      sort: true,
      render: ({ data }: {data: PulsarNodeModel}) => <span>{data.createAtDisplay}</span>,
    },
    {
      label: t('操作'),
      width: isCN.value ? 200 : 260,
      fixed: 'right',
      render: ({ data }: { data: PulsarNodeModel }) => {
        const shrinkDisableTooltips = checkNodeShrinkDisable(data);
        return (
          <>
            <OperationBtnStatusTips
              v-db-console="pulsar.nodeList.scaleDown"
              data={operationData.value}>
              <span v-bk-tooltips={shrinkDisableTooltips.tooltips}>
                <auth-button
                  text
                  theme="primary"
                  action-id="pulsar_shrink"
                  permission={data.permission.pulsar_shrink}
                  resource={props.clusterId}
                  disabled={shrinkDisableTooltips.disabled || operationData.value?.operationDisabled}
                  onClick={() => handleShrinkOne(data)}>
                  { t('缩容') }
                </auth-button>
              </span>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips
              v-db-console="pulsar.nodeList.replace"
              data={operationData.value}>
              <auth-button
                text
                theme="primary"
                class="ml8"
                action-id="pulsar_replace"
                permission={data.permission.pulsar_replace}
                resource={props.clusterId}
                disabled={operationData.value?.operationDisabled}
                onClick={() => handleReplaceOne(data)}>
                { t('替换') }
              </auth-button>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips
              v-db-console="pulsar.nodeList.restartInstance"
              data={operationData.value}>
              <auth-button
                text
                theme="primary"
                action-id="pulsar_reboot"
                permission={data.permission.pulsar_reboot}
                resource={props.clusterId}
                class="ml8"
                disabled={operationData.value?.operationDisabled}
                onClick={() => handleShowDetail(data)}>
                { t('重启实例') }
              </auth-button>
            </OperationBtnStatusTips>
          </>
        );
      },
    },
  ]);

  const searchSelectData = [
    {
      name: 'IP',
      id: 'ip',
      multiple: true,
    },
    {
      name: t('类型'),
      id: 'node_type',
      multiple: true,
      children: [
        {
          id: 'pulsar_bookkeeper',
          name: 'Bookkeeper',
        },
        {
          id: 'pulsar_zookeeper',
          name: 'Zookeeper',
        },
        {
          id: 'pulsar_broker',
          name: 'Broker',
        },
      ],
    },
  ];

  const rowClassCallback = (data: PulsarNodeModel) => (data.isNew ? 'is-new-row' : '');

  const fetchClusterDetail = () => {
    // 获取集群详情
    getPulsarDetail({
      id: props.clusterId,
    }).then((data) => {
      operationData.value = data;
    });
  };

  const fetchNodeList = () => {
    isLoading.value = true;
    const extraParams = {
      ...getSearchSelectorParams(searchValue.value),
      ...sortValue,
    };
    getPulsarNodeList({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_id: props.clusterId,
      no_limit: 1,
      ...extraParams,
    }).then((data) => {
      tableData.value = data.results;
      isAnomalies.value = false;
      if (searchValue.value.length === 0) {
        totalTableData = _.cloneDeep(tableData.value);
      }
    })
      .catch(() => {
        tableData.value = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const {
    pause: pauseFetchClusterDetail,
    resume: resumeFetchClusterDetail,
  } =  useTimeoutPoll(fetchClusterDetail, 5000, {
    immediate: true,
  });

  watch(
    () => props.clusterId,
    () => {
      pauseFetchClusterDetail();
      resumeFetchClusterDetail();
      fetchNodeList();
    },
    {
      immediate: true,
    },
  );

  watch(searchValue, () => {
    checkedNodeMap.value = {}
  })

  const handleOperationChange = () => {
    fetchNodeList();
    checkedNodeMap.value = {};
  };

  // 扩容
  const handleShowExpansion = () => {
    isShowExpandsion.value = true;
  };

  // 复制所有 IP
  const handleCopyAll = () => {
    const ipList = tableData.value.map(item => item.ip);
    if (ipList.length < 1) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }))
  };

  // 复制异常 IP
  const handleCopeFailed = () => {
    const ipList = tableData.value.reduce((result, item) => {
      if (item.status !== 1) {
        result.push(item.ip);
      }
      return result;
    }, [] as Array<string>);
    if (ipList.length < 1) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }))
  };

  // 复制已选 IP
  const handleCopeActive = () => {
    const list = Object.values(checkedNodeMap.value).map(item => item.ip);
    if (list.length < 1) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    execCopy(list.join('\n'), t('复制成功，共n条', { n: list.length }))
  };

  const handleSelect = (checked: boolean, data: PulsarNodeModel) => {
    const checkedMap = { ...checkedNodeMap.value };
    if (checked) {
      checkedMap[data.bk_host_id] = new PulsarNodeModel(data);
    } else {
      delete checkedMap[data.bk_host_id];
    }

    checkedNodeMap.value = checkedMap;
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      checkedNodeMap.value = tableData.value.reduce(
        (result, nodeData) => ({
          ...result,
          [nodeData.bk_host_id]: nodeData,
        }),
        {} as Record<number, PulsarNodeModel>,
      );
    } else {
      checkedNodeMap.value = {};
    }
  };

  // 取消节点的选中状态
  const handleRemoveNodeSelect = (bkHostId: number) => {
    const checkedMap = { ...checkedNodeMap.value };
    delete checkedMap[bkHostId];
    checkedNodeMap.value = checkedMap;
  };

  // 批量缩容
  const handleShowShrink = () => {
    operationNodeList.value = Object.values(checkedNodeMap.value);
    isShowShrink.value = true;
  };

  // 批量扩容
  const handleShowReplace = () => {
    operationNodeList.value = Object.values(checkedNodeMap.value);
    isShowReplace.value = true;
  };
  const handleShrinkOne = (data: PulsarNodeModel) => {
    operationNodeList.value = [data];
    isShowShrink.value = true;
  };

  const handleReplaceOne = (data: PulsarNodeModel) => {
    operationNodeList.value = [data];
    isShowReplace.value = true;
  };

  const handleShowDetail = (data: PulsarNodeModel) => {
    isShowDetail.value = true;
    operationNodeData.value = data;
  };

  const handleClose = () => {
    isShowDetail.value = false;
  };
</script>
<style lang="less">
  .pulsar-detail-node-list {
    padding: 24px 0;

    .bk-vxe-table {
      .bk-checkbox {
        vertical-align: middle;
      }
    }

    .action-box {
      display: flex;
      margin-bottom: 16px;
    }

    .action-copy-icon {
      margin-left: 6px;
      color: #979ba5;
      transform: rotateZ(180deg);
      transition: all 0.2s;

      &--avtive {
        transform: rotateZ(0);
      }
    }
  }

  .action-copy-icon {
    margin-left: 6px;
    color: #979ba5;
    transform: rotateZ(180deg);
    transition: all 0.2s;

    &--avtive {
      transform: rotateZ(0);
    }
  }
</style>
