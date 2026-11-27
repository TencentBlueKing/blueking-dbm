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
          <DbTag style="height: 16px; margin-left: 4px">
            <span style="color: #3a84ff">{{ t('键:值') }}</span>
          </DbTag>
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
        <template v-if="!isDisabled">
          <DbIcon type="qiehuan" />
          <BkButton
            text
            theme="primary"
            @click="handleSwitchMode">
            {{ isKeyValueMode ? t('切换文本编辑') : t('切换网格编辑') }}
          </BkButton>
        </template>
      </div>
    </div>
    <Component
      :is="renderMode"
      ref="modeRef"
      :allow-empty="allowKeyValueEmpty"
      :biz-id="modeBizId"
      :data="tagsPairData"
      :disabled="isDisabled"
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
    getValue: (isIgnoreVerify?: boolean) => Promise<TagsPairType[] | null>;
  }

  interface Props {
    allowKeyValueEmpty?: boolean;
    /** 标签候选查询的业务 ID；不传回退到当前页面业务，业务切换时重新查询，未选择业务时整体禁用 */
    bizId?: number | '';
    data?: { id: number; key: string; value: string }[];
  }

  type Emits = (e: 'change') => void;

  const props = withDefaults(defineProps<Props>(), {
    allowKeyValueEmpty: true,
    bizId: window.PROJECT_CONFIG.BIZ_ID,
    data: () => [],
  });

  const emits = defineEmits<Emits>();

  // 未选择业务（空字符串）时禁用编辑；0 是全业务/公共业务，属于合法业务 ID
  const isDisabled = computed(() => props.bizId === '' || props.bizId === null || props.bizId === undefined);
  const modeBizId = computed(() => (props.bizId === '' ? undefined : props.bizId));

  const { t } = useI18n();

  const modeRef = ref();
  const editMode = ref('key_value');
  const tagsPairData = ref<TagsPairType[]>([]);

  // 标签候选由「内置标签 + 业务标签」两个数据源组合；内置只查一次，业务随 bizId 变化重新查询
  const builtinKeyValueMap = ref<KeyValueMapType>({});
  const businessKeyValueMap = ref<KeyValueMapType>({});
  const keyValueMap = computed<KeyValueMapType>(() => {
    const results: KeyValueMapType = {};
    Object.entries(builtinKeyValueMap.value).forEach(([key, values]) => {
      Object.assign(results, { [key]: [...values] });
    });
    Object.entries(businessKeyValueMap.value).forEach(([key, values]) => {
      if (results[key]) {
        results[key].push(...values.filter((value) => !results[key].includes(value)));
      } else {
        Object.assign(results, { [key]: [...values] });
      }
    });
    return results;
  });

  const isKeyValueMode = computed(() => editMode.value === 'key_value');
  const renderMode = computed(() => renderModeMap[editMode.value]);
  const dataTagIds = computed(() => _.sortBy(props.data.map((item) => item.id)));

  const renderModeMap: Record<string, any> = {
    key_value: KeyValueMode,
    text: TextMode,
  };

  const { run: fetchBuiltinLabels } = useRequest(getBuiltinLabels, {
    manual: true,
    onSuccess(dataList) {
      builtinKeyValueMap.value = dataList.reduce<KeyValueMapType>((results, key) => {
        Object.assign(results, { [key]: [] });
        return results;
      }, {});
    },
  });

  const { run: fetchTagList } = useRequest(listTag, {
    manual: true,
    onSuccess(data) {
      businessKeyValueMap.value = data.results.reduce<KeyValueMapType>((results, item) => {
        if (results[item.key]) {
          results[item.key].push(item.value);
        } else {
          Object.assign(results, { [item.key]: [item.value] });
        }
        return results;
      }, {});
    },
  });

  // 内置标签键是全局数据，挂载即拉取一次，不依赖业务候选查询成败
  onMounted(() => {
    fetchBuiltinLabels();
  });

  // 标签候选按业务维度查询，业务切换时重新查询；未选择业务（空字符串）时不查询；
  // 0 是全业务/公共业务的合法 ID，需要正常查询
  // 业务切换后已填数据不再适用，同步清空回一条空白行
  watch(
    () => props.bizId,
    (bizId) => {
      tagsPairData.value = [];
      if (bizId === '' || bizId === null || bizId === undefined) {
        // 清空业务候选，computed 组合后仅保留内置标签
        businessKeyValueMap.value = {};
        return;
      }
      // 先清空上一业务的候选，避免新结果返回前短暂展示旧业务标签
      businessKeyValueMap.value = {};
      fetchTagList({
        bk_biz_id: bizId,
        limit: -1,
        offset: 0,
        type: 'cluster',
      });
    },
    { immediate: true },
  );

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
    async getValue(isIgnoreVerify?: boolean) {
      return await modeRef.value!.getValue(isIgnoreVerify);
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
