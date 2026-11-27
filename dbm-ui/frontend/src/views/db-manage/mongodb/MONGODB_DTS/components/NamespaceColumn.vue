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
    :label="t('命名空间')"
    :min-width="280"
    :required="false"
    :rules="rules">
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :title="t('命名空间')"
        type="taginput"
        @change="handleBatchEdit">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-select-button"
          @click="isShowBatchEdit = true">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableTagInput
      v-model="modelValue"
      allow-create
      clearable
      :placeholder="t('留空则同步全部用户库表')"
      :split-fn="tagInputSplitFn" />
    <template #tips>
      <div class="mongo-dts-namespace-tips">
        <div style="font-weight: 700">{{ t('命名空间输入说明') }}：</div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('留空表示同步除 admin、local、config 外的全部用户库表') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('填写库或库.表，不支持通配符') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('单元格可同时输入多个对象，使用换行，空格或；，｜分隔，按 Enter 或失焦完成内容输入') }}</span>
        </div>
      </div>
    </template>
  </EditableColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    field?: string;
  }

  type Emits = (e: 'batch-edit', value: string[]) => void;

  withDefaults(defineProps<Props>(), {
    field: 'namespaces',
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const systemDbs = ['admin', 'config', 'local'];

  const rules = [
    {
      message: t('命名空间不支持通配，且不能包含空格'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => item.length > 0 && !/[ ;*\n\t]/.test(item)),
    },
    {
      message: t('不允许输入系统库和特殊库'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => !systemDbs.includes(item.split('.')[0] || '')),
    },
  ];

  const isShowBatchEdit = ref(false);

  const tagInputSplitFn = (value: string) => value.split(batchSplitRegex);

  const handleBatchEdit = (value: string[] | string) => {
    emits('batch-edit', value as string[]);
  };
</script>

<style lang="less">
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .mongo-dts-namespace-tips {
    div {
      display: flex;
      align-items: center;

      .circle-dot {
        display: inline-block;
        width: 4px;
        height: 4px;
        margin-right: 6px;
        background-color: #63656e;
        border-radius: 50%;
      }
    }
  }
</style>
