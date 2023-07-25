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
  <BkLoading :loading="isLoading">
    <BkSelect
      v-if="isSelectAll || localValue.length === 0"
      v-model="localValue"
      class="item-input"
      filterable
      :input-search="false"
      multiple
      show-select-all>
      <BkOption
        v-for="item in selectList"
        :key="item.value"
        :label="item.label"
        :value="item.value" />
    </BkSelect>
    <BkPopover
      v-else
      :content="$t('批量添加')"
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
          class="item-input"
          filterable
          :input-search="false"
          multiple
          show-select-all>
          <BkOption
            v-for="item in selectList"
            :key="item.value"
            :label="item.label"
            :value="item.value" />
        </BkSelect>
        <div
          v-if="moreNum >= 2"
          class="more-box">
          <BkTag>
            +{{ moreNum - 1 }}
          </BkTag>
        </div>
      </div>
    </BkPopover>
  </BkLoading>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { IDataRow } from './Row.vue';

  interface Props {
    selectList?: string[];
    data?: IDataRow['instances'];
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<string[]>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const localValue = ref<string[]>([]);

  const totalText = t('全部');

  const selectList = computed(() => (props.selectList
    ? props.selectList.map(item => ({ value: item, label: item })) : []));
  const isSelectAll = computed(() => localValue.value[0] === totalText);
  const moreNum = computed(() => (localValue.value.length >= 2 ? localValue.value.length : 1));

  watch(() => props.data, (str) => {
    if (str) localValue.value = str.split('\n');
  }, {
    immediate: true,
  });

  watch(localValue, (selectList) => {
    if (selectList.length === props.selectList?.length) {
      localValue.value = [totalText];
    } else if (selectList.length > 1 && selectList[0] === totalText) {
      selectList.shift();
      localValue.value = selectList;
    }
  });

  const getFinalValue = () => {
    if (isSelectAll.value) {
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
