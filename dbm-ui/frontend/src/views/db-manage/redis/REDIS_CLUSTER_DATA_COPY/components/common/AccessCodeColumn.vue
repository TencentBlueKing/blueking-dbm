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
  <EditableColumn
    :append-rules="rules"
    :field="field"
    :label="t('访问密码')"
    required
    :width="200">
    <EditableInput
      v-model="modelValue"
      :placeholder="t('请输入连接密码')"
      type="password"
      @paste="handlePaste" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { testRedisConnection } from '@services/source/redisDts';

  import { encodeMult } from '@utils';

  interface Props {
    dataCopyType: string;
    field: string;
    params: {
      dstCluster: string;
      srcCluster: string;
    };
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('密码不能为空'),
      trigger: 'change',
      validator: (value: string) => Boolean(value),
    },
    {
      message: t('请先选择源集群'),
      trigger: 'change',
      validator: () => Boolean(props.params.srcCluster),
    },
    {
      message: t('请先输入目标集群'),
      trigger: 'change',
      validator: () => Boolean(props.params.dstCluster),
    },
    {
      message: t('密码不匹配'),
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        if (props.dataCopyType === 'copy_to_other_system') {
          return testRedisConnection({
            data_copy_type: 'copy_to_other_system',
            infos: [
              {
                dst_cluster: props.params.dstCluster,
                dst_cluster_password: value,
                src_cluster: props.params.srcCluster,
                src_cluster_password: '',
              },
            ],
          }).then((result) => result);
        }
        return testRedisConnection({
          data_copy_type: 'user_built_to_dbm',
          infos: [
            {
              dst_cluster: props.params.dstCluster,
              dst_cluster_password: '',
              src_cluster: props.params.srcCluster,
              src_cluster_password: value,
            },
          ],
        }).then((result) => result);
      },
    },
  ];

  const handlePaste = (value: string, event: ClipboardEvent) => {
    event.preventDefault();
    let paste = (event.clipboardData || window.clipboardData).getData('text');
    paste = encodeMult(paste);
    modelValue.value = paste;
    window.changeConfirm = true;
  };
</script>
