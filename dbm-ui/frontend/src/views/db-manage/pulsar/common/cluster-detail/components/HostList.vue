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
  <div class="pulsar-detail-host-list">
    <div class="action-box">
      <OperationBtnStatusTips
        v-db-console="'pulsar.nodeList.scaleUp'"
        :data="clusterData">
        <AuthButton
          action-id="pulsar_scale_up"
          :disabled="clusterData?.operationDisabled"
          :resource="clusterData.id"
          theme="primary"
          @click="handleShowExpansion">
          {{ t('扩容') }}
        </AuthButton>
      </OperationBtnStatusTips>
      <OperationBtnStatusTips
        v-db-console="'pulsar.nodeList.scaleDown'"
        :data="clusterData">
        <span v-bk-tooltips="batchShrinkDisabledInfo.tooltips">
          <AuthButton
            action-id="pulsar_shrink"
            class="ml-8"
            :disabled="batchShrinkDisabledInfo.disabled || clusterData?.operationDisabled"
            :resource="clusterData.id"
            @click="handleShowShrink">
            {{ t('缩容') }}
          </AuthButton>
        </span>
      </OperationBtnStatusTips>
      <OperationBtnStatusTips
        v-db-console="'pulsar.nodeList.replace'"
        :data="clusterData">
        <span
          v-bk-tooltips="{
            content: t('请先选中节点'),
            disabled: !isBatchReplaceDisabeld,
          }">
          <AuthButton
            action-id="pulsar_replace"
            class="ml-8"
            :disabled="isBatchReplaceDisabeld || clusterData?.operationDisabled"
            :resource="clusterData.id"
            @click="handleShowReplace">
            {{ t('替换') }}
          </AuthButton>
        </span>
      </OperationBtnStatusTips>
      <BkDropdown
        class="ml-8"
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
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        :placeholder="t('请输入或选择条件搜索')"
        style="flex: 1; max-width: 560px; margin-left: auto"
        @change="handleSearchValueChange" />
    </div>
    <BkAlert
      v-if="clusterData?.operationStatusText"
      class="mb-16"
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
    <HostTable
      ref="hostTableRef"
      :data-source="dataSource"
      :db-type="DBTypes.PULSAR"
      @request-success="handleRequestSuccess"
      @selection="handleSelectChange">
      <HostListFieldColumn
        :db-type="DBTypes.PULSAR"
        :role-list="roleList" />
      <TableColumn
        col-key="row-operation"
        fixed="right"
        :title="t('操作')"
        :width="120">
        <template #default="{ row }: { row: PulsarMachineModel }">
          <!-- 缩容按钮 -->
          <OperationBtnStatusTips
            v-db-console="'pulsar.nodeList.scaleDown'"
            :data="clusterData">
            <span v-bk-tooltips="checkNodeShrinkDisable(row).tooltips">
              <AuthButton
                action-id="pulsar_shrink"
                :disabled="checkNodeShrinkDisable(row).disabled || clusterData?.operationDisabled"
                :permission="clusterData.permission.pulsar_shrink"
                :resource="clusterData.id"
                text
                theme="primary"
                @click="handleShrinkOne(row)">
                {{ t('缩容') }}
              </AuthButton>
            </span>
          </OperationBtnStatusTips>

          <!-- 替换按钮 -->
          <OperationBtnStatusTips
            v-db-console="'pulsar.nodeList.replace'"
            :data="clusterData">
            <AuthButton
              action-id="pulsar_replace"
              class="ml-8"
              :disabled="clusterData.operationDisabled"
              :permission="clusterData.permission.pulsar_replace"
              :resource="clusterData.id"
              text
              theme="primary"
              @click="handleReplaceOne(row)">
              {{ t('替换') }}
            </AuthButton>
          </OperationBtnStatusTips>
        </template>
      </TableColumn>
    </HostTable>
    <ClusterExpansion
      v-if="clusterData"
      v-model:is-show="isShowExpandsion"
      :cluster-data="clusterData"
      @change="handleOperationChange" />
    <ClusterShrink
      v-if="clusterData"
      v-model:is-show="isShowShrink"
      :cluster-data="clusterData"
      :machine-list="operationNodeList"
      @change="handleOperationChange" />
    <ClusterReplace
      v-if="clusterData"
      v-model:is-show="isShowReplace"
      :cluster-data="clusterData"
      :machine-list="operationNodeList"
      @change="handleOperationChange" />
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import PulsarDetailModel from '@services/model/pulsar/pulsar-detail';
  import PulsarMachineModel from '@services/model/pulsar/pulsar-machine';

  import { ClusterTypes, DBTypes } from '@common/const';

  import {
    HostListFieldColumn,
    HostTable,
    useCopyMachineIp,
    useHostSearchSelect,
  } from '@views/db-manage/common/cluster-details';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';
  import ClusterExpansion from '@views/db-manage/pulsar/common/expansion/Index.vue';
  import ClusterReplace from '@views/db-manage/pulsar/common/replace/Index.vue';
  import ClusterShrink from '@views/db-manage/pulsar/common/shrink/Index.vue';

  interface Props {
    clusterData: PulsarDetailModel;
  }

  const props = defineProps<Props>();

  const fetchClusterMachineList = useClusterMachineList(ClusterTypes.PULSAR);

  const { t } = useI18n();
  const { copyAllIp, copyNotAliveIp } = useCopyMachineIp();

  const hostTableRef = ref<InstanceType<typeof HostTable>>();
  const { fetchData, handleSearchValueChange, quickSearchData, quickSearchValue } = useHostSearchSelect(
    DBTypes.PULSAR,
    {
      tableRef: hostTableRef,
    },
  );

  const dataSource = (params: Parameters<typeof fetchClusterMachineList>[0]) =>
    fetchClusterMachineList({
      ...params,
      cluster_ids: `${props.clusterData.id}`,
    });

  const checkNodeShrinkDisable = (node: PulsarMachineModel) => {
    const options = {
      disabled: false,
      tooltips: {
        content: '',
        disabled: true,
      },
    };

    // master 节点不支持缩容
    if (node.isZookeeper) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('节点类型不支持缩容');
    }

    return options;
  };

  const isShowReplace = ref(false);
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isCopyDropdown = ref(false);

  const operationNodeList = shallowRef<Array<PulsarMachineModel>>([]);
  const selectedMachineList = shallowRef<Array<PulsarMachineModel>>([]);
  const roleList = shallowRef<
    {
      label: string;
      value: string;
    }[]
  >([]);

  const isBatchReplaceDisabeld = computed(() => selectedMachineList.value.length < 1);

  const batchShrinkDisabledInfo = computed(() => {
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
    if (_.find(selectedMachineList.value, (item) => item.isZookeeper)) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('Zookeeper 节点不支持缩容');
      return options;
    }

    return options;
  });

  const handleRequestSuccess = (list: PulsarMachineModel[]) => {
    roleList.value = _.uniqBy(
      list.map((item) => ({
        label: item.instance_role,
        value: item.instance_role,
      })),
      'value',
    );
  };

  const handleSelectChange = (list: PulsarMachineModel[]) => {
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
    copyAllIp(hostTableRef.value!.getData());
  };

  // 复制异常 IP
  const handleCopeFailed = () => {
    copyNotAliveIp(hostTableRef.value!.getData());
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
  const handleShrinkOne = (data: PulsarMachineModel) => {
    operationNodeList.value = [data];
    isShowShrink.value = true;
  };

  const handleReplaceOne = (data: PulsarMachineModel) => {
    operationNodeList.value = [data];
    isShowReplace.value = true;
  };
</script>
<style lang="less">
  .pulsar-detail-host-list {
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
