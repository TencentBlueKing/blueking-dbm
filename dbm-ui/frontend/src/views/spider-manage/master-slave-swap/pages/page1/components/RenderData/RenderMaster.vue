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
  <div class="render-master-box">
    <TableEditInput
      ref="editRef"
      v-model="localValue"
      :placeholder="t('请输入IP')"
      :rules="rules" />
  </div>
</template>
<script lang="ts">
  const singleHostSelectMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  // TODO INTERFACE
  import { checkMysqlInstances } from '@services/source/instances';
  import type { InstanceInfos } from '@services/types/clusters';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@components/tools-table-input/index.vue';

  import { random } from '@utils';

  import type { IHostData } from './Row.vue';


  interface Props {
    modelValue?: IHostData
  }

  interface Emits {
    (e: 'change', value: IHostData): void
  }

  interface IValue {
    bk_host_id: number,
    ip: string,
    bk_cloud_id: number,
  }

  interface Exposes {
    getValue: () => Promise<IValue>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const genHostKey = (hostData: InstanceInfos) => `#${hostData.bk_cloud_id}#${hostData.ip}`;

  const instanceKey = `render_master_${random()}`;
  singleHostSelectMemo[instanceKey] = {};

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const editRef = ref();
  const localValue = ref('');

  let localProxyData = {} as InstanceInfos;

  const rules = [
    {
      validator: (value: string) => ipv4.test(_.trim(value)),
      message: t('IP格式不正确'),
    },
    {
      validator: () => checkMysqlInstances({
        bizId: currentBizId,
        instance_addresses: [localValue.value],
      }).then((data) => {
        if (data.length > 0) {
          const [currentInstanceData] = data;
          localProxyData = currentInstanceData;
          return true;
        }
        return false;
      }),
      message: t('目标主库不存在'),
    },
    {
      validator: () => {
        const otherHostSelectMemo = { ...singleHostSelectMemo };
        delete otherHostSelectMemo[instanceKey];
        const otherAllSelectHostMap = Object.values(otherHostSelectMemo).reduce((result, selectItem) => ({
          ...result,
          ...selectItem,
        }), {} as Record<string, boolean>);
        if (otherAllSelectHostMap[genHostKey(localProxyData)]) {
          return false;
        }
        emits('change', localProxyData);
        return true;
      },
      message: t('目标主库重复'),
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
      const formatHost = (item: InstanceInfos) => ({
        bk_host_id: item.bk_host_id,
        ip: item.ip,
        bk_cloud_id: item.bk_cloud_id,
      });
      return editRef.value
        .getValue()
        .then(() => ({
          master: formatHost(localProxyData),
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-master-box {
    position: relative;
  }
</style>
