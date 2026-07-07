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
  <BkAlert
    class="mb-16"
    theme="info">
    <template #title>
      <I18nT
        v-if="!isKeyValueMode"
        keypath="每行一个标签，格式n"
        tag="span">
        <template #n>
          <BkTag style="height: 16px; margin-left: 4px">
            <span style="color: #3a84ff">键:值</span>
          </BkTag>
        </template>
      </I18nT>
      <div>{{ t('标签键 / 值：支持中文、字母、数字、连字符、下划线、点号') }}</div>
    </template>
  </BkAlert>
  <div class="cluster-add-tag-main">
    <div class="title-opeartion-main">
      <template v-if="isKeyValueMode">
        <div class="column-title title-key">{{ t('标签键') }}</div>
        <div class="column-title title-value">{{ t('标签值') }}</div>
      </template>
      <div class="switch-operation">
        <DbIcon type="qiehuan" />
        <BkButton
          text
          theme="primary"
          @click="handleSwitchMode">
          {{ isKeyValueMode ? t('切换文本编辑') : t('切换网格编辑') }}
        </BkButton>
      </div>
    </div>
    <Component
      :is="renderMode"
      ref="modeRef"
      :allow-empty="allowKeyValueEmpty"
      :data="tagsPairData"
      :key-value-map="keyValueMap"
      @change="() => emits('change')" />
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBuiltinLabels } from '@services/source/systemSettings';
  import { listTag } from '@services/source/tag';

  import KeyValueMode from './components/key-value-mode/Index.vue';
  import TextMode from './components/TextMode.vue';

  export type TagsPairType = {
    key: string;
    value: string;
  };

  export type KeyValueMapType = Record<string, string[]>;

  interface Exposes {
    getValue: (isIgnoreVerify?: boolean) => Promise<TagsPairType[]>;
  }

  interface Props {
    allowKeyValueEmpty?: boolean;
    data?: { id: number; key: string; value: string }[];
  }

  type Emits = (e: 'change') => void;

  const props = withDefaults(defineProps<Props>(), {
    allowKeyValueEmpty: true,
    data: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const modeRef = ref();
  const editMode = ref('key_value');
  const tagsPairData = ref<TagsPairType[]>([]);
  const keyValueMap = ref<KeyValueMapType>({});

  const isKeyValueMode = computed(() => editMode.value === 'key_value');
  const renderMode = computed(() => renderModeMap[editMode.value]);
  const dataTagIds = computed(() => _.sortBy(props.data.map((item) => item.id)));

  const renderModeMap: Record<string, any> = {
    key_value: KeyValueMode,
    text: TextMode,
  };

  const { run: handleGetBuiltinLabels } = useRequest(getBuiltinLabels, {
    manual: true,
    onSuccess(dataList) {
      dataList.forEach((innerKey) => {
        if (!keyValueMap.value[innerKey]) {
          Object.assign(keyValueMap.value, {
            [innerKey]: [],
          });
        }
      });
    },
  });

  useRequest(listTag, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        limit: -1,
        offset: 0,
        type: 'cluster',
      },
    ],
    onSuccess(data) {
      keyValueMap.value = data.results.reduce<typeof keyValueMap.value>((results, item) => {
        if (results[item.key]) {
          results[item.key].push(item.value);
        } else {
          Object.assign(results, {
            [item.key]: [item.value],
          });
        }
        return results;
      }, {});
      handleGetBuiltinLabels();
    },
  });

  watch(
    dataTagIds,
    (newTagIds, oldTagIds) => {
      if (_.isEqual(newTagIds, oldTagIds)) {
        return;
      }
      if (props.data.length) {
        tagsPairData.value = props.data.map((item) => ({
          key: item.key,
          value: item.value,
        }));
      }
    },
    {
      immediate: true,
    },
  );

  const handleSwitchMode = async () => {
    const inputData = await modeRef.value!.getValue(true);
    if (inputData) {
      tagsPairData.value = inputData;
      nextTick(() => {
        editMode.value = isKeyValueMode.value ? 'text' : 'key_value';
      });
    }
  };

  defineExpose<Exposes>({
    async getValue() {
      return await modeRef.value!.getValue();
    },
  });
</script>

<style lang="less">
  .cluster-add-tag-main {
    .title-opeartion-main {
      display: flex;
      align-items: center;
      margin-bottom: 8px;
      font-size: 12px;

      .column-title {
        position: relative;
        font-weight: 700;

        &::after {
          position: absolute;
          top: 2px;
          left: 42px;
          color: #ea3636;
          content: '*';
        }

        &.title-key {
          width: 254px;
        }

        &.title-value {
          flex: 1;
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
