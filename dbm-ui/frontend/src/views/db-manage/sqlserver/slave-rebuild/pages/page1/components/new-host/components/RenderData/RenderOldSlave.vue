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
    v-model="localValue"
    :placeholder="t('请输入IP')"
    :rules="rules"
    @input="handleInput" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { checkInstance } from '@services/source/dbbase';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@views/db-manage/tendb-cluster/common/edit/Input.vue';

  import type { IDataRow } from './Row.vue';

  interface Exposes {
    getValue: () => Promise<{
      old_slave_host: {
        bk_biz_id: number;
        bk_cloud_id: number;
        ip: string;
        bk_host_id: number;
        port: number;
      };
    }>;
  }

  const { t } = useI18n();

  const modelValue = defineModel<IDataRow['oldSlave']>();

  const editRef = ref<InstanceType<typeof TableEditInput>>();
  const localValue = ref('');

  const rules = [
    {
      validator: (value: string) => Boolean(_.trim(value)),
      message: t('待重建从库主机不能为空'),
    },
    {
      validator: (value: string) => ipv4.test(value),
      message: t('待重建从库主机格式不正确'),
    },
    {
      validator: (value: string) =>
        checkInstance({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          instance_addresses: [value],
        }).then((data) => {
          if (data.length < 1) {
            return false;
          }
          const [instanceData] = data;
          modelValue.value = {
            bkCloudId: instanceData.bk_cloud_id,
            bkCloudName: instanceData.bk_cloud_name,
            bkHostId: instanceData.bk_host_id,
            ip: instanceData.ip,
            port: instanceData.port,
            clusterId: instanceData.cluster_id,
            dbModuleId: instanceData.db_module_id,
          };
          return true;
        }),
      message: t('待重建从库主机不存在'),
    },
  ];

  watch(
    () => modelValue.value,
    () => {
      if (!modelValue.value) {
        return;
      }
      localValue.value = modelValue.value.ip;
    },
    {
      immediate: true,
    },
  );

  const handleInput = () => {
    modelValue.value = undefined;
  };

  defineExpose<Exposes>({
    getValue() {
      return (editRef.value as InstanceType<typeof TableEditInput>).getValue().then(() => {
        if (!modelValue.value) {
          return Promise.reject();
        }
        return {
          old_slave_host: {
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            bk_cloud_id: modelValue.value.bkCloudId,
            ip: modelValue.value.ip,
            bk_host_id: modelValue.value.bkHostId,
            port: modelValue.value.port,
          },
        };
      });
    },
  });
</script>
