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
  <div class="render-source-box">
    <BkLoading :loading="isLoading">
      <TableEditInput
        ref="editRef"
        v-model="localValue"
        :placeholder="t('请输入IP:Port')"
        :rules="rules" />
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { checkMysqlInstances } from '@services/source/instances';

  import { useGlobalBizs } from '@stores';

  import { ipPort } from '@common/regex';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import type { IDataRow } from './Row.vue';

  interface Exposes {
    getValue: (field: string) => Promise<string>
  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const modelValue = defineModel<IDataRow['slave']>();

  const editRef = ref();
  const localValue = ref('');
  const isLoading = ref(false);

  const rules = [
    {
      validator: (value: string) => Boolean(_.trim(value)),
      message: t('目标从库实例不能为空'),
    },
    {
      validator: (value: string) => ipPort.test(value),
      message: t('目标从库实例格式不正确'),
    },
    {
      validator: (value: string) => checkMysqlInstances({
        bizId: currentBizId,
        instance_addresses: [value],
      }).then((data) => {
        if (data.length < 1) {
          return false;
        }
        const [instanceData] = data;
        modelValue.value = {
          bkCloudId: instanceData.bk_cloud_id,
          bkHostId: instanceData.bk_host_id,
          ip: instanceData.ip,
          port: instanceData.port,
          instanceAddress: instanceData.instance_address,
          clusterId: instanceData.cluster_id,
        };
        return true;
      }),
      message: t('目标从库实例不存在'),
    },
  ];

  watch(() => modelValue.value, () => {
    if (!modelValue.value) {
      return;
    }
    localValue.value = `${modelValue.value.ip}:${modelValue.value.port}`;
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => {
          if (!modelValue.value) {
            return Promise.reject();
          }
          return ({
            slave: {
              bk_biz_id: currentBizId,
              bk_cloud_id: modelValue.value.bkCloudId,
              ip: modelValue.value.ip,
              bk_host_id: modelValue.value.bkHostId,
              port: modelValue.value.port,
              instance_address: modelValue.value.instanceAddress,
            },
          });
        });
    },
  });
</script>
<style lang="less" scoped>
  .render-source-box {
    position: relative;
  }
</style>
