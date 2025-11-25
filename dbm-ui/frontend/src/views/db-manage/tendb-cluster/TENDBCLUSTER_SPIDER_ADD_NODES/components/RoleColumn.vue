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
    field="role"
    :label="t('扩容节点类型')"
    :min-width="150"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :data-list="defaultOptions"
        :title="t('扩容节点类型')"
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
    <EditableSelect
      v-model="modelValue"
      :input-search="false"
      :list="renderList"
      @change="handleChange" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    cluster: {
      spider_master: TendbClusterModel['spider_master'];
      spider_slave: TendbClusterModel['spider_slave'];
    };
  }

  type Emits = (e: 'batch-edit', value: string[], field: string) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const roleCount = defineModel<number>('roleCount', {
    required: true,
  });

  const { t } = useI18n();

  const defaultOptions = [
    {
      label: 'Spider Master',
      value: 'spider_master',
    },
    {
      label: 'Spider Slave',
      value: 'spider_slave',
    },
  ];

  const renderList = ref<
    {
      label: string;
      value: string;
    }[]
  >([]);

  const showBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[] | string) => {
    emits('batch-edit', value as string[], 'role');
  };

  const handleChange = (role: string) => {
    modelValue.value = role;
    roleCount.value = props.cluster[role as keyof Props['cluster']]?.length || 0;
  };

  watch(
    () => props.cluster,
    () => {
      const list = defaultOptions.filter(
        (item) => props.cluster[item.value as 'spider_master' | 'spider_slave'].length > 0,
      );
      const firstRole = list?.[0]?.value;
      renderList.value = list;
      handleChange(firstRole);
    },
  );

  watch(
    modelValue,
    (newVal) => {
      const isExist = renderList.value.some((item) => item.value === newVal);
      if (isExist) {
        handleChange(newVal);
      } else {
        modelValue.value = '';
        roleCount.value = 0;
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
