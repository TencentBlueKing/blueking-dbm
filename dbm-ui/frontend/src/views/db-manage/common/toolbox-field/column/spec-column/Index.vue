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
    :field="field"
    :label="t(label)"
    :min-width="minWidth"
    :required="required"
    :rules="rules">
    <template
      v-if="selectable"
      #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :data-list="batchEditSpecList"
        :placeholder="t('请选择')"
        :title="t(label)"
        type="select"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableBlock
      v-if="!selectable"
      v-model="renderSpecName"
      :placeholder="t('自动生成')" />
    <EditableSelect
      v-else
      v-model="modelValue"
      display-key="spec_name"
      id-key="spec_id"
      :list="sortedSpecList">
      <template #option="{ item }">
        {{ item.spec_name }}
        <BkTag
          v-if="currentSpecIdList?.includes(item.spec_id) && showTag"
          class="ml-4"
          size="small"
          theme="success">
          {{ t('当前规格') }}
        </BkTag>
      </template>
    </EditableSelect>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { ClusterTypes, DBTypes, MachineTypes } from '@common/const';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    clusterType: ClusterTypes | DBTypes;
    /**
     * 多个【当前规格】
     */
    currentSpecIdList?: number[];
    field?: string;
    label?: string;
    /**
     * 机器类型
     * @default backend
     */
    machineType?: MachineTypes;
    minWidth?: number;
    required?: boolean;
    selectable?: boolean;
    showTag?: boolean;
  }

  type Emits = (e: 'batch-edit', value: number, field: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    currentSpecIdList: () => [],
    field: 'specId',
    label: '规格',
    machineType: undefined,
    minWidth: 150,
    required: false,
    selectable: false,
    showTag: true,
  });

  const emits = defineEmits<Emits>();

  /**
   * 绑定当前选择的规格 ID
   */
  const modelValue = defineModel<number>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('规格不能为空'),
      trigger: 'change',
      validator: (value: number) => Boolean(value),
    },
  ];

  const specList = ref<ServiceReturnType<typeof getResourceSpecList>['results']>([]);
  const showBatchEdit = ref(false);

  const batchEditSpecList = computed(() =>
    specList.value.map((item) => ({
      label: item.spec_name,
      value: item.spec_id,
    })),
  );
  const renderSpecName = computed(
    () => specList.value.find((item) => item.spec_id === modelValue.value)?.spec_name || '',
  );
  const sortedSpecList = computed(() => {
    if (!props.currentSpecIdList?.length) {
      return specList.value;
    }
    // 当前规格排在前面
    const currentSpecSet = new Set(props.currentSpecIdList);
    return specList.value.sort((a, b) => {
      const aIsCurrent = currentSpecSet.has(a.spec_id);
      const bIsCurrent = currentSpecSet.has(b.spec_id);
      return aIsCurrent === bIsCurrent ? 0 : aIsCurrent ? -1 : 1;
    });
  });

  const { run: fetchData } = useRequest(getResourceSpecList, {
    manual: true,
    onSuccess: (data) => {
      specList.value = data.results || [];
    },
  });

  watch(
    () => [props.selectable, props.clusterType, props.machineType],
    () => {
      fetchData({
        enable: props.selectable ? true : undefined,
        limit: -1,
        spec_cluster_type: props.clusterType,
        spec_machine_type: props.machineType,
      });
    },
    {
      immediate: true,
    },
  );

  // 初始化
  watch(
    () => [modelValue.value, props.currentSpecIdList],
    () => {
      const currentSpecIdList = _.uniq(props.currentSpecIdList);
      const isSame = currentSpecIdList.length === 1;
      const [currentSpecId] = currentSpecIdList;
      // 所有主机规格相同时则默认填充此规格。各主机规格不同时默认值留空。
      if (!modelValue.value && isSame && currentSpecId) {
        modelValue.value = currentSpecId;
      }

      // 如果 modelValue 被设置为 字符串 时，若在规格列表中匹配到对应规格则选中（用于批量录入）
      if (modelValue.value && typeof modelValue.value === 'string') {
        const matchedSpecId = specList.value.filter(
          (item) => item.spec_name === (modelValue.value as unknown as string),
        )?.[0]?.spec_id;
        if (matchedSpecId) {
          modelValue.value = matchedSpecId;
        }
      }
    },
    {
      immediate: true,
    },
  );

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: number) => {
    emits('batch-edit', value, props.field);
  };
</script>
<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
