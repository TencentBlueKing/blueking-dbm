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
  <div class="es-detail-node-list">
    <div class="action-box">
      <OperationStatusTips :data="operationData">
        <BkButton
          :disabled="operationData?.operationDisabled"
          theme="primary"
          @click="handleShowExpansion">
          {{ $t('扩容') }}
        </BkButton>
      </OperationStatusTips>
      <OperationStatusTips :data="operationData">
        <span
          v-bk-tooltips="batchShrinkDisabledInfo.tooltips">
          <BkButton
            class="ml8"
            :disabled="(batchShrinkDisabledInfo.disabled || operationData?.operationDisabled)"
            @click="handleShowShrink">
            {{ $t('缩容') }}
          </BkButton>
        </span>
      </OperationStatusTips>
      <OperationStatusTips :data="operationData">
        <span
          v-bk-tooltips="{
            content: $t('请先选中节点'),
            disabled: !isBatchReplaceDisabeld
          }">
          <BkButton
            class="ml8"
            :disabled="(isBatchReplaceDisabeld || operationData?.operationDisabled)"
            @click="handleShowReplace">
            {{ $t('替换') }}
          </BkButton>
        </span>
      </OperationStatusTips>
      <BkDropdown
        class="ml8"
        @hide="() => isCopyDropdown = false"
        @show="() => isCopyDropdown = true">
        <BkButton>
          {{ $t('复制IP') }}
          <DbIcon
            class="action-copy-icon"
            :class="{
              'action-copy-icon--avtive': isCopyDropdown
            }"
            type="up-big" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleCopyAll">
              {{ $t('复制全部IP') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopeFailed">
              {{ $t('复制异常IP') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopeActive">
              {{ $t('复制已选IP') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <BkInput
        v-model="searchKey"
        clearable
        :placeholder="$t('请输入IP搜索')"
        style="max-width: 360px; margin-left: 8px; flex: 1;" />
    </div>
    <BkAlert
      v-if="operationData?.operationStatusText"
      class="mb16"
      theme="warning">
      <I18nT
        keypath="当前集群有xx暂时不能进行其他操作跳转xx查看进度"
        tag="div">
        <span>{{ operationData?.operationStatusText }}</span>
        <RouterLink
          target="_blank"
          :to="{
            name: 'SelfServiceMyTickets',
            query: {
              filterId: operationData?.operationTicketId,
            },
          }">
          {{ $t('我的服务单') }}
        </RouterLink>
      </I18nT>
    </BkAlert>
    <BkLoading :loading="isLoading">
      <DbOriginalTable
        :columns="columns"
        :data="renderTableData"
        :is-anomalies="isAnomalies"
        :is-searching="!!searchKey"
        :row-class="setRowClass"
        @clear-search="handleClearSearch"
        @refresh="fetchNodeList"
        @select="handleSelect"
        @select-all="handleSelectAll" />
    </BkLoading>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      quick-close
      :title="$t('xx扩容【name】', {title: 'ES', name:operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="handleOperationChange" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      :title="$t('xx缩容【name】', {title: 'ES', name:operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :data="operationData"
        :node-list="operationNodeList"
        @change="handleOperationChange" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowReplace"
      :title="$t('xx替换【name】', {title: 'ES', name:operationData?.cluster_name })"
      :width="960">
      <ClusterReplace
        v-if="operationData"
        :data="operationData"
        :node-list="operationNodeList"
        @change="handleOperationChange" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowDetail"
      :show-footer="false"
      :title="$t('节点详情')"
      :width="960">
      <InstanceDetail
        v-if="operationNodeData"
        :cluster-id="clusterId"
        :data="operationNodeData"
        @close="handleClose" />
    </DbSideslider>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import {
    computed,
    ref,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import {
    getClusterDetail,
    getListNodes,
  } from '@services/es';
  import type EsModel from '@services/model/es/es';
  import EsNodeModel from '@services/model/es/es-node';

  import {
    useCopy,
    useDebouncedRef,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import OperationStatusTips from '@components/cluster-common/OperationStatusTips.vue';
  import RenderClusterRole from '@components/cluster-common/RenderRole.vue';
  import RenderHostStatus from '@components/render-host-status/Index.vue';

  import ClusterExpansion from '@views/es-manage/common/expansion/Index.vue';
  import ClusterReplace from '@views/es-manage/common/replace/Index.vue';
  import ClusterShrink from '@views/es-manage/common/shrink/Index.vue';

  import {
    encodeRegexp,
    isRecentDays,
    messageWarn,
  } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  import InstanceDetail from './components/InstanceDetail.vue';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const globalBizsStore = useGlobalBizs();
  const copy = useCopy();
  const { t, locale } = useI18n();

  const isCN = computed(() => locale.value === 'zh-cn');
  const searchKey = useDebouncedRef('');
  const isAnomalies = ref(false);
  const operationData = shallowRef<EsModel>();
  const operationNodeData = shallowRef<EsNodeModel>();
  const operationNodeList = shallowRef<Array<EsNodeModel>>([]);
  const isShowReplace = ref(false);
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowDetail = ref(false);
  const isLoading = ref(true);
  const isCopyDropdown = ref(false);
  const tableData = shallowRef<EsNodeModel[]>([]);
  const checkedNodeMap = shallowRef<Record<number, EsNodeModel>>({});

  const isSelectedAll = computed(() => tableData.value.length > 0
    && Object.keys(checkedNodeMap.value).length >= tableData.value.length);

  const setRowClass = (data: EsNodeModel) => (isRecentDays(data.create_at, 24 * 3) ? 'is-new-row' : '');

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
    if (_.find(
      Object.values(checkedNodeMap.value),
      item => !(item.isClient || item.isHot || item.isCold),
    )) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('Master节点不支持缩容');
      return options;
    }

    // 其它类型的节点数不能全部被缩容，至少保留一个
    let clientNodeNum = 0;
    let hotNodeNum = 0;
    let coldNodeNum = 0;
    tableData.value.forEach((nodeItem) => {
      if (checkedNodeMap.value[nodeItem.bk_host_id]) {
        return;
      }
      if (nodeItem.isClient) {
        clientNodeNum = clientNodeNum + 1;
      } else if (nodeItem.isHot) {
        hotNodeNum = hotNodeNum + 1;
      } else if (nodeItem.isCold) {
        coldNodeNum = coldNodeNum + 1;
      }
    });

    if (clientNodeNum < 1) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('Client类型节点至少保留一个');
    } else if (hotNodeNum < 1) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('热节点至少保留一个');
    } else if (coldNodeNum < 1) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('冷节点至少保留一个');
    }

    return options;
  });
  const isBatchReplaceDisabeld = computed(() => Object.keys(checkedNodeMap.value).length < 1);

  const renderTableData = computed(() => {
    const searchReg = new RegExp(`${encodeRegexp(searchKey.value)}`);
    return tableData.value.filter(item => searchReg.test(item.ip));
  });

  const checkNodeShrinkDisable = (node: EsNodeModel) => {
    const options = {
      disabled: false,
      tooltips: {
        disabled: true,
        content: '',
      },
    };

    // master 节点不支持缩容
    if (node.isMaster) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('节点类型不支持缩容');
    } else {
      // 其它类型的节点数不能全部被缩容，至少保留一个
      let clientNodeNum = 0;
      let hotNodeNum = 0;
      let coldNodeNum = 0;
      tableData.value.forEach((nodeItem) => {
        if (nodeItem.isClient) {
          clientNodeNum = clientNodeNum + 1;
        } else if (nodeItem.isHot) {
          hotNodeNum = hotNodeNum + 1;
        } else if (nodeItem.isCold) {
          coldNodeNum = coldNodeNum + 1;
        }
      });

      if (node.isClient && clientNodeNum < 2) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('Client类型节点至少保留一个');
      } else if (node.isHot && hotNodeNum < 2) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('热节点至少保留一个');
      } else if (node.isCold && coldNodeNum < 2) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('冷节点至少保留一个');
      }
    }

    return options;
  };

  const columns = [
    {
      width: 60,
      label: () => (
        <bk-checkbox
          label={true}
          model-value={isSelectedAll.value}
          onChange={handleSelectAll}
        />
      ),
      render: ({ data }: {data: EsNodeModel}) => (
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
      minWidth: 140,
      showOverflowTooltip: false,
      render: ({ data }: { data: EsNodeModel }) => (
        <div style="display: flex; align-items: center;">
          <div class="text-overflow" v-overflow-tips>{data.ip}</div>
          {
            isRecentDays(data.create_at, 24 * 3)
              ? <span class="glob-new-tag ml-4" data-text="NEW" />
              : null
          }
        </div>
      ),
    },
    {
      label: t('实例数量'),
      field: 'node_count',
    },
    {
      label: t('类型'),
      width: 300,
      render: ({ data }: {data: EsNodeModel}) => (
        <RenderClusterRole data={[data.role]} />
      ),
    },
    {
      label: t('Agent状态'),
      render: ({ data }: {data: EsNodeModel}) => (
        <RenderHostStatus data={data.status} />
      ),
    },
    {
      label: t('部署时间'),
      field: 'create_at',
    },
    {
      label: t('操作'),
      width: isCN.value ? 200 : 260,
      render: ({ data }: {data: EsNodeModel}) => {
        const shrinkDisableTooltips = checkNodeShrinkDisable(data);
        return (
          <>
            <OperationStatusTips data={operationData.value}>
              <span v-bk-tooltips={shrinkDisableTooltips.tooltips}>
                <bk-button
                  theme="primary"
                  text
                  disabled={shrinkDisableTooltips.disabled || operationData.value?.operationDisabled}
                  onClick={() => handleShrinkOne(data)}>
                  { t('缩容') }
                </bk-button>
              </span>
            </OperationStatusTips>
            <OperationStatusTips data={operationData.value}>
              <bk-button
                class="ml8"
                theme="primary"
                text
                disabled={operationData.value?.operationDisabled}
                onClick={() => handleReplaceOne(data)}>
                { t('替换') }
              </bk-button>
            </OperationStatusTips>
            <OperationStatusTips data={operationData.value}>
              <bk-button
                theme="primary"
                text
                class="ml8"
                disabled={operationData.value?.operationDisabled}
                onClick={() => handleShowDetail(data)}>
                { t('重启实例') }
              </bk-button>
            </OperationStatusTips>
          </>
        );
      },
    },
  ];

  const fetchClusterDetail = () => {
    // 获取集群详情
    getClusterDetail({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_id: props.clusterId,
    })
      .then((data) => {
        operationData.value = data;
      });
  };

  const fetchNodeList = () => {
    isLoading.value = true;
    getListNodes({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_id: props.clusterId,
      no_limit: 1,
    }).then((data) => {
      tableData.value = data.results;
      isAnomalies.value = false;
    })
      .catch(() => {
        tableData.value = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const handleClearSearch = () => {
    searchKey.value = '';
  };

  const {
    pause: pauseFetchClusterDetail,
    resume: resumeFetchClusterDetail,
  } = useTimeoutPoll(fetchClusterDetail, 2000, {
    immediate: true,
  });

  watch(() => props.clusterId, () => {
    pauseFetchClusterDetail();
    resumeFetchClusterDetail();
    fetchNodeList();
  }, {
    immediate: true,
  });

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
    copy(ipList.join('\n'));
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
    copy(ipList.join('\n'));
  };

  // 复制已选 IP
  const handleCopeActive = () => {
    const list = Object.values(checkedNodeMap.value).map(item => item.ip);
    if (list.length < 1) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    copy(list.join('\n'));
  };

  const handleSelect = (checked: boolean, data: EsNodeModel) => {
    const checkedMap = { ...checkedNodeMap.value };
    if (checked) {
      checkedMap[data.bk_host_id] = new EsNodeModel(data);
    } else {
      delete checkedMap[data.bk_host_id];
    }

    checkedNodeMap.value = checkedMap;
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      checkedNodeMap.value = tableData.value.reduce((result, nodeData) => ({
        ...result,
        [nodeData.bk_host_id]: nodeData,
      }), {} as Record<number, EsNodeModel>);
    } else {
      checkedNodeMap.value = {};
    }
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
  const handleShrinkOne = (data: EsNodeModel) => {
    operationNodeList.value = [data];
    isShowShrink.value = true;
  };

  const handleReplaceOne = (data: EsNodeModel) => {
    operationNodeList.value = [data];
    isShowReplace.value = true;
  };

  const handleShowDetail = (data: EsNodeModel) => {
    isShowDetail.value = true;
    operationNodeData.value = data;
  };

  const handleClose = () => {
    isShowDetail.value = false;
  };

</script>
<style lang="less">
  .es-detail-node-list {
    padding: 24px 0;

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
</style>
