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
  <div class="doris-detail-node-list">
    <div class="action-box">
      <OperationBtnStatusTips :data="operationData">
        <AuthButton
          action-id="es_scale_up"
          :disabled="operationData?.operationDisabled"
          :permission="operationData?.permission.es_scale_up"
          :resource="operationData?.id"
          theme="primary"
          @click="handleShowExpansion">
          {{ t('扩容') }}
        </AuthButton>
      </OperationBtnStatusTips>
      <OperationBtnStatusTips :data="operationData">
        <span v-bk-tooltips="batchShrinkDisabledInfo.tooltips">
          <AuthButton
            action-id="es_shrink"
            class="ml8"
            :disabled="batchShrinkDisabledInfo.disabled || operationData?.operationDisabled"
            :permission="operationData?.permission.es_shrink"
            :resource="operationData?.id"
            @click="handleShowShrink">
            {{ t('缩容') }}
          </AuthButton>
        </span>
      </OperationBtnStatusTips>
      <OperationBtnStatusTips :data="operationData">
        <span
          v-bk-tooltips="{
            content: t('请先选中节点'),
            disabled: !isBatchReplaceDisabeld,
          }">
          <AuthButton
            action-id="es_replace"
            class="ml8"
            :disabled="isBatchReplaceDisabeld || operationData?.operationDisabled"
            :permission="operationData?.permission.es_replace"
            :resource="operationData?.id"
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
            <BkDropdownItem>
              <BkButton
                :disabled="renderTableData.length === 0"
                text
                @click="handleCopyAll">
                {{ t('复制全部IP') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                :disabled="abnormalNodeList.length === 0"
                text
                @click="handleCopeFailed">
                {{ t('复制异常IP') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                :disabled="selectedIdList.length === 0"
                text
                @click="handleCopeActive">
                {{ t('复制已选IP') }}
              </BkButton>
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <BkInput
        v-model="searchKey"
        clearable
        :placeholder="t('请输入IP搜索')"
        style="max-width: 360px; margin-left: 8px; flex: 1" />
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
              id: operationData?.operationTicketId,
            },
          }">
          {{ t('我的服务单') }}
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
      :title="t('xx扩容【name】', { title: 'Doris', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="handleOperationChange" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      :title="t('xx缩容【name】', { title: 'Doris', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :data="operationData"
        :node-list="operationNodeList"
        @change="handleOperationChange" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowReplace"
      :title="t('xx替换【name】', { title: 'Doris', name: operationData?.cluster_name })"
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
      :title="t('节点详情')"
      :width="960">
      <BigdataInstanceDetail
        v-if="operationNodeData"
        :cluster-id="clusterId"
        :cluster-type="ClusterTypes.DORIS"
        :data="operationNodeData"
        @close="handleClose" />
    </DbSideslider>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import DorisNodeModel from '@services/model/doris/doris-node';
  import {
    getDorisDetail,
    getDorisNodeList,
  } from '@services/source/doris';

  import {
    useCopy,
    useDebouncedRef,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const'

  import BigdataInstanceDetail from '@components/bigdata-instance-detail/Index.vue';
  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderHostStatus from '@components/render-host-status/Index.vue';

  import ClusterExpansion from '@views/doris-manage/common/expansion/Index.vue';
  import ClusterReplace from '@views/doris-manage/common/replace/Index.vue';
  import ClusterShrink from '@views/doris-manage/common/shrink/Index.vue';

  import { encodeRegexp } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const globalBizsStore = useGlobalBizs();
  const copy = useCopy();
  const { t } = useI18n();
  const searchKey = useDebouncedRef('');

  const columns = [
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
      render: ({ data }: {data: DorisNodeModel}) => (
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
      width: 140,
      showOverflowTooltip: false,
      render: ({ data }: { data: DorisNodeModel }) => (
        <div style="display: flex; align-items: center;">
          <div class="text-overflow" v-overflow-tips>{data.ip}</div>
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
        </div>
      ),
    },
    {
      label: t('实例数量'),
      field: 'node_count',
    },
    {
      label: t('类型'),
      width: 100,
      field: 'role',
      // render: ({ data }: {data: DorisNodeModel}) => (
      //   <RenderClusterRole data={[data.role]} />
      // ),
    },
    {
      label: t('Agent状态'),
      render: ({ data }: {data: DorisNodeModel}) => (
        <RenderHostStatus data={data.status} />
      ),
    },
    {
      label: t('部署时间'),
      field: 'createAtDisplay',
      width: 200,
    },
    {
      label: t('操作'),
      width: 200,
      fixed: 'right',
      render: ({ data }: {data: DorisNodeModel}) => {
        const shrinkDisableTooltips = checkNodeShrinkDisable(data);
        return (
          <>
            <OperationBtnStatusTips data={operationData.value}>
              <span v-bk-tooltips={shrinkDisableTooltips.tooltips}>
                <auth-button
                  text
                  theme="primary"
                  action-id="es_shrink"
                  permission={data.permission.es_shrink}
                  resource={data.bk_host_id}
                  disabled={shrinkDisableTooltips.disabled || operationData.value?.operationDisabled}
                  onClick={() => handleShrinkOne(data)}>
                  { t('缩容') }
                </auth-button>
              </span>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips data={operationData.value}>
              <auth-button
                text
                theme="primary"
                action-id="es_replace"
                permission={data.permission.es_replace}
                resource={data.bk_host_id}
                class="ml-16"
                disabled={operationData.value?.operationDisabled}
                onClick={() => handleReplaceOne(data)}>
                { t('替换') }
              </auth-button>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips data={operationData.value}>
              <auth-button
                text
                theme="primary"
                action-id="es_reboot"
                permission={data.permission.es_reboot}
                resource={data.bk_host_id}
                class="ml-16"
                disabled={operationData.value?.operationDisabled}
                onClick={() => handleShowDetail(data)}>
                { t('重启实例') }
              </auth-button>
            </OperationBtnStatusTips>
          </>
        );
      },
    },
  ];

  const isAnomalies = ref(false);
  const isShowReplace = ref(false);
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowDetail = ref(false);
  const isLoading = ref(true);
  const isCopyDropdown = ref(false);
  const operationData = shallowRef<DorisModel>();
  const operationNodeData = shallowRef<DorisNodeModel>();
  const operationNodeList = shallowRef<Array<DorisNodeModel>>([]);
  const tableData = shallowRef<DorisNodeModel[]>([]);
  const checkedNodeMap = shallowRef<Record<number, DorisNodeModel>>({});

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
    if (_.find(
      Object.values(checkedNodeMap.value),
      item => !(item.isObserver || item.isHot || item.isCold),
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
      if (nodeItem.isObserver) {
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

  const selectedIdList = computed(() => Object.values(checkedNodeMap.value).map(item => item.ip));
  const abnormalNodeList = computed(() => renderTableData.value.filter(item => item.isAbnormal));

  const fetchClusterDetail = () => {
    // 获取集群详情
    getDorisDetail({
      id: props.clusterId,
    })
      .then((data) => {
        operationData.value = data;
      });
  };

  const {
    pause: pauseFetchClusterDetail,
    resume: resumeFetchClusterDetail,
  } = useTimeoutPoll(fetchClusterDetail, 2000, {
    immediate: true,
  });

  const fetchNodeList = () => {
    isLoading.value = true;
    getDorisNodeList({
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

  watch(() => props.clusterId, () => {
    pauseFetchClusterDetail();
    resumeFetchClusterDetail();
    fetchNodeList();
  }, {
    immediate: true,
  });

  const setRowClass = (data: DorisNodeModel) => (data.isNew ? 'is-new-row' : '');

  const checkNodeShrinkDisable = (node: DorisNodeModel) => {
    const options = {
      disabled: false,
      tooltips: {
        disabled: true,
        content: '',
      },
    };

    // master 节点不支持缩容
    if (node.isFollower) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('节点类型不支持缩容');
    } else {
      // 其它类型的节点数不能全部被缩容，至少保留一个
      let clientNodeNum = 0;
      let hotNodeNum = 0;
      let coldNodeNum = 0;
      tableData.value.forEach((nodeItem) => {
        if (nodeItem.isObserver) {
          clientNodeNum = clientNodeNum + 1;
        } else if (nodeItem.isHot) {
          hotNodeNum = hotNodeNum + 1;
        } else if (nodeItem.isCold) {
          coldNodeNum = coldNodeNum + 1;
        }
      });

      if (node.isObserver && clientNodeNum < 2) {
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

  const handleClearSearch = () => {
    searchKey.value = '';
  };

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
    const ipList = tableData.value.map(nodeItem => nodeItem.ip);
    copy(ipList.join('\n'));
  };

  // 复制异常 IP
  const handleCopeFailed = () => {
    const ipList = abnormalNodeList.value.map(nodeItem => nodeItem.ip);
    copy(ipList.join('\n'));
  };

  // 复制已选 IP
  const handleCopeActive = () => {
    const ipList = Object.values(checkedNodeMap.value).map(nodeItem => nodeItem.ip);
    copy(ipList.join('\n'));
  };

  const handleSelect = (checked: boolean, data: DorisNodeModel) => {
    const checkedMap = { ...checkedNodeMap.value };
    if (checked) {
      checkedMap[data.bk_host_id] = new DorisNodeModel(data);
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
      }), {} as Record<number, DorisNodeModel>);
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
  const handleShrinkOne = (data: DorisNodeModel) => {
    operationNodeList.value = [data];
    isShowShrink.value = true;
  };

  const handleReplaceOne = (data: DorisNodeModel) => {
    operationNodeList.value = [data];
    isShowReplace.value = true;
  };

  const handleShowDetail = (data: DorisNodeModel) => {
    isShowDetail.value = true;
    operationNodeData.value = data;
  };

  const handleClose = () => {
    isShowDetail.value = false;
  };
</script>

<style lang="less" scoped>
  .doris-detail-node-list {
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

<style lang="less">
  .doris-breadcrumbs-box {
    display: flex;
    width: 100%;
    margin-left: 8px;
    font-size: 12px;
    align-items: center;

    .doris-breadcrumbs-box-status {
      display: flex;
      margin-left: 30px;
      align-items: center;
    }

    .doris-breadcrumbs-box-button {
      display: flex;
      margin-left: auto;
      align-items: center;

      .more-button {
        padding: 3px 6px;
      }
    }
  }
</style>
