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
      <div style="display: none">
        <div ref="popRef">
          <p>{{ t('逻辑备份：仅影响目标集群中存在的同名Database') }}</p>
          <p>{{ t('物理备份：将清空目标集群的所有Database') }}</p>
        </div>
      </div>
      <div
        ref="rootRef"
        class="conflict-db-head"
        @mouseenter="handleShowTips">
        {{ t('受影响的 DB') }}
      </div>
      <span class="required-icon" />
    </template>
    <EditableBlock :placeholder="t('自动生成')">
      <BkButton
        v-if="isParamsComplete"
        text
        theme="primary"
        @click="handleClick">
        {{ modelValue.length }}
      </BkButton>
    </EditableBlock>
  </EditableColumn>
  <PriviewConflictDbs
    v-model:is-show="isShowSlider"
    v-bind="props" />
</template>
<script lang="ts" setup>
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import BackupLogRecordModel from '@services/model/mysql/backup-log-record';
  import { showDatabasesWithPatterns } from '@services/source/remoteService';

  import PriviewConflictDbs from './PriviewConflictDbs.vue';

  interface Props {
    /**
     * 指源库表是否可编辑
     * true：默认*，不可编辑
     * false: 可填
     */
    disabled?: boolean;
    rowData: {
      backupRecord: BackupLogRecordModel;
      cluster: {
        id: number;
        master_domain: string;
      };
      databases: string[];
      tables: string[];
      targetCluster?: {
        id: number;
        master_domain: string;
      };
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const isShowSlider = ref(false);
  const rootRef = ref();
  const popRef = ref();
  // 参数是否选填完整
  const isParamsComplete = ref(false);

  let tippyIns: Instance | undefined;

  const { loading, run: fetchData } = useRequest(showDatabasesWithPatterns, {
    manual: true,
    onSuccess: (data) => {
      let dataList = data?.[0]?.databases || [];
      if (!props.disabled) {
        // 可填时需根据备份记录的 database_list 与目标集群的 db 列表取交集
        dataList = dataList.filter((item) => props.rowData.backupRecord.database_list?.includes(item));
      }
      modelValue.value = dataList;
    },
  });

  const disabledMethod = (rowData?: any) => {
    if (!rowData.backupRecord) {
      return t('请先选择备份记录');
    }
    if (rowData.databases?.length <= 0) {
      return t('请先选择源 DB');
    }
    const targetCluster = rowData?.targetCluster || rowData?.cluster;
    if (!targetCluster?.id) {
      return t('请先选择目标集群');
    }
    return '';
  };

  const handleClick = () => {
    isShowSlider.value = true;
  };

  const handleShowTips = () => {
    tippyIns?.show();
  };

  onMounted(() => {
    setTimeout(() => {
      if (rootRef.value && popRef.value) {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          allowHTML: true,
          appendTo: () => document.body,
          arrow: true,
          content: popRef.value,
          hideOnClick: true,
          interactive: true,
          maxWidth: 'none',
          offset: [0, 8],
          placement: 'top',
          theme: 'black',
          trigger: 'mouseenter click',
          zIndex: 999999,
        });
      }
    }, 60);
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns?.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });

  watch(
    () => [
      props.rowData.cluster.id,
      props.rowData.backupRecord?.backup_id,
      props.rowData.databases,
      props.rowData.targetCluster?.id,
    ],
    () => {
      modelValue.value = [];
      let valid = false;
      if (props.rowData.targetCluster) {
        valid = Boolean(
          props.rowData.cluster.id &&
          props.rowData.backupRecord?.backup_id &&
          props.rowData.databases.length &&
          props.rowData.targetCluster.id,
        );
      } else {
        valid = Boolean(
          props.rowData.cluster.id && props.rowData.backupRecord?.backup_id && props.rowData.databases.length,
        );
      }
      isParamsComplete.value = valid;
      if (!valid) {
        return;
      }

      const clusterId = props.rowData.targetCluster?.id || props.rowData.cluster.id; // 回档的目标集群是源集群
      const dbs = props.rowData.databases || [];
      if (clusterId) {
        fetchData({
          infos: [
            {
              cluster_id: clusterId,
              dbs,
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
