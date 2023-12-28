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
  <div class="render-proxy-box">
    <TableEditInput
      ref="inputRef"
      v-model="localValue"
      :disabled="disabled"
      :placeholder="$t('请输入单个IP')"
      :rules="rules"
      textarea />
  </div>
</template>
<script setup lang="ts">
  import {
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getHostTopoInfos } from '@services/source/ipchooser';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@views/mysql/common/edit/Input.vue';

  import type {  IDataRow } from './Row.vue';

  type HostTopoInfo = ServiceReturnType<typeof getHostTopoInfos>['hosts_topo_info'][number]

  interface Props {
    modelValue: IDataRow['proxyIp'],
    cloudId: null | number
    disabled: boolean
    domain?: string
  }

  interface Exposes {
    getValue: () => Promise<Array<string>>
  }

  const props = defineProps<Props>();

  const {
    t,
    locale,
  } = useI18n();
  const {
    currentBizId,
    currentBizInfo,
  } = useGlobalBizs();

  const inputRef = ref();
  const localValue = ref('');

  const isCN = computed(() => locale.value === 'zh-cn');

  let localHostData = {} as HostTopoInfo;
  let errorMessage = t('IP不存在');

  const rules = [
    {
      validator: (value: string) => ipv4.test(value),
      message: t('IP格式不正确'),
    },
    {
      validator: (value: string) => getHostTopoInfos({
        filter_conditions: {
          bk_host_innerip: [value],
          mode: 'idle_only',
        },
        bk_biz_id: currentBizId,
      }).then((data) => {
        if (data.hosts_topo_info.length < 1) {
          const bizName = isCN.value ? currentBizInfo?.name || '--' : currentBizInfo?.english_name || '--';
          errorMessage = t('IP不在x业务空闲机模块', { name: bizName });
          return false;
        }
        const hostData = data.hosts_topo_info.find(item => item.bk_cloud_id === props.cloudId);
        if (!hostData) {
          errorMessage = t('新主机xx跟目标集群xx须在同一个管控区域', {
            ip: value,
            cluster: props.domain,
          });
          return false;
        }
        localHostData = hostData;
        return true;
      }),
      message: () => errorMessage,
    },
  ];

  watch(() => props.modelValue, () => {
    if (props.modelValue) {
      localValue.value = props.modelValue.ip;
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      const formatHost = (item: HostTopoInfo) => ({
        bk_biz_id: currentBizId,
        bk_host_id: item.bk_host_id,
        ip: item.ip,
        bk_cloud_id: item.bk_cloud_id,
      });
      return inputRef.value
        .getValue()
        .then(() => Promise.resolve({
          new_proxy: formatHost(localHostData),
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-proxy-box {
    position: relative;
  }
</style>
