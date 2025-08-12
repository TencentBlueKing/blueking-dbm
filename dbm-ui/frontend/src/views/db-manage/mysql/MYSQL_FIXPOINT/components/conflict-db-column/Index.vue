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
    :disabled-method="disabledMethod"
    field="conflictDb"
    :label="t('受影响的 DB')"
    :loading="loading"
    :min-width="200">
    <template #head>
      <div
        v-bk-tooltips="{
          content: t('构造的目标已经存在了同名的 DB'),
        }"
        class="conflict-db-head">
        {{ t('受影响的 DB') }}
      </div>
      <span class="required-icon" />
    </template>
    <EditableBlock :placeholder="t('自动生成')">
      <BkButton
        text
        theme="primary"
        @click="handleClick">
        {{ conflictDbNum }}
      </BkButton>
    </EditableBlock>
  </EditableColumn>
  <PriviewConflictDbs
    v-model:is-show="isShowSlider"
    v-bind="props" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import { showDatabasesWithPatterns } from '@/services/source/remoteService';

  import PriviewConflictDbs from './PriviewConflictDbs.vue';

  interface Props {
    rowData: {
      cluster: TendbhaModel;
      databases: string[];
      tables: string[];
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const conflictDbNum = ref(0);
  const isShowSlider = ref(false);

  const { loading, run: fetchData } = useRequest(showDatabasesWithPatterns, {
    manual: true,
    onSuccess: (data) => {
      conflictDbNum.value = data?.[0]?.databases?.length || 0;
    },
  });

  const disabledMethod = (rowData?: any, field?: string) => {
    if (field === 'conflictDb' && !rowData.cluster.id) {
      return t('请先选择待回档集群');
    }
    if (field === 'conflictDb' && rowData.databases?.length <= 0) {
      return t('请先选择源 DB');
    }
    return '';
  };

  const handleClick = () => {
    isShowSlider.value = true;
  };

  watch(
    () => [props.rowData.cluster.id, props.rowData.databases],
    () => {
      if (props.rowData.cluster.id && props.rowData.databases?.length > 0) {
        fetchData({
          infos: [
            {
              cluster_id: props.rowData.cluster.id,
              dbs: props.rowData.databases,
              ignore_dbs: [],
            },
          ],
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .conflict-db-head {
    border-bottom: 1px dashed #979ba5;
  }

  .required-icon::after {
    margin-left: 4px;
    line-height: 20px;
    color: @danger-color;
    content: '*';
  }
</style>
