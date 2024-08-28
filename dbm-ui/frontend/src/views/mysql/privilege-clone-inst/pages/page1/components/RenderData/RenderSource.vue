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
    v-model="localInstanceAddress"
    :placeholder="t('请输入IP:Port或从表头批量选择')"
    :rules="rules" />
</template>
<script lang="ts">
  const instanceAddreddMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkMysqlInstances } from '@services/source/instances';

  import { useGlobalBizs } from '@stores';

  import { ipPort } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  import type { IDataRow } from './Row.vue';

  interface Exposes {
    getValue: () => Array<number>;
  }

  const instanceKey = `render_source_${random()}`;
  instanceAddreddMemo[instanceKey] = {};

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const modelValue = defineModel<IDataRow['source']>();
  const editRef = ref();

  const localInstanceAddress = ref('');

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('源实例不能为空'),
    },
    {
      validator: (value: string) => {
        const infos = value.split(':');
        if (infos.length !== 2) {
          return false;
        }

        // 判断是否为合法实例
        if (ipPort.test(`${infos[0]}:${infos[1]}`) === false) {
          return false;
        }

        return true;
      },
      message: t('请输入合法管控区域_IP_Port'),
      trigger: 'blur',
    },
    {
      validator: (value: string) =>
        checkMysqlInstances({
          bizId: currentBizId,
          instance_addresses: [value],
        }).then((data) => {
          if (data.length < 1) {
            return false;
          }
          instanceAddreddMemo[instanceKey] = { [value]: true };

          const [currentInstanceData] = data;

          modelValue.value = {
            bkCloudId: currentInstanceData.bk_cloud_id,
            clusterId: currentInstanceData.cluster_id,
            dbModuleId: currentInstanceData.db_module_id,
            dbModuleName: currentInstanceData.db_module_name,
            instanceAddress: currentInstanceData.instance_address,
            masterDomain: currentInstanceData.master_domain,
            clusterType: currentInstanceData.cluster_type,
          };
          return true;
        }),
      message: t('源实例不存在'),
    },
    {
      validator: () => {
        const currentClusterSelectMap = instanceAddreddMemo[instanceKey];
        const otherClusterMemoMap = { ...instanceAddreddMemo };
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
            return false;
          }
        }
        return true;
      },
      message: t('源实例重复'),
    },
  ];

  // 同步外部值
  watch(
    modelValue,
    () => {
      if (modelValue.value) {
        localInstanceAddress.value = modelValue.value.instanceAddress;

        instanceAddreddMemo[instanceKey] = { [localInstanceAddress.value]: true };
      } else {
        instanceAddreddMemo[instanceKey] = {};
      }
    },
    {
      immediate: true,
    },
  );

  onBeforeUnmount(() => {
    delete instanceAddreddMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      // 用户输入未完成验证
      return editRef.value.getValue().then(() => {
        if (!localInstanceAddress.value) {
          return Promise.reject();
        }

        return {
          source: localInstanceAddress.value,
        };
      });
    },
  });
</script>
