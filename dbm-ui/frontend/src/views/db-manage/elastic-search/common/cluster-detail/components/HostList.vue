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
  <div class="es-detail-host-list">
    <div class="action-box">
      <OperationBtnStatusTips
        v-db-console="'es.nodeList.scaleUp'"
        :data="clusterData">
        <AuthButton
          action-id="es_scale_up"
          :disabled="clusterData?.operationDisabled"
          :resource="clusterData.id"
          theme="primary"
          @click="handleShowExpansion">
          {{ t('扩容') }}
        </AuthButton>
      </OperationBtnStatusTips>
      <OperationBtnStatusTips
        v-db-console="'es.nodeList.scaleDown'"
        :data="clusterData">
        <span v-bk-tooltips="batchShrinkDisabledInfo.tooltips">
          <AuthButton
            action-id="es_shrink"
            class="ml8"
            :disabled="batchShrinkDisabledInfo.disabled || clusterData?.operationDisabled"
            :permission="clusterData?.permission.es_shrink"
            :resource="clusterData.id"
            @click="handleShowShrink">
            {{ t('缩容') }}
          </AuthButton>
        </span>
      </OperationBtnStatusTips>
      <OperationBtnStatusTips
        v-db-console="'es.nodeList.replace'"
        :data="clusterData">
        <span
          v-bk-tooltips="{
            content: t('请先选中节点'),
            disabled: !isBatchReplaceDisabeld,
          }">
          <AuthButton
            action-id="es_replace"
            class="ml8"
            :disabled="isBatchReplaceDisabeld || clusterData?.operationDisabled"
            :resource="clusterData.id"
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
        :model-value="searchSelectValue"
        :placeholder="t('请输入或选择条件搜索')"
        style="flex: 1; max-width: 560px; margin-left: auto"
        unique-select
        @change="handleSearchValueChange" />
    </div>
    <BkAlert
      v-if="clusterData?.operationStatusText"
      class="mb16"
      theme="warning">
      <I18nT
        keypath="当前集群有xx暂时不能进行其他操作跳转xx查看进度"
        tag="div">
        <span>{{ clusterData?.operationStatusText }}</span>
        <AuthRouterLink
          action-id="ticket_view"
          :resource="clusterData?.operationTicketId"
          target="_blank"
          :to="{
            name: 'bizTicketManage',
            params: {
              ticketId: clusterData?.operationTicketId,
            },
          }">
          {{ t('单据') }}
        </AuthRouterLink>
      </I18nT>
    </BkAlert>
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      primary-key="bk_host_id"
      :row-config="{
        useKey: true,
        keyField: 'bk_host_id',
      }"
      selectable
      @selection="handleSelectChange">
      <HostListFieldColumn />
      <BkTableColumn
        field=""
        fixed="right"
        :label="t('操作')"
        :width="120">
        <template #default="{ data }: { data: EsMachineModel }">
          <!-- 缩容按钮 -->
          <OperationBtnStatusTips
            v-db-console="'es.nodeList.scaleDown'"
            :data="clusterData">
            <span v-bk-tooltips="checkNodeShrinkDisable(data).tooltips">
              <AuthButton
                action-id="es_shrink"
                :disabled="checkNodeShrinkDisable(data).disabled || clusterData?.operationDisabled"
                :permission="clusterData.permission.es_shrink"
                :resource="clusterData.id"
                text
                theme="primary"
                @click="handleShrinkOne(data)">
                {{ t('缩容') }}
              </AuthButton>
            </span>
          </OperationBtnStatusTips>

          <!-- 替换按钮 -->
          <OperationBtnStatusTips
            v-db-console="'es.nodeList.replace'"
            :data="clusterData">
            <AuthButton
              action-id="es_replace"
              class="ml8"
              :disabled="clusterData?.operationDisabled"
              :permission="clusterData.permission.es_replace"
              :resource="clusterData.id"
              text
              theme="primary"
              @click="handleReplaceOne(data)">
              {{ t('替换') }}
            </AuthButton>
          </OperationBtnStatusTips>
        </template>
      </BkTableColumn>
    </DbTable>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      quick-close
      :title="t('xx扩容【name】', { title: 'ES', name: clusterData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="clusterData"
        :data="clusterData"
        @change="handleOperationChange" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      :title="t('xx缩容【name】', { title: 'ES', name: clusterData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="clusterData"
        :data="clusterData"
        :machine-list="operationNodeList"
        @change="handleOperationChange" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowReplace"
      :title="t('xx替换【name】', { title: 'ES', name: clusterData?.cluster_name })"
      :width="960">
      <ClusterReplace
        v-if="clusterData"
        :data="clusterData"
        :machine-list="operationNodeList"
        @change="handleOperationChange" />
    </DbSideslider>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import EsModel from '@services/model/es/es';
  import EsMachineModel from '@services/model/es/es-machine';

  import { useUrlSearch } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import {
    getSearchSelectValue,
    HostListFieldColumn,
    URL_HOST_MEMO_KEY,
    useCopyMachineIp,
  } from '@views/db-manage/common/cluster-details';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import ClusterExpansion from '@views/db-manage/elastic-search/common/expansion/Index.vue';
  import ClusterReplace from '@views/db-manage/elastic-search/common/replace/Index.vue';
  import ClusterShrink from '@views/db-manage/elastic-search/common/shrink/Index.vue';
  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import { getSearchSelectorParams } from '@utils';

  interface Props {
    clusterData: EsModel;
  }

  const props = defineProps<Props>();

  const fetchClusterMachineList = useClusterMachineList(ClusterTypes.DORIS);
  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { copyAllIp, copyNotAliveIp } = useCopyMachineIp();

  const { getSearchParams } = useUrlSearch();

  const dataSource = (params: Parameters<typeof fetchClusterMachineList>[0]) =>
    fetchClusterMachineList({
      ...params,
      cluster_ids: `${props.clusterData.id}`,
    });

  const searchSelectData = [
    {
      id: 'ip',
      name: 'IP',
    },
    {
      id: 'instance_role',
      name: t('部署角色'),
    },
    {
      id: 'region',
      name: t('地域'),
    },
    {
      id: 'bk_sub_zone',
      name: t('园区'),
    },
    {
      id: 'bk_os_name',
      name: t('操作系统'),
    },

    {
      id: 'bk_svr_device_cls_name',
      name: t('机型'),
    },
  ];

  const urlPaylaod = JSON.parse(decodeURIComponent(String(route.query[URL_HOST_MEMO_KEY] || '{}')));

  const checkNodeShrinkDisable = (node: EsMachineModel) => {
    const options = {
      disabled: false,
      tooltips: {
        content: '',
        disabled: true,
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
      (tableRef.value.getData() as EsMachineModel[]).forEach((nodeItem) => {
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

  const tableRef = ref();
  const isShowReplace = ref(false);
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isCopyDropdown = ref(false);

  const searchSelectValue = shallowRef<ReturnType<typeof getSearchSelectValue>>([]);
  const operationNodeList = shallowRef<Array<EsMachineModel>>([]);
  const selectedMachineList = shallowRef<Array<EsMachineModel>>([]);
  const isBatchReplaceDisabeld = computed(() => selectedMachineList.value.length < 1);

  const selectedMachineMap = computed(() => {
    return selectedMachineList.value.reduce<Record<number, EsMachineModel>>((result, item) => {
      return Object.assign(result, {
        [item.bk_host_id]: item,
      });
    }, {});
  });

  const batchShrinkDisabledInfo = computed(() => {
    // 缩容限制
    // 1. 冷节点和热节点的总数至少为一台
    // 2. client 缩容不限制
    // 3.  master 不允许缩容
    const options = {
      disabled: false,
      tooltips: {
        content: '',
        disabled: true,
      },
    };
    if (selectedMachineList.value.length < 1) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('请先选中节点');
      return options;
    }
    if (_.find(selectedMachineList.value, (item) => !(item.isClient || item.isHot || item.isCold))) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('Master节点不支持缩容');
      return options;
    }

    let hotNodeNumTotal = 0;
    let hotNodeNum = 0;
    let coldNodeNumTotal = 0;
    let coldNodeNum = 0;
    (tableRef.value.getData() as EsMachineModel[]).forEach((nodeItem) => {
      if (nodeItem.isHot) {
        hotNodeNumTotal = hotNodeNumTotal + 1;
      } else if (nodeItem.isCold) {
        coldNodeNumTotal = coldNodeNumTotal + 1;
      }
      if (selectedMachineMap.value[nodeItem.bk_host_id]) {
        return;
      }
      if (nodeItem.isHot) {
        hotNodeNum = hotNodeNum + 1;
      } else if (nodeItem.isCold) {
        coldNodeNum = coldNodeNum + 1;
      }
    });

    if (hotNodeNum + coldNodeNum < 1 && (hotNodeNumTotal > 0 || coldNodeNumTotal > 0)) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('冷节点和热节点的总数至少为一台');
    }

    return options;
  });

  const fetchData = () => {
    const serachParams = getSearchSelectorParams(searchSelectValue.value);
    tableRef.value?.fetchData(serachParams);

    router.replace({
      query: {
        ...getSearchParams(),
        [URL_HOST_MEMO_KEY]: encodeURIComponent(JSON.stringify(serachParams)),
      },
    });
  };

  const handleSelectChange = (_: any[], list: EsMachineModel[]) => {
    selectedMachineList.value = list;
  };

  const handleOperationChange = () => {
    fetchData();
  };

  // 扩容
  const handleShowExpansion = () => {
    isShowExpandsion.value = true;
  };

  // 复制所有 IP
  const handleCopyAll = () => {
    copyAllIp(tableRef.value.getData());
  };

  // 复制异常 IP
  const handleCopeFailed = () => {
    copyNotAliveIp(tableRef.value.getData());
  };

  // 复制已选 IP
  const handleCopeActive = () => {
    copyAllIp(selectedMachineList.value);
  };

  // 批量缩容
  const handleShowShrink = () => {
    operationNodeList.value = selectedMachineList.value;
    isShowShrink.value = true;
  };

  // 批量扩容
  const handleShowReplace = () => {
    operationNodeList.value = selectedMachineList.value;
    isShowReplace.value = true;
  };
  const handleShrinkOne = (data: EsMachineModel) => {
    operationNodeList.value = [data];
    isShowShrink.value = true;
  };

  const handleReplaceOne = (data: EsMachineModel) => {
    operationNodeList.value = [data];
    isShowReplace.value = true;
  };

  const handleSearchValueChange = _.debounce((payload: any) => {
    searchSelectValue.value = payload;
    fetchData();
  }, 100);

  onMounted(() => {
    searchSelectValue.value = getSearchSelectValue(searchSelectData, urlPaylaod);
  });
</script>
<style lang="less">
  .es-detail-host-list {
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
