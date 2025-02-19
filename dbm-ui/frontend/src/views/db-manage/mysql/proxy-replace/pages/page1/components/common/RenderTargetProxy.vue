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
  <TableEditInput
    ref="inputRef"
    v-model="modelValue.ip"
    :disabled="!originProxy.ip"
    :placeholder="t('请输入单个IP')"
    :rules="rules" />
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getHostTopoInfos } from '@services/source/ipchooser';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  interface ProxyItem {
    bk_biz_id: number;
    bk_cloud_id: number | null;
    bk_host_id: number;
    ip: string;
    port?: number;
  }

  interface Props {
    originProxy: ProxyItem;
  }

  interface Exposes {
    getValue: () => {
      target_proxy: ProxyItem;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<ProxyItem>('modelValue', {
    default: () => ({
      bk_biz_id: 0,
      bk_cloud_id: null,
      bk_host_id: 0,
      ip: '',
      port: 0,
    }),
  });

  const { locale, t } = useI18n();
  const { currentBizId, currentBizInfo } = useGlobalBizs();

  const inputRef = ref();

  const isCN = computed(() => locale.value === 'zh-cn');

  let hostDataMemo = {} as ServiceReturnType<typeof getHostTopoInfos>['hosts_topo_info'][number];
  let errorMessage = t('IP不存在');

  const rules = [
    {
      message: t('IP格式不正确'),
      validator: (value: string) => ipv4.test(value),
    },
    {
      message: () => errorMessage,
      validator: (value: string) =>
        getHostTopoInfos({
          bk_biz_id: currentBizId,
          filter_conditions: {
            bk_host_innerip: [value],
            mode: 'idle_only',
          },
        }).then((data) => {
          if (data.hosts_topo_info.length < 1) {
            const bizName = isCN.value ? currentBizInfo?.name || '--' : currentBizInfo?.english_name || '--';
            errorMessage = t('IP不在x业务空闲机模块', { name: bizName });
            return false;
          }
          const hostData = data.hosts_topo_info.find((item) => item.bk_cloud_id === props.originProxy.bk_cloud_id);
          if (!hostData) {
            errorMessage = t('新主机xx跟目标proxy主机xx须在同一个管控区域', {
              ip: value,
              target: props.originProxy.ip,
            });
            return false;
          }
          hostDataMemo = hostData;
          return true;
        }),
    },
  ];

  defineExpose<Exposes>({
    getValue() {
      return inputRef.value
        .getValue()
        .then(() => ({
          target_proxy: {
            bk_biz_id: currentBizId,
            bk_cloud_id: hostDataMemo.bk_cloud_id,
            bk_host_id: hostDataMemo.bk_host_id,
            ip: hostDataMemo.ip,
          },
        }))
        .catch(() =>
          Promise.reject({
            target_proxy: {
              bk_biz_id: currentBizId,
              bk_cloud_id: hostDataMemo.bk_cloud_id,
              bk_host_id: hostDataMemo.bk_host_id,
              ip: hostDataMemo.ip,
            },
          }),
        );
    },
  });
</script>
