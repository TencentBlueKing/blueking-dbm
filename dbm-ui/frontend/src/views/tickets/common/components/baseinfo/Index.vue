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
  <div class="base-container">
    <template
      v-for="(list, index) of columns"
      :key="index + unique">
      <ul
        class="base-info"
        :style="{ '--width': width }">
        <li
          v-for="config of list"
          :key="config.key"
          class="info-item">
          <span class="info-label">
            <span
              v-overflow-tips
              class="text-overflow">
              {{ config.label }}
            </span>
            ：
          </span>
          <div class="base-info-value-container">
            <BkForm
              v-if="editState.key === config.key && !readonly"
              class="info-edit"
              :model="editState">
              <BkFormItem
                ref="editItemRef"
                class="mb-0"
                error-display-type="tooltips"
                label-width="0"
                property="value"
                :rules="config.isRequired === true ? rules : undefined">
                <BkInput
                  ref="editInputRef"
                  v-model="editState.value"
                  :disabled="loading"
                  :placeholder="$t('请输入')"
                  style="width: 240px"
                  @blur="handleSaveEdit"
                  @enter="handleSaveEdit" />
                <BkLoading
                  class="info-loading"
                  :loading="loading"
                  mode="spin"
                  size="mini"
                  theme="primary" />
              </BkFormItem>
            </BkForm>
            <template v-else>
              <span
                v-overflow-tips
                class="base-info__value text-overflow">
                <Component
                  :is="config.render"
                  v-if="config.render" />
                <template v-else>{{ data[config.key] || '--' }}</template>
              </span>
              <div class="info-icons">
                <i
                  v-if="config.isEdit && !readonly"
                  class="info-icon db-icon-edit"
                  @click.stop="handleEdit(config.key, data[config.key])" />
                <i
                  v-if="config.isCopy"
                  class="info-icon db-icon-copy"
                  @click.stop="handleCopy(data[config.key])" />
              </div>
            </template>
          </div>
        </li>
      </ul>
    </template>
  </div>
</template>
<script lang="ts">
  import type { VNode } from 'vue';

  import { useCopy } from '@hooks';

  import { generateId } from '@utils';

  import { t } from '@locales/index';

  export type InfoColumn = {
    label: string;
    key: string;
    isEdit?: boolean;
    isCopy?: boolean;
    isRequired?: boolean;
    render?: () => VNode | string | null;
  };

  export type EditEmitData = {
    value: string;
    key: string;
    editResolve: (value: unknown) => void;
  };

  /**
   * 默认显示信息配置
   */
  export const getDefaultColumns = () => [
    [
      {
        label: t('配置名称'),
        key: 'name',
        isEdit: true,
        isRequired: true,
      },
      {
        label: t('描述'),
        key: 'description',
        isEdit: true,
      },
      {
        label: t('数据库版本'),
        key: 'version',
      },
    ],
    [
      {
        label: t('更新时间'),
        key: 'updated_at',
      },
      {
        label: t('更新人'),
        key: 'updated_by',
      },
    ],
  ];

  export default {
    name: 'EditableInfo',
  };
</script>

<script setup lang="ts">
  interface Props {
    readonly?: boolean,
    columns?: Array<Array<InfoColumn>>,
    data?: Record<string, any>,
    width?: string,
  }

  interface Emits {
    (e: 'save', value: EditEmitData): void
  }

  const props = withDefaults(defineProps<Props>(), {
    readonly: false,
    columns: () => getDefaultColumns(),
    data: () => ({}),
    width: '50%',
  });
  const emits = defineEmits<Emits>();

  const unique = ref(generateId('EDITABLE_INFO_KEY_', 6));
  const loading = ref(false);
  const rules = [{ required: true, trigger: 'blur', message: t('必填项') }];

  watch(() => props.columns, () => {
    unique.value = generateId('EDITABLE_INFO_KEY_', 6);
  }, { deep: true });

  /**
   * 编辑基本信息
   */
  const editState = reactive({
    value: '',
    key: '',
  });
  const editItemRef = ref();
  const editInputRef = ref();
  const handleEdit = (key: string, value: string) => {
    editState.key = key;
    editState.value = value;
    loading.value = false;

    // focus
    nextTick(() => {
      const [inputRef] = editInputRef.value || [];
      inputRef?.focus?.();
    });
  };
  const handleSaveEdit = async () => {
    // 内容没变更则不触发保存
    if (editState.value === props.data[editState.key]) {
      editState.value = '';
      editState.key = '';
      return;
    }

    const validate = await editItemRef.value[0]?.validate()
      .then(() => true)
      .catch(() => false);
    if (validate) {
      loading.value = true;
      let editResolve = (value: unknown = true) => value;
      const promise = new Promise(resolve => editResolve = resolve);
      emits('save', { ...editState, editResolve });
      const res = await promise;
      loading.value = false;
      if (res) {
        editState.value = '';
        editState.key = '';
      }
    }
  };

  /**
   * 复制信息
   */
  const handleCopy = useCopy();
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .base-container {
    display: flex;
    font-size: @font-size-mini;
  }

  .base-info {
    flex: 0 1 var(--width);
    max-width: var(--width);

    .info-item {
      .flex-center();

      line-height: 32px;
    }

    .info-label {
      display: flex;
      flex-shrink: 0;
      width: 140px;
      padding-left: 10px;
      text-align: right;
      justify-content: flex-end;
    }

    .base-info-value-container {
      .flex-center();

      overflow: hidden;
      color: @title-color;
      flex: 1;
    }

    .info-edit {
      :deep(.bk-form-label) {
        padding-right: 0;
      }
    }

    .info-icons {
      .flex-center();
    }

    .info-icon {
      margin-left: 4px;
      font-size: @font-size-normal;
      color: @primary-color;
      cursor: pointer;
    }

    .info-loading {
      position: absolute;
      top: 50%;
      right: 8px;
      transform: translateY(-50%);
    }
  }
</style>
