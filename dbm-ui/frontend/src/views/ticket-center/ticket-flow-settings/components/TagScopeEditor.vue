<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DBM(BlueKing-BK-DBM) available.
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
  <div class="tag-scope-editor">
    <DbForm
      form-type="vertical"
      :model="formModel">
      <!-- 标签键 -->
      <FormItemWithHint
        ref="keyFormItemRef"
        :label="t('标签键')"
        :model="selectedKey"
        property="tag_key"
        required>
        <BkSelect
          v-model="selectedKey"
          :clearable="false"
          :disabled="disabled"
          filterable
          :placeholder="t('请选择标签键')"
          @change="handleKeyChange">
          <!-- 已保存但失效的键：置顶展示并标「已失效」，禁用选择 -->
          <BkOption
            v-if="invalidSavedKey"
            disabled
            :label="`${invalidSavedKey}（${t('已失效')}）`"
            :value="invalidSavedKey">
            <span class="invalid-key-label">
              {{ invalidSavedKey }}
              <BkTag
                size="small"
                theme="danger">
                {{ t('已失效') }}
              </BkTag>
            </span>
          </BkOption>
          <!-- 有效键列表 -->
          <BkOption
            v-for="key in validKeyList"
            :key="key"
            :label="key"
            :value="key" />
        </BkSelect>
      </FormItemWithHint>

      <!-- 标签值（键选定后展示） -->
      <FormItemWithHint
        ref="valueFormItemRef"
        :label="t('标签值')"
        :model="selectedValues"
        property="tag_value"
        required
        :rules="tagRepeatRules">
        <BkSelect
          v-model="selectedValues"
          :all-option-id="TAG_ANY_VALUE"
          :all-option-text="t('任意值')"
          :disabled="isKeyInvalid || !selectedKey"
          filterable
          :input-search="false"
          multiple
          multiple-mode="tag"
          :placeholder="t('请选择标签值')"
          selected-style="checkbox"
          :show-all="!!selectedKey && !isKeyInvalid"
          show-select-all
          @change="handleTagValueChange">
          <template #tag="{ selected }">
            <BkTag
              v-for="item in selected"
              :key="item.value ?? item"
              closable
              @close="() => handleRemoveValue(item.value ?? item)">
              {{ item.value === TAG_ANY_VALUE ? t('任意值') : (item.label ?? item.value ?? item) }}
            </BkTag>
          </template>
          <BkOption
            v-for="value in valueOptions"
            :key="value"
            :disabled="isKeyInvalid"
            :label="value"
            :value="value" />
          <!-- 失效键时展示已保存值且禁用 -->
          <BkOption
            v-for="value in invalidSavedValues"
            :key="`invalid-${value}`"
            disabled
            :label="value"
            :value="value" />
        </BkSelect>
      </FormItemWithHint>

      <!-- 失效提示 -->
      <BkAlert
        v-if="isKeyInvalid"
        class="mt-8"
        theme="warning">
        {{ t('该标签键已从业务移除') }}
      </BkAlert>
    </DbForm>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { TAG_ANY_VALUE, type TagMatchType } from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { checkTicketFlowConfigClusterTagRepeat, type ClusterTagItem } from '@services/source/ticket';

  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  import { useClusterTags } from '../hooks/use-cluster-tags';

  interface Props {
    /** 业务 ID（标签重复校验入参） */
    bizId: number;
    /** 编辑态回填的已保存标签条件 */
    clusterTags?: ClusterTagItem[];
    /** 当前编辑的子策略 id，仅编辑态传入（用于后端重复校验排除自身） */
    configId?: number;
    /** 是否禁用（只读场景） */
    disabled?: boolean;
    /** 当前编辑的单据类型（标签重复校验入参） */
    ticketType: string;
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    clearValidate: () => void;
    /** 获取标签条件与匹配类型；校验失败 reject */
    getValue: () => Promise<{ clusterTags: ClusterTagItem[]; matchType: TagMatchType }>;
    reset: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterTags: () => [],
    configId: undefined,
    disabled: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  // 标签键值聚合（失效判定由后端 is_invalid 字段提供）
  const { getTagId, keyValueMap } = useClusterTags();

  const keyFormItemRef = ref<InstanceType<typeof FormItemWithHint>>();
  const valueFormItemRef = ref<InstanceType<typeof FormItemWithHint>>();

  const selectedKey = ref<string>('');
  // 选中的标签值列表（含「任意值」时为 [TAG_ANY_VALUE]，与具体值互斥）
  const selectedValues = ref<string[]>([]);

  // DbForm 值上下文：property=tag_key/tag_value 由此取值做 required 校验，直接派生无需手动同步
  const formModel = computed(() => ({
    tag_key: selectedKey.value,
    tag_value: selectedValues.value,
  }));

  // 已保存但失效的键（编辑态回填时，键不在有效集合中）
  const invalidSavedKey = ref<string>('');
  // 已保存但失效的具体值（失效键时展示且禁用）
  const invalidSavedValues = ref<string[]>([]);

  const validKeyList = computed(() => Object.keys(keyValueMap.value));

  // 当前键是否失效（编辑回填时由后端 is_invalid 字段判定）
  const isKeyInvalid = computed(() => invalidSavedKey.value !== '');

  const isAnyValue = computed(() => selectedValues.value.includes(TAG_ANY_VALUE));

  const valueOptions = computed(() => keyValueMap.value[selectedKey.value] || []);

  // 清空失效态与已选值（重选键 / 重置共用）
  const clearInvalidAndValues = () => {
    invalidSavedKey.value = '';
    invalidSavedValues.value = [];
    selectedValues.value = [];
  };

  const handleKeyChange = (_value: string) => {
    clearInvalidAndValues();
    emits('change');
  };

  const handleRemoveValue = (value: string) => {
    selectedValues.value = selectedValues.value.filter((v) => v !== value);
    emits('change');
  };

  // 标签重复校验：选值后实时校验，与 SelectClusters 交互保持一致
  // 缓存最近一次入参与错误，避免重复调用接口
  const tagRepeatCache = ref<{ error: string; key: string; values: string }>({ error: '', key: '', values: '' });

  const tagRepeatRules = [
    {
      trigger: 'change',
      validator: async () => {
        if (!selectedKey.value || !selectedValues.value.length || !props.bizId || !props.ticketType) return true;
        const valuesKey = [...selectedValues.value].sort().join(',');
        if (tagRepeatCache.value.key === selectedKey.value && tagRepeatCache.value.values === valuesKey) {
          return tagRepeatCache.value.error || true;
        }
        const tags = isAnyValue.value
          ? [{ tag_key: selectedKey.value, tag_value: TAG_ANY_VALUE }]
          : selectedValues.value.map((v) => ({ tag_key: selectedKey.value, tag_value: v }));
        const checkResult = await checkTicketFlowConfigClusterTagRepeat({
          bk_biz_id: props.bizId,
          cluster_tags: tags,
          config_id: props.configId,
          ticket_type: props.ticketType,
        });
        const duplicateTags = (checkResult || [])
          .filter((item) => item.validate)
          .map((item) => `${item.tag_key} : ${item.tag_value === TAG_ANY_VALUE ? t('任意值') : item.tag_value}`);
        const error =
          duplicateTags.length === 0
            ? ''
            : t('标签 tags 已在其他按标签子策略中，不可重复', { tags: duplicateTags.join('、') });
        tagRepeatCache.value = { error, key: selectedKey.value, values: valuesKey };
        return error || true;
      },
    },
  ];

  // 选值变化时延迟校验（确保 v-model 已更新）
  const handleTagValueChange = () => {
    nextTick(() => valueFormItemRef.value?.validate?.());
    emits('change');
  };

  const reset = () => {
    selectedKey.value = '';
    clearInvalidAndValues();
  };

  // 编辑态回填（reset 需在 watch 之前定义，immediate: true 会立即执行回调）
  watch(
    () => props.clusterTags,
    (tags) => {
      if (tags && tags.length > 0) {
        const key = tags[0].tag_key;
        selectedKey.value = key;
        // 任意值：回填为 [TAG_ANY_VALUE]
        if (tags.some((item) => item.tag_value === TAG_ANY_VALUE)) {
          selectedValues.value = [TAG_ANY_VALUE];
        } else {
          selectedValues.value = tags.map((item) => item.tag_value);
        }
        // 失效判定：后端在 cluster_tags 每项返回 is_invalid 字段，任一项为 true 即视为失效
        if (tags.some((item) => item.is_invalid === true)) {
          invalidSavedKey.value = key;
          invalidSavedValues.value = tags
            .filter((item) => item.tag_value !== TAG_ANY_VALUE)
            .map((item) => item.tag_value);
        } else {
          invalidSavedKey.value = '';
          invalidSavedValues.value = [];
        }
      } else {
        reset();
      }
    },
    { immediate: true },
  );

  defineExpose<Exposes>({
    clearValidate: () => {
      keyFormItemRef.value?.clearValidate?.();
      valueFormItemRef.value?.clearValidate?.();
    },
    async getValue() {
      // validate 失败会 reject，由父组件捕获后不提交
      // tagRepeatRules 内已包含标签重复校验（change 触发）
      await keyFormItemRef.value?.validate?.();
      await valueFormItemRef.value?.validate?.();

      const values = isAnyValue.value ? [TAG_ANY_VALUE] : selectedValues.value;
      const matchType: TagMatchType = isAnyValue.value ? 'exists' : values.length === 1 ? 'single' : 'in';
      const clusterTags: ClusterTagItem[] = values.map((value) => ({
        id: getTagId(selectedKey.value, value),
        tag_key: selectedKey.value,
        tag_value: value,
      }));

      return { clusterTags, matchType };
    },
    reset,
  });
</script>

<style lang="less" scoped>
  .tag-scope-editor {
    padding: 16px 16px 32px 16px;
    background: #f5f7fa;

    .invalid-key-label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    // BkAlert 位于 BkFormItem 的 bk-form-content 内，会继承 line-height: 32px，
    // 导致 Alert 内部文字行高被撑大产生形变，此处重置行高修复
    :deep(.bk-alert) {
      line-height: 20px;
    }
  }
</style>
