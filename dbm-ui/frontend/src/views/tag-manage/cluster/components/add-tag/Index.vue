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
  <div class="create-tag-content-main">
    <div class="title-opeartion-main">
      <template v-if="isKeyValueMode">
        <div class="title title-key">{{ t('标签键') }}</div>
        <div class="title title-value">{{ t('标签值') }}</div>
      </template>
      <div class="switch-operation">
        <DbIcon type="qiehuan" />
        <BkButton
          text
          theme="primary"
          @click="handleSwitchMode">
          {{ isKeyValueMode ? t('切换文本编辑') : t('切换为 key/value') }}
        </BkButton>
      </div>
    </div>
    <Component
      :is="renderMode"
      ref="modeRef"
      :data="tagsPairData"
      :existed-keys="existedKeys" />
  </div>
</template>

<script setup lang="tsx">
  import { computed, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import KeyValueMode from './components/key-value-mode/Index.vue';
  import TextMode from './components/TextMode.vue';

  export type TagsPairType = Record<string, string[]>;

  interface Props {
    existedKeys: Set<string>;
  }

  interface Exposes {
    getValue: () => TagsPairType | null;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const modeRef = ref();
  const editMode = ref('key_value');
  const tagsPairData = ref<TagsPairType>();

  const isKeyValueMode = computed(() => editMode.value === 'key_value');
  const renderMode = computed(() => renderModeMap[editMode.value]);

  const renderModeMap: Record<string, any> = {
    key_value: KeyValueMode,
    text: TextMode,
  };

  const handleSwitchMode = () => {
    const inputData = modeRef.value!.getValue(true);
    if (inputData) {
      tagsPairData.value = inputData;
      nextTick(() => {
        editMode.value = isKeyValueMode.value ? 'text' : 'key_value';
      });
    }
  };

  defineExpose<Exposes>({
    getValue() {
      return modeRef.value!.getValue();
    },
  });
</script>

<style lang="less">
  .create-tag-content-main {
    .title-opeartion-main {
      display: flex;
      align-items: center;
      margin-bottom: 8px;
      font-size: 12px;

      .title {
        font-weight: 700;

        &.title-key {
          width: 225px;
        }

        &.title-value {
          width: 300px;
        }
      }

      .switch-operation {
        flex: 1;
        display: flex;
        justify-content: flex-end;
        align-items: center;
        color: #3a84ff;
      }
    }
  }
</style>
