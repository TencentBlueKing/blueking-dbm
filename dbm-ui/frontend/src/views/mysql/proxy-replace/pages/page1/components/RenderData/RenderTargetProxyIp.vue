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
  <div class="render-target-proxy-ip">
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
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getHostTopoInfos } from '@services/source/ipchooser';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@views/mysql/common/edit/Input.vue';

  import type { IHostData } from './Row.vue';

  interface Props {
    cloudId: number | null,
    modelValue?: IHostData
    disabled: boolean
    targetIp?: string
  }

  interface Exposes {
    getValue: () => Promise<Array<string>>
  }

  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const inputRef = ref();
  const localValue = ref('');

  let hostDataMemo  = {} as ServiceReturnType<typeof getHostTopoInfos>['hosts_topo_info'][number];
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
          errorMessage = t('IP不在空闲机中');
          return false;
        }
        const hostData = data.hosts_topo_info.find(item => item.bk_cloud_id === props.cloudId);
        if (!hostData) {
          errorMessage = t('新主机xx跟目标proxy主机xx须在同一个管控区域', {
            ip: value,
            target: props.targetIp,
          });
          return false;
        }
        hostDataMemo = hostData;
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
      return inputRef.value
        .getValue()
        .then(() => ({
          target_proxy: {
            bk_biz_id: currentBizId,
            bk_host_id: hostDataMemo.bk_host_id,
            bk_cloud_id: hostDataMemo.bk_cloud_id,
            ip: hostDataMemo.ip,
          },
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-target-proxy-ip {
    position: relative;

    &.is-repeat {
      .input-error {
        display: none;
      }
    }

    .repeat-flag {
      position: absolute;
      top: 0;
      right: 0;
      display: flex;
      height: 20px;
      padding: 0 5px;
      font-size: 12px;
      line-height: 20px;
      color: #fff;
      background-color: #ea3636;
      border-radius: 2px;
      align-self: center;
      transform: scale(0.8);
      transform-origin: right top;
    }
  }
</style>
