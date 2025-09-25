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
  <div class="doris-detail-host-list">
    <div class="action-box">
      <OperationBtnStatusTips :data="clusterData">
        <AuthButton
          action-id="doris_scale_up"
          :disabled="clusterData?.operationDisabled"
          :resource="clusterData.id"
          theme="primary"
          @click="handleShowExpansion">
          {{ t('扩容') }}
        </AuthButton>
      </OperationBtnStatusTips>
      <OperationBtnStatusTips :data="clusterData">
        <span v-bk-tooltips="batchShrinkDisabledInfo.tooltips">
          <AuthButton
            action-id="doris_shrink"
            class="ml-8"
            :disabled="batchShrinkDisabledInfo.disabled || clusterData?.operationDisabled"
            :resource="clusterData.id"
            @click="handleShowShrink">
            {{ t('缩容') }}
          </AuthButton>
        </span>
      </OperationBtnStatusTips>
      <OperationBtnStatusTips :data="clusterData">
        <span
          v-bk-tooltips="{
            content: t('请先选中节点'),
            disabled: !isBatchReplaceDisabeld,
          }">
          <AuthButton
            action-id="doris_replace"
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
          <BkDropdownMenu class="dropdown-menu-with-button">
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
        <RouterLink
          target="_blank"
          :to="{
            name: 'SelfServiceMyTickets',
            query: {
              id: clusterData?.operationTicketId,
            },
          }">
          {{ t('我的服务单') }}
        </RouterLink>
      </I18nT>
    </BkAlert>
    <HostTable
      ref="tableRef"
      :data-source="dataSource"
      :db-type="DBTypes.DORIS"
      @request-success="handleRequestSuccess"
      @selection="handleSelectChange">
      <HostListFieldColumn
        :db-type="DBTypes.DORIS"
        :role-list="roleList" />
      <TableColumn
        col-key="row-operation"
        fixed="right"
        :title="t('操作')"
        :width="120">
        <template #default="{ row }: { row: DorisMachineModel }">
          <!-- 缩容按钮 -->
          <OperationBtnStatusTips :data="clusterData">
            <span v-bk-tooltips="checkNodeShrinkDisable(row).tooltips">
              <AuthButton
                action-id="doris_shrink"
                :disabled="checkNodeShrinkDisable(row).disabled || clusterData?.operationDisabled"
                :permission="clusterData.permission.doris_shrink"
                :resource="clusterData.id"
                text
                theme="primary"
                @click="handleShrinkOne(row)">
                {{ t('缩容') }}
              </AuthButton>
            </span>
          </OperationBtnStatusTips>

          <!-- 替换按钮 -->
          <OperationBtnStatusTips :data="clusterData">
            <AuthButton
              action-id="doris_replace"
              class="ml-8"
              :disabled="clusterData?.operationDisabled"
              :permission="clusterData.permission.doris_replace"
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
      :machine-list="operationMachineList"
      @change="handleOperationChange" />
    <ClusterReplace
      v-if="clusterData"
      v-model:is-show="isShowReplace"
      :cluster-data="clusterData"
      :machine-list="operationMachineList"
      @change="handleOperationChange" />
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import DorisDetailModel from '@services/model/doris/doris-detail';
  import DorisMachineModel from '@services/model/doris/doris-machine';

  import { ClusterTypes, DBTypes } from '@common/const';

  import {
    HostListFieldColumn,
    HostTable,
    useCopyMachineIp,
    useHostSearchSelect,
  } from '@views/db-manage/common/cluster-details';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import ClusterExpansion from '@views/db-manage/doris/common/expansion/Index.vue';
  import ClusterReplace from '@views/db-manage/doris/common/replace/Index.vue';
  import ClusterShrink from '@views/db-manage/doris/common/shrink/Index.vue';
  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  interface Props {
    clusterData: DorisDetailModel;
  }

  const props = defineProps<Props>();

  const fetchClusterMachineList = useClusterMachineList(ClusterTypes.DORIS);
  const { t } = useI18n();
  const { copyAllIp, copyNotAliveIp } = useCopyMachineIp();

  const dbTableRef = ref<InstanceType<typeof HostTable>>();
  const { fetchData, handleSearchValueChange, quickSearchData, quickSearchValue } = useHostSearchSelect(DBTypes.DORIS, {
    tableRef: dbTableRef,
  });

  const dataSource = (params: Parameters<typeof fetchClusterMachineList>[0]) =>
    fetchClusterMachineList({
      ...params,
      cluster_ids: `${props.clusterData.id}`,
    });

  const checkNodeShrinkDisable = (node: DorisMachineModel) => {
    const options = {
      disabled: false,
      tooltips: {
        content: '',
        disabled: true,
      },
    };

    // follower 节点不支持缩容
    if (node.isFollower) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('节点类型不支持缩容');
    } else {
      // Observer 若存在至少需要2台
      // 冷/热 数据节点必选1种以上，每个角色至少需要2台
      let observerNodeNum = 0;
      let hotNodeNum = 0;
      let coldNodeNum = 0;
      (dbTableRef.value!.getData() as DorisMachineModel[]).forEach((nodeItem) => {
        if (nodeItem.isObserver) {
          observerNodeNum = observerNodeNum + 1;
        } else if (nodeItem.isHot) {
          hotNodeNum = hotNodeNum + 1;
        } else if (nodeItem.isCold) {
          coldNodeNum = coldNodeNum + 1;
        }
      });

      if (node.isObserver && observerNodeNum === 2) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('Follower类型节点若存在至少保留两台');
      } else if (node.isHot && hotNodeNum > 0 && coldNodeNum === 0) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('冷/热 数据节点必选 1 种以上，每个角色至少需要 2 台');
      } else if (node.isCold && coldNodeNum > 0 && hotNodeNum === 0) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('冷/热 数据节点必选 1 种以上，每个角色至少需要 2 台');
      }
    }

    return options;
  };

  const isShowReplace = ref(false);
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isCopyDropdown = ref(false);

  const operationMachineList = shallowRef<Array<DorisMachineModel>>([]);
  const selectedMachineList = shallowRef<Array<DorisMachineModel>>([]);
  const roleList = shallowRef<
    {
      label: string;
      value: string;
    }[]
  >([]);

  const isBatchReplaceDisabeld = computed(() => selectedMachineList.value.length < 1);

  const batchShrinkDisabledInfo = computed(() => {
    // 1.Follower 为必须，3个节点, 缩容
    // 2.Observer 非必选，若选至少需要2台
    // 3.冷/热 数据节点必选1种以上，每个角色至少需要2台

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
    if (selectedMachineList.value.some((item) => item.isFollower)) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('Follower节点不支持缩容');
      return options;
    }

    return options;
  });

  const handleRequestSuccess = (list: DorisMachineModel[]) => {
    roleList.value = _.uniqBy(
      list.map((item) => ({
        label: item.instance_role,
        value: item.instance_role,
      })),
      'value',
    );
  };

  const handleSelectChange = (_: any[], list: DorisMachineModel[]) => {
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
    copyAllIp(dbTableRef.value!.getData());
  };

  // 复制异常 IP
  const handleCopeFailed = () => {
    copyNotAliveIp(dbTableRef.value!.getData());
  };

  // 复制已选 IP
  const handleCopeActive = () => {
    copyAllIp(selectedMachineList.value);
  };

  // 批量缩容
  const handleShowShrink = () => {
    operationMachineList.value = selectedMachineList.value;
    isShowShrink.value = true;
  };

  // 批量扩容
  const handleShowReplace = () => {
    operationMachineList.value = selectedMachineList.value;
    isShowReplace.value = true;
  };
  const handleShrinkOne = (data: DorisMachineModel) => {
    operationMachineList.value = [data];
    isShowShrink.value = true;
  };

  const handleReplaceOne = (data: DorisMachineModel) => {
    operationMachineList.value = [data];
    isShowReplace.value = true;
  };
</script>

<style lang="less">
  .doris-detail-host-list {
    padding: 16px 0;

    .action-box {
      display: flex;
      margin-bottom: 16px;

      .action-box-search-select {
        max-width: 360px;
        margin-left: auto;
        flex: 1;
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
  }
</style>
