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
  <Column
    :append-rules="editable ? rules : []"
    :field="field"
    :label="label"
    :loading="loading"
    :min-width="300"
    required>
    <Input
      v-if="editable"
      v-model="localValue"
      :placeholder="t('请选择主机')"
      @change="handleInputChange">
      <template #default>
        <span ref="rootRef">{{ localValue }}</span>
      </template>
      <template #append>
        <DbIcon
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </Input>
    <Block
      v-else
      v-model="localValue"
      :placeholder="t('请选择主机')">
      <template #default>
        <span ref="rootRef">{{ localValue }}</span>
      </template>
      <template #append>
        <DbIcon
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </Block>
  </Column>
  <ResourceHostSelector
    v-model:is-show="showSelector"
    v-mode="modelValue"
    :params="params"
    @change="handleSelectorChange" />
  <div style="display: none">
    <div ref="popRef">
      <p
        v-for="item in modelValue"
        :key="item.ip">
        {{ item.ip }}
      </p>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import type { Instance, SingleTarget } from 'tippy.js';
  import tippy from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchListDbaHost } from '@services/source/dbresourceResource';

  import { ipv4 } from '@common/regex';

  import { Block, Column, Input } from '@components/editable-table/Index.vue';
  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  interface Props {
    /**
     * field 对应的必须是model的数组变量
     */
    field: string;
    label: string;
    editable?: boolean;
    params?: {
      for_biz?: number;
      bk_cloud_ids?: string;
      resource_type?: string;
      os_type?: string;
    };
  }

  interface IHost {
    bk_biz_id?: number;
    bk_cloud_id?: number;
    bk_host_id?: number;
    ip: string;
  }

  withDefaults(defineProps<Props>(), {
    editable: false,
    params: () => ({}),
  });

  /**
   * 绑定modelValue为数组 项须包含ip
   */
  const modelValue = defineModel<IHost[]>({
    default: () => [],
  });

  const { t } = useI18n();

  const rootRef = ref();
  const popRef = ref();
  const showSelector = ref(false);
  const localValue = ref('');
  let notIpv4: string[] = [];
  let notFound: string[] = [];
  let tippyIns: Instance;

  const rules = [
    {
      validator: (hosts: IHost[]) => {
        notIpv4 = [];
        hosts.forEach((item) => {
          if (!ipv4.test(item.ip)) {
            notIpv4.push(item.ip);
          }
        });
        return !notIpv4.length;
      },
      message: () => t('xx不符合IPv4标准', [notIpv4.join(',')]),
      trigger: 'change',
    },
    {
      validator: (hosts: IHost[]) => {
        notFound = [];
        hosts.forEach((item) => {
          if (!item.bk_host_id) {
            notFound.push(item.ip);
          }
        });
        return !notFound.length;
      },
      message: () => t('目标主机xx不存在', [notFound.join(',')]),
      trigger: 'blur',
    },
  ];

  const { run: queryHost, loading } = useRequest(fetchListDbaHost, {
    manual: true,
    onSuccess: (data) => {
      console.log(data, 'data');
      // modelValue.value = data.map(item => ({
      //   bk_biz_id: item.dedicated_biz || item.bk_biz_id,
      // bk_cloud_id: item.bk_cloud_id,
      // bk_host_id: item.bk_host_id,
      // ip: item.ip,
      // }))
      // localValue.value = data.map(item => item.ip).join(',')
    },
  });

  const destroyInst = () => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  };

  watch(modelValue, () => {
    localValue.value = modelValue.value.map((item) => item.ip).join(',');
    if (modelValue.value.length > 0) {
      destroyInst();
      nextTick(() => {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          content: popRef.value,
          placement: 'top-start',
          appendTo: () => document.body,
          theme: 'light',
          maxWidth: 'none',
          trigger: 'mouseenter click',
          interactive: true,
          arrow: false,
          allowHTML: true,
          zIndex: 999999,
          hideOnClick: true,
        });
      });
    }
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    queryHost({
      search_content: value,
      limit: -1,
      offset: 0,
    });
  };

  const handleSelectorChange = (hostList: IValue[]) => {
    modelValue.value = hostList;
  };

  onBeforeUnmount(() => {
    destroyInst();
  });
</script>

<style lang="less" scoped>
  :deep(.select-icon) {
    display: flex;
    margin-right: 5px;
    font-size: 18px;
    color: #979ba5;
    align-items: center;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }
  }
</style>
