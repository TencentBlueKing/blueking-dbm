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
  <Column
    :append-rules="rules"
    :field="field"
    :label="label"
    :min-width="200"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :title="label"
        type="input"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <Input v-model="modelValue" />
  </Column>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { checkClusterDatabase } from '@services/source/remoteService';

  import { Column, Input } from '@components/editable-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    field: string;
    label: string;
    clusterId: number;
    checkExist?: boolean;
    checkNotExist?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    checkExist: false,
    checkNotExist: false,
  });

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const showBatchEdit = ref(false);

  const rules = [
    {
      validator: (value: string) => !/^stage_truncate/.test(value),
      message: t('不可以stage_truncate开头'),
      trigger: 'change',
    },
    {
      validator: (value: string) => !/rollback$/.test(value),
      message: t('不可以rollback结尾'),
      trigger: 'change',
    },
    {
      validator: (value: string) => /^[a-zA-z][a-zA-Z0-9_-]{1,39}$/.test(value),
      message: t('由字母_数字_下划线_减号_字符组成以字母开头'),
      trigger: 'change',
    },
    {
      validator: async (value: string) => {
        if (!_.some(value, (item) => !/[*%]/.test(item))) {
          return true;
        }
        const data = await checkClusterDatabase({
          infos: [
            {
              cluster_id: props.clusterId,
              db_names: [value],
            },
          ],
        });
        const isExist = Boolean(data[0]?.check_info[value]);
        if (isExist && props.checkExist) {
          return t('DB已存在');
        }
        if (!isExist && props.checkNotExist) {
          return t('DB不存在');
        }
        return true;
      },
      message: '',
      trigger: 'blur',
    },
  ];

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string) => {
    modelValue.value = value;
  };
</script>
<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
