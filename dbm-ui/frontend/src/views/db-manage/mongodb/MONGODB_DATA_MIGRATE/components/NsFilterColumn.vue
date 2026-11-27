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
    v-model="dbPatterns"
    :append-rules="rules"
    :disabled-method="disabledMethod"
    field="db_patterns"
    :label="t('库表范围')"
    :min-width="240"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-for="item in batchFields"
        :key="item.field"
        v-model="item.show"
        :title="item.title"
        type="taginput"
        @change="(value) => handleBatchEdit(value, item.field)">
        <span
          v-bk-tooltips="item.tips"
          class="batch-select-button"
          @click="item.show = true">
          {{ item.short }}
        </span>
      </BatchEditColumn>
    </template>
    <div class="ns-filter-cell">
      <span class="ns-filter-label">{{ t('DB 名') }}</span>
      <EditableTagInput
        v-model="dbPatterns"
        allow-create
        clearable
        :placeholder="t('请输入DB 名称，支持通配符“*”')"
        :split-fn="tagInputSplitFn" />
      <span class="ns-filter-label">{{ t('忽略 DB') }}</span>
      <EditableTagInput
        v-model="ignoreDbs"
        allow-create
        clearable
        :placeholder="t('可选')"
        :split-fn="tagInputSplitFn" />
      <span class="ns-filter-label">{{ t('表名') }}</span>
      <EditableTagInput
        v-model="tablePatterns"
        allow-create
        clearable
        :placeholder="t('请输入表名，支持通配符“*”')"
        :split-fn="tagInputSplitFn" />
      <span class="ns-filter-label">{{ t('忽略表') }}</span>
      <EditableTagInput
        v-model="ignoreTables"
        allow-create
        clearable
        :placeholder="t('可选，与忽略 DB 同时填写')"
        :split-fn="tagInputSplitFn" />
    </div>
  </EditableColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { checkClusterDatabase } from '@services/source/dbbase';

  import { batchSplitRegex } from '@common/regex';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'batch-edit', value: string[], field: string) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const dbPatterns = defineModel<string[]>('dbPatterns', { required: true });
  const ignoreDbs = defineModel<string[]>('ignoreDbs', { required: true });
  const tablePatterns = defineModel<string[]>('tablePatterns', { required: true });
  const ignoreTables = defineModel<string[]>('ignoreTables', { required: true });

  const { t } = useI18n();

  const namePattern = /^[a-zA-Z0-9_-]*\*?[a-zA-Z0-9_-]*$/;
  const systemDbs = ['admin', 'config', 'local'];

  const batchFields = reactive([
    { field: 'db_patterns', short: 'DB', show: false, tips: t('批量设置 DB 名'), title: t('DB 名') },
    { field: 'ignore_dbs', short: t('忽略'), show: false, tips: t('批量设置忽略 DB'), title: t('忽略 DB') },
    { field: 'table_patterns', short: t('表'), show: false, tips: t('批量设置表名'), title: t('表名') },
    { field: 'ignore_tables', short: t('忽略表'), show: false, tips: t('批量设置忽略表'), title: t('忽略表') },
  ]);

  const rules = [
    {
      message: t('库名长度不超过64个字符'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => item.length <= 64),
    },
    {
      message: t('表名不能为空'),
      trigger: 'change',
      validator: () => tablePatterns.value.length > 0,
    },
    {
      message: t('表名长度不超过255个字符'),
      trigger: 'change',
      validator: () => _.every(tablePatterns.value, (item) => item.length <= 255),
    },
    {
      message: t('输入格式有误'),
      trigger: 'change',
      validator: (value: string[]) =>
        _.every(value, (item) => namePattern.test(item)) &&
        _.every(ignoreDbs.value, (item) => namePattern.test(item)) &&
        _.every(tablePatterns.value, (item) => namePattern.test(item)) &&
        _.every(ignoreTables.value, (item) => namePattern.test(item)),
    },
    {
      message: t('不允许输入系统库和特殊库'),
      trigger: 'change',
      validator: (value: string[]) =>
        _.every(value, (item) => !systemDbs.includes(item)) &&
        _.every(ignoreDbs.value, (item) => !systemDbs.includes(item)),
    },
    {
      message: t('忽略DB名、忽略表名要么同时为空, 要么同时不为空'),
      trigger: 'change',
      validator: () => (ignoreDbs.value.length === 0) === (ignoreTables.value.length === 0),
    },
    {
      message: t('DB 不存在'),
      trigger: 'blur',
      validator: (value: string[]) => {
        const clearDbList = _.filter(value, (item) => !/[*%]/.test(item));
        if (clearDbList.length < 1 || !props.clusterId) {
          return true;
        }
        return checkClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.clusterId,
          db_list: value,
        }).then((data) => {
          const notExistDbList = Object.keys(data).reduce<string[]>((result, dbName) => {
            if (!data[dbName]) {
              result.push(dbName);
            }
            return result;
          }, []);
          if (notExistDbList.length > 0) {
            return t('n 不存在', { n: notExistDbList.join('、') });
          }
          return true;
        });
      },
    },
  ];

  const tagInputSplitFn = (value: string) => value.split(batchSplitRegex);

  const disabledMethod = () => (!props.clusterId ? t('请先输入合法的集群域名') : false);

  const handleBatchEdit = (value: string[] | string, field: string) => {
    emits('batch-edit', value as string[], field);
  };
</script>

<style lang="less" scoped>
  .batch-select-button {
    margin-left: 8px;
    font-size: 12px;
    color: #3a84ff;
    cursor: pointer;
  }

  .ns-filter-cell {
    display: flex;
    width: 100%;
    flex-direction: column;
    gap: 4px;
    padding: 8px 0;
  }

  .ns-filter-label {
    font-size: 12px;
    line-height: 20px;
    color: #979ba5;
  }
</style>
