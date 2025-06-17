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
    :append-rules="rules"
    field="new_readonly_host"
    :label="t('新只读主机')"
    :loading="loading"
    :min-width="200">
    <template #headAppend> <span class="required-icon" /> </template>
    <EditableBlock
      v-if="cluster.id && !cluster.readonly_host.length"
      :placeholder="t('无只读主机')" />
    <EditableInput
      v-else
      v-model="inputIps"
      :placeholder="t('请输入n个主机IP', { n: hostLimit })"
      @change="handleInputChange">
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
    v-model="selected"
    v-model:is-show="showSelector"
    :limit="hostLimit"
    :params="{
      for_bizs: [currentBizId, 0],
      resource_types: [DBTypes.MYSQL, 'PUBLIC'],
    }"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchList } from '@services/source/dbresourceResource';

  import { DBTypes } from '@common/const';
  import { batchSplitRegex, ipv4 } from '@common/regex';

  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  interface Props {
    cluster: {
      id: number;
      readonly_host: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
  }

  const props = defineProps<Props>();

  /**
   * 绑定的modelValue须包含ip
   */
  const modelValue = defineModel<
    {
      bk_biz_id?: number;
      bk_cloud_id?: number;
      bk_host_id?: number;
      ip: string;
    }[]
  >({
    default: () => [
      {
        bk_biz_id: undefined,
        bk_cloud_id: undefined,
        bk_host_id: undefined,
        ip: '',
      },
    ],
  });

  const { t } = useI18n();

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const inputIps = ref('');
  const showSelector = ref(false);

  const hostLimit = computed(() => props.cluster.readonly_host.length);
  const selected = computed(() =>
    modelValue.value.filter((item) => !!item.ip).length ? (modelValue.value as IValue[]) : ([] as IValue[]),
  );

  const rules = [
    {
      message: t('新只读主机不能为空'),
      trigger: 'change',
      validator: (value: Props['cluster']['readonly_host']) => value.every((item) => !!item.ip),
    },
    {
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'change',
      validator: (value: Props['cluster']['readonly_host']) => value.every((item) => ipv4.test(item.ip)),
    },
    {
      message: t('新只读主机数与旧只读主机数不一致'),
      trigger: 'blur',
      validator: (value: Props['cluster']['readonly_host']) => value.length === hostLimit.value,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: () => modelValue.value.every((item) => Boolean(item.bk_host_id)),
    },
  ];

  const { loading, run: queryHost } = useRequest(fetchList, {
    manual: true,
    onSuccess: (data) => {
      modelValue.value = data.results.map((item) => ({
        bk_biz_id: item.dedicated_biz,
        bk_cloud_id: item.bk_cloud_id,
        bk_host_id: item.bk_host_id,
        ip: item.ip,
      }));
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = [
      {
        bk_biz_id: undefined,
        bk_cloud_id: undefined,
        bk_host_id: undefined,
        ip: value,
      },
    ];
    if (value) {
      queryHost({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        hosts: value.split(batchSplitRegex).join(','),
        limit: hostLimit.value,
        offset: 0,
      });
    }
  };

  const handleSelectorChange = (hostList: IValue[]) => {
    if (hostList.length) {
      inputIps.value = hostList.map((item) => item.ip).join(',');
      modelValue.value = hostList.map((item) => ({
        bk_biz_id: item.dedicated_biz || item.bk_biz_id,
        bk_cloud_id: item.bk_cloud_id,
        bk_host_id: item.bk_host_id,
        ip: item.ip,
      }));
    }
  };
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

  .required-icon::after {
    line-height: 20px;
    color: #ea3636;
    content: '*';
  }
</style>
