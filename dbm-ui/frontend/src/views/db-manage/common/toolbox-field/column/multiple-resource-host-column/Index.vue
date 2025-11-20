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
  <EditableColumn
    :append-rules="limit > -1 ? appendRules : []"
    :field="field"
    :label="label"
    :loading="loading"
    :min-width="minWidth"
    required
    :rules="rules">
    <EditableInput
      v-model="localValue"
      :placeholder="limit === -1 ? t('请输入主机IP,多个英文逗号分隔') : t('请输入n个主机IP', { n: limit })"
      @change="handleInputChange">
      <template #default>
        <span ref="rootRef">{{ localValue }}</span>
      </template>
      <template #append>
        <DbIcon
          v-bk-tooltips="t('从资源池选择')"
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </EditableInput>
  </EditableColumn>
  <ResourceHostSelector
    v-model:is-show="showSelector"
    v-mode="modelValue"
    :limit="limit"
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchList } from '@services/source/dbresourceResource';

  import { batchSplitRegex, ipv4 } from '@common/regex';

  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  interface IHost {
    bk_biz_id?: number;
    bk_cloud_id?: number;
    bk_host_id?: number;
    ip: string;
  }

  interface Props {
    /**
     * field 对应的必须是model的数组变量
     */
    field: string;
    label: string;
    limit?: number;
    minWidth?: number;
    params?: ComponentProps<typeof ResourceHostSelector>['params'];
  }

  const props = withDefaults(defineProps<Props>(), {
    limit: -1,
    minWidth: 300,
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
      message: () => t('xx不符合IPv4标准', [notIpv4.join(',')]),
      trigger: 'change',
      validator: (hosts: IHost[]) => {
        notIpv4 = [];
        hosts.forEach((item) => {
          if (!ipv4.test(item.ip)) {
            notIpv4.push(item.ip);
          }
        });
        return !notIpv4.length;
      },
    },
    {
      message: () => t('目标主机xx不存在', [notFound.join(',')]),
      trigger: 'blur',
      validator: (hosts: IHost[]) => {
        notFound = [];
        hosts.forEach((item) => {
          if (!item.bk_host_id) {
            notFound.push(item.ip);
          }
        });
        return !notFound.length;
      },
    },
  ];

  const appendRules = [
    {
      message: t('最多输入n个主机IP', { n: props.limit }),
      trigger: 'blur',
      validator: () => localValue.value.split(batchSplitRegex).length <= props.limit,
    },
  ];

  const { loading, run: queryHost } = useRequest(fetchList, {
    manual: true,
    onSuccess: ({ results }) => {
      if (results.length) {
        modelValue.value = results.map((item) => ({
          bk_biz_id: item.dedicated_biz || item.bk_biz_id,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          ip: item.ip,
        }));
        localValue.value = results.map((item) => item.ip).join(',');
      }
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
    if (modelValue.value.length > 0 && rootRef.value) {
      destroyInst();
      nextTick(() => {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          allowHTML: true,
          appendTo: () => document.body,
          arrow: false,
          content: popRef.value,
          hideOnClick: true,
          interactive: true,
          maxWidth: 'none',
          placement: 'top-start',
          theme: 'light',
          trigger: 'mouseenter click',
          zIndex: 999999,
        });
      });
    }
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    if (!value) {
      return;
    }
    modelValue.value = value.split(',').map((ip) => ({
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: ip,
    }));
  };

  const handleSelectorChange = (hostList: IValue[]) => {
    modelValue.value = hostList.map((item) => ({
      bk_biz_id: item.dedicated_biz || item.bk_biz_id,
      bk_cloud_id: item.bk_cloud_id,
      bk_host_id: item.bk_host_id,
      ip: item.ip,
    }));
  };

  onBeforeUnmount(() => {
    destroyInst();
  });

  watch(
    modelValue,
    () => {
      if (modelValue.value?.[0]?.ip && !modelValue.value?.[0]?.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          hosts: localValue.value,
          limit: props.limit,
          offset: 0,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .select-icon {
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
