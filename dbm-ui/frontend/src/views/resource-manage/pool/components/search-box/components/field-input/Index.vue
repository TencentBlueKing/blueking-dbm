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
      <ComFactory
        :ref="(el: any) => initInputRefCallback(el, 'for_bizs')"
        :model="localValueMemo"
        name="for_bizs"
        @change="handleChange" />
      <ComFactory
        :ref="(el: any) => initInputRefCallback(el, 'resource_types')"
        :model="localValueMemo"
        name="resource_types"
        @change="handleChange" />
      <ComFactory
        :ref="(el: any) => initInputRefCallback(el, 'bk_cloud_ids')"
        :model="localValueMemo"
        name="bk_cloud_ids"
        @change="handleChange" />
      <ComFactory
        :ref="(el: any) => initInputRefCallback(el, 'agent_status')"
        :model="localValueMemo"
        name="agent_status"
        @change="handleChange" />
    </div>
    <div class="row">
      <ComFactory
        :ref="(el: any) => initInputRefCallback(el, 'spec_id')"
        :model="localValueMemo"
        name="spec_id"
        @change="handleChange" />
      <ComFactory
        :ref="(el: any) => initInputRefCallback(el, 'device_class')"
        :model="localValueMemo"
        name="device_class"
        @change="handleChange" />
      <ComFactory
        :ref="(el: any) => initInputRefCallback(el, 'city')"
        :model="localValueMemo"
        name="city"
        @change="handleChange" />
    </div>
    <KeepAlive>
      <template v-if="isShowMore">
        <div class="row">
          <ComFactory
            :ref="(el: any) => initInputRefCallback(el, 'mount_point')"
            :model="localValueMemo"
            name="mount_point"
            @change="handleChange" />
          <ComFactory
            :ref="(el: any) => initInputRefCallback(el, 'cpu')"
            :model="localValueMemo"
            name="cpu"
            @change="handleChange" />
          <ComFactory
            :ref="(el: any) => initInputRefCallback(el, 'mem')"
            :model="localValueMemo"
            name="mem"
            @change="handleChange" />
          <ComFactory
            :ref="(el: any) => initInputRefCallback(el, 'disk')"
            :model="localValueMemo"
            name="disk"
            @change="handleChange" />
        </div>
        <div class="row">
          <ComFactory
            :ref="(el: any) => initInputRefCallback(el, 'disk_type')"
            :model="localValueMemo"
            name="disk_type"
            @change="handleChange" />
          <ComFactory
            :ref="(el: any) => initInputRefCallback(el, 'subzones')"
            :model="localValueMemo"
            name="subzones"
            @change="handleChange" />
          <ComFactory
            :ref="(el: any) => initInputRefCallback(el, 'os_type')"
            :model="localValueMemo"
            name="os_type"
            @change="handleChange" />
          <div style="flex: 1" />
        </div>
      </template>
    </KeepAlive>
    <div class="row">
      <ComFactory
        :ref="(el: any) => initInputRefCallback(el, 'hosts')"
        :model="localValueMemo"
        name="hosts"
        @change="handleChange" />
      <div style="flex: 2; display: flex; align-items: flex-end;">
        <div class="action-box">
          <BkButton
            class="ml-8 w-88"
            @click="handleClear">
            {{ t('清空') }}
          </BkButton>
          <CollectSearchParams
            class="ml-8 w-88"
            :search-params="modelValue"
            style="flex: 1"
            @change="handleCollectParamsChange" />
        </div>
      </div>
    </div>
    <div class="toggle-input-btn">
      <BkButton
        class="ml-8 w-88"
        text
        theme="primary"
        @click="handleShowMore">
        {{ t('更多条件') }}
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
  import {
    onActivated,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import ComFactory from '../com-factory/Index.vue';

  import CollectSearchParams from './components/CollectSearchParams.vue';

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
  const inputRef = shallowRef<Record<string, typeof ComFactory>>({});
  const localValueMemo = shallowRef<Record<string, any>>({});

  const initInputRefCallback =  (com: typeof ComFactory, name: string) => {
    inputRef.value[name] = com;
  };

  // 同步外部值的改动
  watch(() => props.modelValue, () => {
    localValueMemo.value = { ...props.modelValue };
  }, {
    immediate: true,
  });

  // 提交搜索，更新外部值
  const handleSubmit = _.debounce(() => {
    Promise.all(Object.values(inputRef.value).map(inputItem => inputItem.getValue()))
      .then(() => {
        emits('update:modelValue', {
          ...localValueMemo.value,
        });
        emits('submit');
      });
  }, 200, {
    trailing: true,
  });

  // 搜索项值改变，临时缓存
  const handleChange = (name: string, value: any) => {
    const result = { ...localValueMemo.value };
    result[name] = value;

    localValueMemo.value = result;
    // 搜索项改变立即搜索
    handleSubmit();
  };

  // 清空搜索项
  const handleClear = () => {
    localValueMemo.value = {};
    emits('update:modelValue', {});
    Object.values(inputRef.value).map(inputItem => inputItem.reset());
    handleSubmit();
  };

  // 展开更多搜索项
  const handleShowMore = () => {
    isShowMore.value = !isShowMore.value;
  };

  const handleCollectParamsChange = (value: Props['modelValue']) => {
    emits('update:modelValue', value);
    emits('submit');
  };

  onActivated(() => {
    // 组件激活时需要校验一次值
    Promise.all(Object.values(inputRef.value).map(inputItem => inputItem.getValue()));
  });
</script>
<style lang="less" scoped>
  .search-field-input {
    position: relative;
    padding-right: 76px;

    .row {
      display: flex;

      & ~ .row {
        margin-top: 24px;
      }
    }

    .action-box {
      display: flex;
      width: 100%;
      padding: 0 20px;
    }

    .toggle-input-btn {
      position: absolute;
      top: 117px;
      right: 0;
    }
  }
</style>
