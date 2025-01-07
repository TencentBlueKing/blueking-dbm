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
    :label="label"
    :min-width="200"
    :required="required">
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :title="label"
        type="taginput"
        @change="handleBatchEditChange">
        <BkButton
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          text
          theme="primary"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </BkButton>
      </BatchEditColumn>
    </template>
    <div
      ref="root"
      class="edit-regex-keys-content"
      @click="handleShowTips">
      <EditableTagInput
        v-model="modelValue"
        allow-auto-match
        allow-create
        clearable
        has-delete-icon
        :placeholder="t('请输入正则表达式')"
        @change="handleChange" />
      <div style="display: none">
        <div
          ref="pop"
          style="font-size: 12px; line-height: 24px; color: #63656e">
          <p style="font-weight: bold">
            {{ t('可使用通配符进行提取，如：') }}
          </p>
          <p>{{ t('*Key$ ：提取以 Key 结尾的 key，包括 Key') }}</p>
          <p>{{ t('^Key$：提取精确匹配的Key') }}</p>
          <p>{{ t('* ：代表所有') }}</p>
        </div>
      </div>
    </div>
  </EditableColumn>
</template>

<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { Column as EditableColumn } from '@components/editable-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    label: string;
    field: string;
    required?: boolean;
  }

  interface Emits {
    (e: 'batch-edit', value: string[], field: string): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    required: false,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  let tippyIns: Instance | undefined;

  const isShowBatchEdit = ref(false);
  const rootRef = useTemplateRef('root');
  const popRef = useTemplateRef('pop');

  const handleBatchEditShow = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[] | string) => {
    emits('batch-edit', value as string[], props.field);
  };

  const handleShowTips = () => {
    tippyIns?.show();
  };

  const handleChange = (value: string[]) => {
    if (value.includes('*') && value.length > 1) {
      // 已经输入默认全部，不能继续输入其他字符
      modelValue.value = ['*'];
    }
  };

  onMounted(() => {
    nextTick(() => {
      if (rootRef.value !== null) {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          content: popRef.value,
          placement: 'top',
          appendTo: () => document.body,
          theme: 'light',
          maxWidth: 'none',
          trigger: 'manual',
          interactive: true,
          arrow: true,
          offset: [0, 18],
          zIndex: 9998,
          hideOnClick: true,
        });
      }
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });
</script>

<style lang="less" scoped>
  .edit-regex-keys-content {
    width: 100%;
  }
</style>
