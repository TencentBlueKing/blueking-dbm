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
  <EditableColumn
    field="currentCapacity.spec_name"
    :label="t('当前容量')"
    :min-width="200"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <div v-if="cluster?.cluster_spec?.spec_name">
        <p>{{ t('规格') }}：{{ cluster.cluster_spec.spec_name || '--' }}</p>
        <p>{{ t('机器组数') }}：{{ cluster.machine_pair_cnt || '--' }}</p>
        <p>{{ t('集群分片数') }}：{{ cluster.cluster_shard_num || '--' }}</p>
        <p>
          {{ t('容量') }}：
          <span
            v-if="cluster.cluster_capacity"
            style="font-weight: bold">
            {{ cluster.cluster_capacity }} G
          </span>
          <span v-else>--</span>
        </p>
      </div>
      <div v-else></div>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    field="targetCapacity.spec_name"
    :label="t('目标容量')"
    :min-width="200"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :title="t('目标容量')"
        title-prefix-type="edit"
        :validator="() => batchFormRef?.validate().catch(() => false)"
        :width="480"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleShowBatchEdit">
          <DbIcon type="bulk-edit" />
        </span>
        <template #content>
          <div class="batch-edit-form">
            <BkForm
              ref="batchFormRef"
              form-type="vertical"
              :model="batchFormData"
              :rules="batchFormRules">
              <BkFormItem
                :label="t('规格')"
                property="specId"
                required>
                <SpecSelector
                  ref="specSelectorRef"
                  v-model="batchFormData.specId"
                  :biz-id="currentBizId"
                  :clearable="false"
                  :cloud-id="cluster?.bk_cloud_id || 0"
                  :cluster-type="ClusterTypes.TENDBCLUSTER"
                  machine-type="backend"
                  style="width: 94%" />
              </BkFormItem>
              <BkFormItem
                :label="t('机器组数')"
                property="count"
                required>
                <BkInput
                  v-model="batchFormData.count"
                  allow-empty-value
                  clearable
                  :min="1"
                  style="width: 100%"
                  :suffix="t('组')"
                  type="number">
                </BkInput>
              </BkFormItem>
            </BkForm>
            <BkAlert
              v-if="validateState.message"
              class="mt-20"
              :theme="validateState.theme || 'info'"
              :title="validateState.message"
              type="info" />
          </div>
        </template>
      </BatchEditColumn>
    </template>
    <EditableBlock @click="handleShow">
      <template #append>
        <DbIcon type="down-big" />
      </template>
      <div v-if="modelValue.spec_name">
        <p>{{ t('规格') }}：{{ modelValue.spec_name || '--' }}</p>
        <p>{{ t('机器组数') }}：{{ modelValue.machine_pair || '--' }}</p>
        <p>{{ t('集群分片数') }}：{{ cluster.cluster_shard_num || '--' }}</p>
        <p>
          {{ t('容量') }}：
          <span
            v-if="modelValue.cluster_capacity"
            style="font-weight: bold">
            {{ modelValue.cluster_capacity }} G
          </span>
          <span v-else>--</span>
        </p>
      </div>
      <div v-else></div>
    </EditableBlock>
  </EditableColumn>
  <CapacityChange
    v-model="modelValue"
    v-bind="props"
    v-model:is-show="isShow" />
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  import CapacityChange, { type TicketSpecInfo } from './CapacityChange.vue';

  interface Props {
    /** 所有行的集群数据列表，用于统一设置时的校验 */
    allClusters?: Props['cluster'][];
    cluster: Pick<
      TendbClusterModel,
      | 'id'
      | 'master_domain'
      | 'bk_cloud_id'
      | 'cluster_capacity'
      | 'cluster_shard_num'
      | 'cluster_spec'
      | 'db_module_id'
      | 'machine_pair_cnt'
      | 'remote_shard_num'
      | 'disaster_tolerance_level'
    >;
  }

  type Emits = (e: 'batch-edit', value: { count: number; specData: TicketSpecInfo; specId: number }) => void;

  const props = withDefaults(defineProps<Props>(), {
    allClusters: () => [],
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<TicketSpecInfo>({
    required: true,
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const isShow = ref(false);
  const isShowBatchEdit = ref(false);
  const batchFormRef = ref<InstanceType<(typeof import('bkui-vue'))['BkForm']>>();
  const specSelectorRef = ref<InstanceType<typeof SpecSelector>>();

  // 批量编辑表单数据
  const batchFormData = reactive({
    count: undefined as number | undefined,
    specId: '' as number | string,
  });

  // 批量编辑表单校验规则
  const batchFormRules = {
    count: [
      {
        message: () => t('请输入数量'),
        trigger: 'change',
        validator: (value: number) => Boolean(value),
      },
    ],
    specId: [
      {
        message: () => t('请选择规格'),
        trigger: 'change',
        validator: (value: string | number) => Boolean(value),
      },
    ],
  };

  // 校验状态枚举
  enum ValidateStatus {
    /** 全部跳过 */
    AllSkip = 'all_skip',
    /** 全部可应用 */
    AllValid = 'all_valid',
    /** 未填 */
    Empty = 'empty',
    /** 部分跳过 */
    PartialSkip = 'partial_skip',
  }

  /** 校验结果类型定义 */
  interface BatchValidateResult {
    iconType: string;
    message: string;
    skipCount: number;
    status: ValidateStatus;
    theme: '' | 'info' | 'warning' | 'danger';
    validCount: number;
  }

  /** 校验各行的 cluster_shard_num 是否能被数量整除 */
  const validateResult = computed<BatchValidateResult>(() => {
    const allRows = props.allClusters;
    if (!allRows.length) {
      return {
        iconType: '',
        message: '',
        skipCount: 0,
        status: ValidateStatus.Empty,
        theme: '',
        validCount: 0,
      };
    }

    const count = batchFormData.count;
    if (!count) {
      return {
        iconType: 'info-circle',
        message: t('将应用到全部_n_行', { n: allRows.length }),
        skipCount: 0,
        status: ValidateStatus.Empty,
        theme: 'info',
        validCount: allRows.length,
      };
    }

    let validCount = 0;
    let skipCount = 0;

    for (const row of allRows) {
      const shardNum = row.cluster_shard_num;
      if (shardNum > 0 && shardNum % count === 0) {
        validCount++;
      } else {
        skipCount++;
      }
    }

    if (skipCount === 0) {
      return {
        iconType: 'info-circle',
        message: t('将应用到全部_n_行；各行列单机分片数将按集群分片数除以数量自动计算', { n: allRows.length }),
        skipCount,
        status: ValidateStatus.AllValid,
        theme: 'info',
        validCount,
      };
    }
    if (validCount > 0) {
      return {
        iconType: 'info-circle',
        message: t('将应用到_x_行_y_行算不出整数的单机分片数_本次跳过', { x: validCount, y: skipCount }),
        skipCount,
        status: ValidateStatus.PartialSkip,
        theme: 'warning',
        validCount,
      };
    }
    return {
      iconType: 'info-circle',
      message: t('当前数量算不出任何集群的整数单机分片数_请调整数量'),
      skipCount,
      status: ValidateStatus.AllSkip,
      theme: 'danger',
      validCount: 0,
    };
  });

  const validateState = computed(() => validateResult.value);

  const handleShow = () => {
    isShow.value = true;
  };

  /** 打开统一设置弹窗 */
  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = true;
  };

  /**
   * BatchEditColumn 确认回调
   * 校验通过后 emit batch-edit 到父组件；全部跳过时不做任何操作（弹窗关闭但数据不写入）
   */
  const handleBatchEditChange = () => {
    // 全部跳过时置灰效果：不 emit，弹窗正常关闭，主表无变更
    if (validateResult.value.status === ValidateStatus.AllSkip) {
      return;
    }

    const specData = specSelectorRef.value?.getData();
    const specId = Number(batchFormData.specId);
    const count = batchFormData.count!;

    emits('batch-edit', {
      count,
      specData: {
        cluster_capacity: count * getSpecCapacity(specData?.storage_spec ?? []),
        machine_pair: count,
        spec_id: specId,
        spec_name: specData?.spec_name ?? '',
      },
      specId,
    });
  };

  /**
   * 从规格的 storage_spec 中获取 /data1 或 /data 的容量值
   */
  const getSpecCapacity = (storageSpec: { min?: number; mount_point?: string }[]): number => {
    let specCapacity = 0;
    for (let i = 0; i < storageSpec.length; i++) {
      const item = storageSpec[i];
      if (item.mount_point === '/data1') {
        return item.min ?? 0;
      }
      if (item.mount_point === '/data') {
        specCapacity = (item.min ?? 0) / 2;
      }
    }
    return specCapacity;
  };
</script>

<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
