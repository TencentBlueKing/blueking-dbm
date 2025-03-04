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
    field="new_master_slave_host"
    :label="t('新主从主机')"
    :loading="loading"
    :min-width="200"
    required
    :rules="rules">
    <EditableInput
      v-model="localValue"
      :placeholder="t('请输入n个主机IP', { n: limit })"
      @change="handleInputChange" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getHostTopoInfos } from '@services/source/ipchooser';

  import { batchSplitRegex, ipv4 } from '@common/regex';

  interface IHost {
    bk_biz_id?: number;
    bk_cloud_id?: number;
    bk_host_id?: number;
    ip: string;
  }

  /**
   * 绑定modelValue为数组 项须包含ip
   */
  const modelValue = defineModel<IHost[]>({
    default: () => [],
  });

  const { t } = useI18n();

  const localValue = ref('');
  let notIpv4: string[] = [];
  let notFound: string[] = [];
  const limit = 2;

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
      message: t('最多输入n个主机IP', { n: limit }),
      trigger: 'blur',
      validator: () => localValue.value.split(batchSplitRegex).length <= limit,
    },
  ];

  const { loading, run: queryHost } = useRequest(getHostTopoInfos, {
    manual: true,
    onSuccess: ({ hosts_topo_info: results }) => {
      if (results.length) {
        modelValue.value = results.map((item) => ({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          ip: item.ip,
        }));
        localValue.value = results.map((item) => item.ip).join(',');
      }
    },
  });

  const handleInputChange = (value: string) => {
    modelValue.value = [];
    if (value) {
      queryHost({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        filter_conditions: {
          bk_host_innerip: value.split(batchSplitRegex),
          mode: 'idle_only',
        },
      });
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
</style>
