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
  <BkLoading :loading="isLoading">
    <TableEditInput
      ref="inputRef"
      :model-value="localMasterInstance"
      :placeholder="$t('输入集群后自动生成')"
      readonly
      :rules="rules" />
  </BkLoading>
</template>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRemoteMachineInstancePair } from '@services/mysqlCluster';

  import TableEditInput from '@views/mysql/common/edit/Input.vue';

  interface Props {
    modelValue: string,
    scope: string,
    slave?: string
  }

  interface Exposes {
    getValue: () => Promise<{
      master: string
    }>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const inputRef = ref();
  const localMasterInstance = ref('');

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('校验不能为空'),
    },
  ];

  const {
    loading: isLoading,
    run: fetchRemoteMachineInstancePair,
  } = useRequest(getRemoteMachineInstancePair, {
    manual: true,
    onSuccess(data)  {
      const instanceData = data.instances[props.slave as string];
      localMasterInstance.value = instanceData.instance;
    },
  });

  watch(() => props.scope, () => {
    localMasterInstance.value = props.scope === 'all' ? t('全部') : props.modelValue;
  }, {
    immediate: true,
  });

  watch(() => props.slave, () => {
    if (props.slave) {
      fetchRemoteMachineInstancePair({
        instances: [props.slave],
      });
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      if (props.scope === 'all') {
        return Promise.resolve({
          master: '',
        });
      }
      return inputRef.value.getValue()
        .then(() => ({
          master: localMasterInstance.value,
        }));
    },
  });
</script>
