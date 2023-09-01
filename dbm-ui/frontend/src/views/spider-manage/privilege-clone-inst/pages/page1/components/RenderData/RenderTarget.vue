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
    multi-input
    :placeholder="$t('请输入IP_Port')"
    :rules="rules" />
</template>
<script lang="ts">
  const instanceAddreddMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { checkInstances } from '@services/clusters';
  import type SpiderModel from '@services/model/spider/spider';
  import type { InstanceInfos } from '@services/types/clusters';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import { random } from '@utils';

  import type { IProxyData } from './Row.vue';

  interface Props {
    modelValue?: IProxyData,
    clusterData?:SpiderModel
  }

  interface Exposes {
    getValue: () => Array<number>
  }

  const props = defineProps<Props>();

  const instanceKey = `render_target_${random()}`;
  instanceAddreddMemo[instanceKey] = {};

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const editRef = ref();

  const localInstanceAddress = ref('');
  let localInstanceData: InstanceInfos;

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('新实例不能为空'),
    },
    {
      validator: () => checkInstances(currentBizId, {
        instance_addresses: [localInstanceAddress.value],
      }).then((data) => {
        if (data.length < 1) {
          return false;
        }
        [localInstanceData] = data;
        instanceAddreddMemo[instanceKey][localInstanceAddress.value] = true;

        return true;
      }),
      message: t('新实例不存在'),
    },
    {
      validator: () => !!props.clusterData && localInstanceData.bk_cloud_id === props.clusterData.bk_cloud_id,
      message: t('新实例和源实例的云区域不一致'),
    },
    {
      validator: () => {
        const currentClusterSelectMap = instanceAddreddMemo[instanceKey];
        const otherClusterMemoMap = { ...instanceAddreddMemo };
        delete otherClusterMemoMap[instanceKey];

        const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce((result, item) => ({
          ...result,
          ...item,
        }), {} as Record<string, boolean>);

        const currentSelectClusterIdList = Object.keys(currentClusterSelectMap);
        for (let i = 0; i < currentSelectClusterIdList.length; i++) {
          if (otherClusterIdMap[currentSelectClusterIdList[i]]) {
            return false;
          }
        }
        return true;
      },
      message: t('新实例重复'),
    },
  ];

  // 同步外部值
  watch(() => props.modelValue, () => {
    if (props.modelValue) {
      localInstanceAddress.value = props.modelValue.instance_address;

      instanceAddreddMemo[instanceKey][localInstanceAddress.value] = true;
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      // 用户输入未完成验证
      return editRef.value
        .getValue()
        .then(() => ({
          target: localInstanceAddress.value,
        }));
    },
  });
</script>
