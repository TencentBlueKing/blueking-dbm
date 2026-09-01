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
    ref="editableColumnRef"
    :disabled-method="disabledMethod"
    field="rename_infos"
    :label="t('恢复后库名')"
    :min-width="300"
    :rules="rules">
    <BkLoading :loading="isLoading || isCheckoutDbLoading">
      <EditableBlock>
        <BkButton
          text
          theme="primary"
          @click="handleShowEditName">
          <span v-if="moduleValue.length < 1">--</span>
          <template v-else>
            <span v-if="hasEditDbName">
              {{ t('已更新') }}
            </span>
            <I18nT
              v-else
              keypath="n项待修改">
              <span style="padding-right: 4px; font-weight: bold; color: #ea3636">
                {{ moduleValue.length }}
              </span>
            </I18nT>
          </template>
        </BkButton>
      </EditableBlock>
    </BkLoading>
  </EditableColumn>
  <EditName
    v-if="cluster.id && targetCluster.id"
    v-model:is-show="isShowEditName"
    :data="renameInfoData"
    @submit="handleSubmit" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkClusterDatabase } from '@services/source/dbbase';
  import { queryBackupLogs, queryDbsByBackupLog } from '@services/source/sqlserver';

  import EditName, { type IValue } from './components/edit-rename-info/Index.vue';

  interface Props {
    cluster: {
      id: number;
      master_domain: string;
    };
    isLocal: boolean;
    restoreBackupFile?: ServiceReturnType<typeof queryBackupLogs>[number];
    restoreTime?: string;
    targetCluster: {
      cluster_type?: string;
      id: number;
      master_domain: string;
    };
  }

  const props = defineProps<Props>();

  const moduleValue = defineModel<IValue[]>({
    required: true,
  });

  const dbName = defineModel<string[]>('dbName', {
    required: true,
  });

  const dbIgnoreName = defineModel<string[]>('dbIgnoreName', {
    required: true,
  });

  const { t } = useI18n();

  const editableColumnRef = useTemplateRef('editableColumnRef');

  const isShowEditName = ref(false);
  const hasEditDbName = ref(false);

  const renameInfoData = computed(() => ({
    backupDbList: props.restoreBackupFile?.backup_db_list,
    dbIgnoreName: dbIgnoreName.value,
    dbName: dbName.value,
    renameInfoList: moduleValue.value,
    srcCluster: props.cluster,
    targetCluster: props.targetCluster,
  }));

  const rules = [
    {
      message: t('构造后 DB 名待有冲突更新'),
      trigger: 'change',
      validator: () => hasEditDbName.value,
    },
  ];

  const { loading: isCheckoutDbLoading, run: runCheckClusterDatabase } = useRequest(checkClusterDatabase, {
    manual: true,
    onSuccess(data) {
      hasEditDbName.value = _.every(Object.values(data), (item) => !item);
    },
  });

  const { loading: isLoading, run: runQueryDbsByBackupLog } = useRequest(queryDbsByBackupLog, {
    manual: true,
    onSuccess(data) {
      moduleValue.value = data.map((item) => ({
        db_name: item,
        rename_db_name: '',
        target_db_name: item,
      }));
      if (data.length > 0) {
        runCheckClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.targetCluster.id,
          db_list: data,
        });
      }
    },
  });

  let isInnerChange = false;

  let skipWatchUntil = 0;

  watch(
    () => [
      props.cluster.id,
      props.targetCluster.id,
      props.restoreTime,
      props.restoreBackupFile,
      dbName.value,
      dbIgnoreName.value,
    ],
    () => {
      if (isInnerChange) {
        isInnerChange = false;
        return;
      }
      if (Date.now() < skipWatchUntil) {
        return;
      }
      if (
        !props.cluster.id ||
        !props.targetCluster.id ||
        dbName.value.length < 1 ||
        (!props.restoreTime && !props.restoreBackupFile)
      ) {
        return;
      }
      runQueryDbsByBackupLog({
        backup_logs: props.restoreBackupFile ? { logs: props.restoreBackupFile.logs } : undefined,
        cluster_id: props.cluster.id,
        db_pattern: dbName.value,
        ignore_db: dbIgnoreName.value,
        restore_time: props.restoreTime,
      });
    },
    {
      immediate: true,
    },
  );

  defineExpose({
    setSkipNextWatch() {
      skipWatchUntil = Date.now() + 3000;
    },
  });

  const handleShowEditName = () => {
    isShowEditName.value = true;
  };

  const disabledMethod = () => {
    if (
      props.cluster.id &&
      props.targetCluster.id &&
      dbName.value.length > 0 &&
      (props.restoreBackupFile || props.restoreTime)
    ) {
      return false;
    }
    return props.isLocal ? t('请先设置集群、构造 DB、回档信息') : t('请先设置集群、目标集群、构造 DB、回档信息');
  };

  const handleSubmit = (result: Pick<typeof renameInfoData.value, 'dbIgnoreName' | 'dbName' | 'renameInfoList'>) => {
    isInnerChange = true;
    isShowEditName.value = false;
    hasEditDbName.value = true;
    dbName.value = result.dbName;
    dbIgnoreName.value = result.dbIgnoreName;
    moduleValue.value = result.renameInfoList;

    editableColumnRef.value!.validate();
  };
</script>

<style lang="less" scoped>
  .render-rename {
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
