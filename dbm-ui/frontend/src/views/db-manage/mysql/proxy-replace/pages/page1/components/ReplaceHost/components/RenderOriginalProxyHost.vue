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
    ref="editRef"
    v-model="modelValue"
    :placeholder="t('请输入或从表头批量选择')"
    :rules="rules" />
</template>
<script lang="ts">
  const proxyHostMemo: { [key: string]: Record<string, boolean> } = {};

  interface Emits {
    (e: 'inputFinish', relatedInstances: IDataRow['relatedInstances']): void;
  }

  interface Exposes {
    getValue: () => {
      origin_proxy: IDataRow['originProxy'];
    };
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkMysqlInstances } from '@services/source/instances';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  import type { IDataRow } from './RenderData/Row.vue';

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>('modelValue', {
    default: '',
  });

  const instanceKey = `render_original_proxy_${random()}`;
  proxyHostMemo[instanceKey] = {};
  let proxyHostData = {} as IDataRow['originProxy'];

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const editRef = ref();

  const rules = [
    {
      validator: (value: string) => {
        if (value) {
          return true;
        }
        return false;
      },
      message: t('目标Proxy主机不能为空'),
    },
    {
      validator: (value: string): Promise<boolean> =>
        checkMysqlInstances({
          bizId: currentBizId,
          instance_addresses: [value],
        }).then((data) => {
          if (data.length < 1) {
            emits('inputFinish', []);
            return false;
          }
          const [currentData] = data;
          proxyHostMemo[instanceKey][currentData.ip] = true;
          proxyHostData = {
            ip: currentData.ip,
            bk_cloud_id: currentData.bk_cloud_id,
            bk_host_id: currentData.bk_host_id,
            bk_biz_id: currentBizId,
            port: currentData.port,
          };
          const relatedInstances = data.map((item) => ({
            cluster_id: item.cluster_id,
            instance: item.instance_address,
          }));
          emits('inputFinish', relatedInstances);
          return true;
        }),
      message: t('目标Proxy主机不存在'),
    },
    {
      validator: () => {
        const currentClusterSelectMap = proxyHostMemo[instanceKey];
        const otherClusterMemoMap = { ...proxyHostMemo };
        delete otherClusterMemoMap[instanceKey];

        const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce(
          (result, item) => ({
            ...result,
            ...item,
          }),
          {} as Record<string, boolean>,
        );

        const currentSelectClusterIdList = Object.keys(currentClusterSelectMap);
        for (let i = 0; i < currentSelectClusterIdList.length; i++) {
          if (otherClusterIdMap[currentSelectClusterIdList[i]]) {
            emits('inputFinish', []);
            return false;
          }
        }
        return true;
      },
      message: t('目标Proxy主机重复'),
    },
  ];

  watch(
    () => modelValue.value,
    () => {
      if (modelValue.value) {
        setTimeout(() => {
          editRef.value!.getValue();
        });
      }
    },
    {
      immediate: true,
    },
  );

  onBeforeUnmount(() => {
    delete proxyHostMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value.getValue().then(() => ({
        origin_proxy: proxyHostData,
      }));
    },
  });
</script>
