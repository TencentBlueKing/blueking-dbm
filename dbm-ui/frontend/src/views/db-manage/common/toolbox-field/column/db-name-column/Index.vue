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

  interface Emits {
    (e: 'batch-edit', value: string, field: string): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    checkExist: false,
    checkNotExist: false,
  });

  const emits = defineEmits<Emits>();

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
      validator: (value: string) => {
        if (!props.checkExist) {
          return true;
        }
        const clearDbList = _.filter(value, (item) => !/[*%]/.test(item));
        if (clearDbList.length < 1) {
          return true;
        }
        return checkClusterDatabase({
          infos: [
            {
              cluster_id: props.clusterId,
              db_names: [value],
            },
          ],
        }).then((data) => (data.length > 0 ? data[0].check_info[value] : false));
      },
      message: t('DB不存在'),
      trigger: 'blur',
    },
    {
      validator: (value: string) => {
        if (!props.checkNotExist) {
          return true;
        }
        const clearDbList = _.filter(value, (item) => !/[*%]/.test(item));
        if (clearDbList.length < 1) {
          return true;
        }
        return checkClusterDatabase({
          infos: [
            {
              cluster_id: props.clusterId,
              db_names: [value],
            },
          ],
        }).then((data) => (data.length > 0 ? !data[0].check_info[value] : true));
      },
      message: t('DB已存在'),
      trigger: 'blur',
    },
  ];

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string) => {
    emits('batch-edit', value, props.field);
  };
</script>
<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
