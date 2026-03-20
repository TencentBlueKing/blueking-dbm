<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkSideslider
    :before-close="handleBeforeClose"
    class="config-edit-diff-sideslider"
    :is-show="isShow"
    render-directive="if"
    width="70%"
    @closed="handleClose">
    <template #header>
      {{ t('批量编辑_clusterType_参数', { clusterType: clusterTypeLabel }) }}
      <span class="batch-edit-subtitle">
        {{ clusterDomain }}
      </span>
      <span class="batch-edit-count ml-40">
        {{ t('已选 : n 个参数', { n: editItems.length }) }}
      </span>
    </template>

    <!-- 步骤指示器 -->
    <div class="batch-edit-steps">
      <div class="step-item">
        <span
          class="step-circle"
          :class="currentStep > 1 ? 'is-done' : 'is-active'">
          <DbIcon
            v-if="currentStep > 1"
            type="bk-dbm-icon db-icon-check-line" />
          <span v-else>1</span>
        </span>
        <span class="step-label">{{ t('参数配置') }}</span>
      </div>
      <span class="step-line" />
      <div class="step-item">
        <span
          class="step-circle"
          :class="currentStep === 2 ? 'is-active' : 'is-pending'">
          2
        </span>
        <span class="step-label">{{ t('差异对比') }}</span>
      </div>
    </div>

    <div class="batch-edit-body">
      <DbCard class="batch-edit-card">
        <BkAlert
          class="mb-16"
          theme="warning"
          :title="t('批量编辑后_参数配置将转为自定义状态_且不再随父级更新')" />

        <!-- Step 1: 编辑表格 -->
        <PrimaryTable
          v-if="currentStep === 1"
          :data="editItems"
          :filter-value="filterValue"
          :max-height="tableMaxHeight"
          resizable
          row-key="conf_name"
          @filter-change="handleFilterChange">
          <TableColumn
            col-key="conf_name"
            ellipsis
            :title="t('参数名')"
            :width="200" />
          <!-- <TableColumn
            col-key="value_default"
            :title="t('默认值')"
            :width="150" /> -->
          <TableColumn
            col-key="conf_value"
            :title="t('当前值')"
            :width="200">
            <template #default="{ row }">
              <BkInput
                v-model="row.conf_value"
                :placeholder="t('请输入')"
                size="small" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="value_allowed"
            :min-width="250"
            :title="t('约束值')">
            <template #default="{ row }">
              {{ row.value_allowed || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="description"
            ellipsis
            :title="t('描述')"
            :width="150">
            <template #default="{ row }">
              {{ row.description || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="need_restart"
            :filter="needRestartFilter"
            :title="t('重启生效')"
            :width="100">
            <template #default="{ row }">
              <span :class="row.need_restart === 1 ? 'restart-icon-yes' : 'restart-icon-no'">
                <DbIcon :type="row.need_restart === 1 ? 'check-line' : 'close'" />
              </span>
            </template>
          </TableColumn>
          <TableColumn
            col-key="operation"
            fixed="right"
            :title="t('操作')"
            :width="80">
            <template #default="{ rowIndex }">
              <BkButton
                text
                theme="primary"
                @click="handleRemoveItem(rowIndex)">
                {{ t('移除') }}
              </BkButton>
            </template>
          </TableColumn>
        </PrimaryTable>

        <!-- Step 2: 差异对比 -->
        <div
          v-if="currentStep === 2"
          class="diff-table-scroll"
          :style="{ maxHeight: tableMaxHeight }">
          <table class="diff-table">
            <thead>
              <tr>
                <th :width="200">
                  {{ t('参数名') }}
                </th>
                <th>{{ t('修改前') }}</th>
                <th>{{ t('修改后') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item of diffItems"
                :key="item.conf_name">
                <td>{{ item.conf_name }}</td>
                <td>{{ item.originValue }}</td>
                <td :class="{ 'is-changed': item.isChanged }">
                  {{ item.newValue }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </DbCard>
    </div>

    <template #footer>
      <template v-if="currentStep === 1">
        <BkButton
          class="mr-8"
          theme="primary"
          @click="handleNextStep">
          {{ t('下一步：差异对比') }}
        </BkButton>
        <BkButton @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </template>
      <template v-else>
        <BkButton
          class="mr-8"
          @click="currentStep = 1">
          {{ t('上一步') }}
        </BkButton>
        <BkButton
          class="mr-8"
          :loading="submitLoading"
          theme="primary"
          @click="handleSave">
          {{ t('保存') }}
        </BkButton>
        <BkButton @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </template>
    </template>
  </BkSideslider>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { PrimaryTable } from '@blueking/tdesign-ui';

  import { updateBusinessConfig } from '@services/source/configs';

  import { useBeforeClose } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { clusterTypeInfos, type ClusterTypes, ConfLevels } from '@common/const';

  import type { ConfItem } from './ParamTable.vue';

  interface Props {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
    confType: string;
    data: ConfItem[];
    version: string;
  }

  const props = defineProps<Props>();
  const emit = defineEmits<(e: 'saved') => void>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const handleBeforeClose = useBeforeClose();

  const currentStep = ref(1);
  const submitLoading = ref(false);
  const editItems = ref<ConfItem[]>([]);
  const originItems = ref<ConfItem[]>([]);
  const filterValue = ref<Record<string, string>>({});

  const clusterTypeLabel = computed(
    () => clusterTypeInfos[props.cluster.cluster_type]?.name || props.cluster.cluster_type,
  );
  const clusterDomain = computed(() => props.cluster.master_domain);

  // 表格最大高度：视口 - header(52) - steps(48) - footer(52) - body padding(32) - card padding(32) - alert(~56)
  const tableMaxHeight = computed(() => `${window.innerHeight - 52 - 48 - 52 - 32 - 32 - 56}px`);

  const needRestartFilter = {
    name: t('重启生效'),
    props: {
      list: [
        { label: t('是'), value: '1' },
        { label: t('否'), value: '0' },
      ],
    },
    showConfirmAndReset: true,
    type: 'multiple' as const,
  };

  const diffItems = computed(() =>
    editItems.value.map((item) => {
      const origin = originItems.value.find((o) => o.conf_name === item.conf_name);
      return {
        conf_name: item.conf_name,
        isChanged: origin?.conf_value !== item.conf_value,
        newValue: item.conf_value ?? '--',
        originValue: origin?.conf_value ?? '--',
      };
    }),
  );

  watch(isShow, () => {
    if (isShow.value) {
      editItems.value = _.cloneDeep(props.data);
      originItems.value = _.cloneDeep(props.data);
      filterValue.value = {};
      currentStep.value = 1;
    }
  });

  const handleFilterChange = (val: Record<string, string>) => {
    filterValue.value = val;
  };

  const handleRemoveItem = (index: number) => {
    editItems.value.splice(index, 1);
  };

  const handleNextStep = () => {
    currentStep.value = 2;
  };

  const handleSave = async () => {
    const changedItems = editItems.value
      .filter((item) => {
        const origin = originItems.value.find((o) => o.conf_name === item.conf_name);
        return origin?.conf_value !== item.conf_value;
      })
      .map((item) => ({
        ...item,
        op_type: 'update',
      }));

    if (changedItems.length === 0) {
      handleClose();
      return;
    }

    submitLoading.value = true;
    try {
      await updateBusinessConfig({
        bk_biz_id: globalBizsStore.currentBizId,
        conf_items: changedItems,
        conf_type: props.confType,
        confirm: 1,
        description: changedItems[0].description,
        level_name: ConfLevels.CLUSTER,
        level_value: props.cluster.id,
        meta_cluster_type: props.cluster.cluster_type,
        name: changedItems[0].conf_name,
        publish_description: '',
        version: props.version,
      });
      emit('saved');
      handleClose();
    } finally {
      submitLoading.value = false;
    }
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>

<style lang="less" scoped>
  .config-edit-diff-sideslider {
    .batch-edit-steps {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 48px;
      background: #fff;
      border-bottom: 1px solid #eaebf0;
    }

    .step-item {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .step-circle {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      font-size: 12px;
      border-radius: 32px;

      &.is-active {
        color: #fff;
        background: #3a84ff;
      }

      &.is-done {
        color: #3a84ff;
        background: #f0f5ff;
      }

      &.is-pending {
        color: #63656e;
        background: #eaebf0;
      }
    }

    .step-label {
      font-size: 14px;
      color: #313238;
    }

    .step-line {
      width: 100px;
      height: 0;
      margin: 0 16px;
      border-top: 1px solid #3a84ff;
    }

    .batch-edit-body {
      padding: 16px 24px;
      background: #f5f7fa;
    }

    .batch-edit-card {
      padding: 16px 24px;
      background: #fff;

      :deep(.db-card__content) {
        padding: 0;
      }
    }

    .batch-edit-subtitle {
      position: relative;
      padding-left: 8px;
      margin-left: 8px;
      font-size: 14px;
      line-height: 22px;
      color: #979ba5;

      &::before {
        position: absolute;
        top: 50%;
        left: 0;
        width: 1px;
        height: 16px;
        content: '';
        background: #dcdee5;
        transform: translateY(-50%);
      }
    }

    .batch-edit-count {
      font-size: 14px;
      color: #979ba5;
    }

    .restart-icon-yes,
    .restart-icon-no {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 20px;
      height: 20px;
      border-radius: 50%;
    }

    .restart-icon-yes {
      font-size: 12px;
      color: #65c389;
      background: #ebfaf0;
    }

    .restart-icon-no {
      font-size: 16px;
      color: #ff5656;
      background: #ffebeb;
    }

    .diff-table-scroll {
      overflow: auto;
    }

    .diff-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;

      tr {
        border-bottom: 1px solid #dcdee5;
      }

      th,
      td {
        padding: 10px 16px;
        text-align: left;
      }

      th {
        font-weight: normal;
        color: #313238;
        background: #f0f1f5;
      }

      td {
        color: #63656e;
      }

      td.is-changed {
        background: #fdf4e8;
      }
    }
  }
</style>
