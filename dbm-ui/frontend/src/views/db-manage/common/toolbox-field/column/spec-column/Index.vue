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
    v-test="{ type: 'column', value: 'spec' }"
    :field="field"
    :label="renderLabel"
    :min-width="minWidth"
    :readonly="readonly"
    :required="required"
    :rowspan="rowspan"
    :rules="rules">
    <template
      v-if="tooltips"
      #head>
      <div v-bk-tooltips="tooltips">
        <span class="spec-title">{{ renderLabel }}</span>
      </div>
    </template>
    <template
      v-if="selectable && !onlyShowCurrentSpec"
      #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :data-list="batchEditSpecList"
        :placeholder="t('请选择')"
        :title="renderLabel"
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
      v-if="readonly"
      v-model="renderSpecName"
      :placeholder="t('自动生成')" />
    <EditableSelect
      v-else
      v-model="modelValue"
      display-key="spec_name"
      id-key="spec_id"
      :list="sortedSpecList">
      <template #option="{ item }">
        <div
          v-bk-tooltips="{
            content: t('请选择与当前不同的规格'),
            disabled: !item.disabled,
            placement: 'right',
          }"
          class="spec-column-option">
          {{ item.spec_name }}
          <BkTag
            v-if="showTag && item.isCurrent"
            class="ml-4"
            size="small"
            theme="success">
            {{ t('当前规格') }}
          </BkTag>
        </div>
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
    /**
     * 是否禁用当前规格选项
     */
    disabledCurrentSpec?: boolean;
    field?: string;
    label?: string;
    /**
     * 机器类型
     * @default backend
     */
    machineType?: MachineTypes;
    minWidth?: number;
    /**
     * 仅显示当前规格
     */
    onlyShowCurrentSpec?: boolean;
    required?: boolean;
    rowspan?: number;
    selectable?: boolean;
    showTag?: boolean;
    tooltips?: string;
  }

  type Emits = (e: 'batch-edit', value: number, field: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    currentSpecIdList: () => [],
    disabledCurrentSpec: false,
    field: 'specId',
    label: '',
    machineType: undefined,
    minWidth: 200,
    onlyShowCurrentSpec: false,
    required: false,
    rowspan: 1,
    selectable: false,
    showTag: true,
    tooltips: '',
  });

  const emits = defineEmits<Emits>();

  /**
   * 绑定当前选择的规格 ID
   */
  const modelValue = defineModel<number | string>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('规格不能为空'),
      required: true,
      trigger: 'blur',
      validator: (value: number) => {
        if (!props.required) {
          return true;
        }
        return !!value;
      },
    },
  ];

  const specList = ref<ServiceReturnType<typeof getResourceSpecList>['results']>([]);
  const showBatchEdit = ref(false);

  const renderLabel = computed(() => (props.label ? props.label : !props.selectable ? t('当前规格') : t('目标规格')));
  const readonly = computed(() => !props.selectable);
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
    let list = specList.value.map((item) =>
      Object.assign({}, item, {
        disabled: props.currentSpecIdList?.includes(item.spec_id) && props.disabledCurrentSpec,
        isCurrent: props.currentSpecIdList?.includes(item.spec_id),
      }),
    );

    // 仅显示当前规格
    if (props.onlyShowCurrentSpec) {
      list = list.filter((item) => props.currentSpecIdList?.includes(item.spec_id));
    }

    // 当前规格排在前面
    return list.sort((a, b) => {
      if (a.isCurrent === b.isCurrent) return 0;
      return a.isCurrent ? -1 : 1;
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
      const params = {
        limit: -1,
        spec_cluster_type: props.clusterType,
        spec_machine_type: props.machineType,
      };
      /**
       * 1.规格不变时，即使规格【已停用】，也需要回显规格名
       * 2.规格可选时:
       * 规格来源为集群的当前规格，忽略【启用/停用】标识，显示集群的当前全部规格
       * 规格来源为全部规格，过滤掉【停用】的规格，显示全部【已启用】的规格
       */
      if (props.selectable) {
        Object.assign(params, {
          biz_ids: `${window.PROJECT_CONFIG.BIZ_ID}`,
          enable: props.onlyShowCurrentSpec ? undefined : true,
        });
      }
      fetchData(params);
    },
    {
      immediate: true,
    },
  );

  // 初始化
  watch(sortedSpecList, () => {
    nextTick(() => {
      // 如果 modelValue 被设置为 字符串 时，若在规格列表中匹配到对应规格则选中（用于批量录入）
      if (modelValue.value && typeof modelValue.value === 'string') {
        const matchedSpecId = sortedSpecList.value.filter(
          (item) => item.spec_name === (modelValue.value as unknown as string),
        )?.[0]?.spec_id;
        if (matchedSpecId) {
          modelValue.value = matchedSpecId;
        } else {
          modelValue.value = '';
        }
        return;
      }

      // 如果 modelValue 被设置为 数字 时，若在规格列表中匹配到对应规格则选中,否则重置
      if (props.selectable && modelValue.value && typeof modelValue.value === 'number') {
        const isExist = sortedSpecList.value.some((item) => item.spec_id === modelValue.value);
        if (!isExist) {
          modelValue.value = '';
        }
        return;
      }

      const currentSpecIdList = _.uniq(props.currentSpecIdList);
      const isSame = currentSpecIdList.length === 1;
      const [currentSpecId] = currentSpecIdList;
      // 所有主机规格相同时则默认填充此规格。各主机规格不同时默认值留空。
      if (modelValue.value === 0 && isSame && currentSpecId && !props.disabledCurrentSpec) {
        modelValue.value = currentSpecId;
      }
    });
  });

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: number) => {
    emits('batch-edit', value, props.field);
  };
</script>
<style lang="less" scoped>
  .spec-title {
    border-bottom: 1px dashed #979ba5;
  }

  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .spec-column-option {
    display: flex;
    width: 100%;
    justify-content: space-between;
  }
</style>
