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
  <div class="search-field-input">
    <div class="row">
      <SearchItem
        :model="modelValue"
        name="for_bizs"
        @change="handleChange" />
      <SearchItem
        :model="modelValue"
        name="resource_types"
        @change="handleChange" />
      <SearchItem
        :model="modelValue"
        name="hosts"
        @change="handleChange" />
    </div>
    <div class="row">
      <SearchItem
        :model="modelValue"
        name="agent_status"
        @change="handleChange" />
      <SearchItem
        :model="modelValue"
        name="device_class"
        @change="handleChange" />
      <SearchItem
        :model="modelValue"
        name="city"
        @change="handleChange" />
      <SearchItem
        :model="modelValue"
        name="mount_point"
        @change="handleChange" />
    </div>
    <KeepAlive>
      <template v-if="isShowMore">
        <div class="row">
          <SearchItem
            :model="modelValue"
            name="cpu"
            @change="handleChange" />
          <SearchItem
            :model="modelValue"
            name="mem"
            @change="handleChange" />
          <SearchItem
            :model="modelValue"
            name="disk"
            @change="handleChange" />
          <SearchItem
            :model="modelValue"
            name="disk_type"
            @change="handleChange" />
        </div>
      </template>
    </KeepAlive>
    <div class="mt-24">
      <BkButton
        size="small"
        theme="primary"
        @click="handleSubmit">
        {{ t('查询') }}
      </BkButton>
      <BkButton
        class="ml-8"
        size="small">
        {{ t('收藏条件') }}
      </BkButton>
      <BkButton
        class="ml-8"
        size="small"
        @click="handleClear">
        {{ t('清空') }}
      </BkButton>
      <BkButton
        class="ml-8"
        text
        theme="primary"
        @click="handleShowMore">
        {{ t('展开更多条件') }}
        <DbIcon
          v-if="isShowMore"
          type="up-big" />
        <DbIcon
          v-else
          type="down-big" />
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import SearchItem from './components/SearchItem.vue';

  interface Props {
    modelValue: Record<string, any>
  }
  interface Emits {
    (e: 'update:modelValue', params: Record<string, any>): void;
    (e: 'submit'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isShowMore = ref(false);

  const handleChange = (name: string, value: any) => {
    const result = { ...props.modelValue };

    if (_.isEmpty(value)) {
      delete result[name];
    } else {
      result[name] = value;
    }

    emits('update:modelValue', result);
  };

  const handleSubmit = () => {
    emits('submit');
  };

  const handleClear = () => {
    emits('update:modelValue', {});
  };

  const handleShowMore = () => {
    isShowMore.value = !isShowMore.value;
  };
</script>
<style lang="less" scoped>
  .search-field-input {
    .row {
      display: flex;
      overflow: hidden;

      & ~ .row {
        margin-top: 24px;
      }
    }
  }
</style>
