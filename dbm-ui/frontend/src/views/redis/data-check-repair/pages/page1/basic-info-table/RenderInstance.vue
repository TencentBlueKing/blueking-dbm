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
  <BkPopover
    :disabled="isSelectAll || localValue.length < 2"
    placement="top"
    theme="dark">
    <template #content>
      <div
        v-for="item in localValue"
        :key="item">
        {{ item }}
      </div>
    </template>
    <div class="content">
      <BkSelect
        v-model="localValue"
        filterable
        :input-search="false"
        multiple
        show-select-all>
        <template #trigger>
          <div class="item-input">
            {{ displayText }}
          </div>
        </template>
        <BkOption
          v-for="item in selectList"
          :key="item.value"
          :label="item.label"
          :value="item.value" />
      </BkSelect>
      <div
        v-if="!isSelectAll && localValue.length > 1"
        class="more-box">
        <BkTag>
          +{{ localValue.length - 1 }}
        </BkTag>
      </div>
    </div>
  </BkPopover>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { IDataRow } from './Row.vue';

  interface Props {
    selectList?: string[];
    data?: IDataRow['instances'];
  }

  interface Exposes {
    getValue: () => Promise<string[]>
  }

  const props = withDefaults(defineProps<Props>(), {
    selectList: () => ([]),
    data: '',
  });

  const { t } = useI18n();

  const totalText = t('全部');

  const localValue = ref<string[]>([]);
  const displayText = ref(totalText);

  const selectList = computed(() => (props.selectList
    ? props.selectList.map(item => ({ value: item, label: item })) : []));
  const isSelectAll = computed(() => localValue.value.length === props.selectList.length);


  watch(localValue, (list) => {
    if (list.length === props.selectList.length) {
      displayText.value = totalText;
      return;
    }
    if (list.length > 1 && list[0] === totalText) {
      list.shift();
    }
    displayText.value = list.join(' , ');
  });

  watch(() => props.selectList, (list) => {
    if (list.length > 0) {
      localValue.value = list;
    }
  });

  watch(() => props.data, (str) => {
    if (str) {
      localValue.value = str.split('\n');
    }
  }, {
    immediate: true,
  });

  const getFinalValue = () => {
    if (isSelectAll.value || localValue.value.length === 0) {
      return ['all'];
    }
    return localValue.value;
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.resolve(getFinalValue());
    },
  });
</script>
<style lang="less" scoped>


  .item-input {
    width: 100%;
    height: 40px;
    padding: 0 16px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;

    :deep(.bk-input) {
      position: relative;
      height: 40px;
      overflow: hidden;
      border: none;
    }
  }

  .content {
    position: relative;

    .more-box{
      position: absolute;
      top: 0;
      right: 3px;

      .bk-tag {
        padding: 0 4px;
      }
    }
  }


</style>
