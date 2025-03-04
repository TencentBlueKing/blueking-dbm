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
    field="new_proxy.ip"
    :label="t('新Proxy主机')"
    :loading="loading"
    :min-width="300"
    required>
    <EditableInput
      v-model="modelValue.ip"
      :placeholder="t('请输入单个IP')"
      @change="handleInputChange" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getHostTopoInfos } from '@services/source/ipchooser';

  import { batchSplitRegex, ipv4 } from '@common/regex';

  /**
   * 绑定的modelValue须包含ip
   */
  const modelValue = defineModel<{
    bk_biz_id?: number;
    bk_cloud_id?: number;
    bk_host_id?: number;
    ip: string;
  }>({
    default: () => ({
      bk_biz_id: undefined,
      bk_cloud_id: undefined,
      bk_host_id: undefined,
      ip: '',
    }),
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'change',
      validator: (value: string) => ipv4.test(value),
    },
    {
      message: t('最多输入n个主机IP', { n: 1 }),
      trigger: 'blur',
      validator: (value: string) => value.split(batchSplitRegex).length <= 1,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.bk_host_id),
    },
  ];

  const { loading, run: queryHost } = useRequest(getHostTopoInfos, {
    manual: true,
    onSuccess: (data) => {
      const [currentHost] = data.hosts_topo_info;
      if (currentHost) {
        modelValue.value.bk_biz_id = window.PROJECT_CONFIG.BIZ_ID;
        modelValue.value.bk_cloud_id = currentHost.bk_cloud_id;
        modelValue.value.bk_host_id = currentHost.bk_host_id;
      }
    },
  });

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_biz_id: undefined,
      bk_cloud_id: undefined,
      bk_host_id: undefined,
      ip: value,
    };
    if (value) {
      queryHost({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        filter_conditions: {
          bk_host_innerip: [value],
          mode: 'idle_only',
        },
      });
    }
  };
</script>
