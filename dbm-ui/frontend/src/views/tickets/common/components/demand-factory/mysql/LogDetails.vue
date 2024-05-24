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
  <div class="log-layout">
    <div
      v-if="fileList.length > 1"
      class="layout-left">
      <RenderFileList
        v-model="selectFileName"
        :file-log-map="fileLogMap"
        :flow-status="flowStatus"
        :list="fileDataList" />
    </div>
    <div
      class="layout-right"
      style="width: 928px">
      <div class="log-header">
        <div>{{ t('执行日志') }}</div>
        <div class="log-status">
          <DbIcon
            v-if="currentSelectFileData?.isSuccessed"
            style="color: #2dcb56;"
            type="check-circle-fill" />
          <DbIcon
            v-else-if="currentSelectFileData?.isPending"
            svg
            type="sync-pending" />
          <DbIcon
            v-else-if="currentSelectFileData?.isWaiting"
            class="rotate-loading"
            style="color: #2dcb56"
            svg
            type="check-circle-fill" />
          <DbIcon
            v-else
            style="color: #ea3636;"
            svg
            type="delete-fill" />
          <span style="padding-left: 4px; font-size: 12px;">{{ executedStatusDisplayText }}</span>
        </div>
      </div>
      <div style="height: calc(100% - 40px)">
        <RenderLog :data="renderLog" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { querySemanticData } from '@services/source/sqlImport';

  import { useGlobalBizs } from '@stores';

  import RenderFileList, {
    type IFileItem,
  } from '@views/mysql/sql-execute/steps/step2/components/render-file-list/Index.vue';
  import RenderLog from '@views/mysql/sql-execute/steps/step2/components/RenderLog.vue';
  import useFlowStatus from '@views/mysql/sql-execute/steps/step2/hooks/useFlowStatus';
  import useLog from '@views/mysql/sql-execute/steps/step2/hooks/useLog';

  interface Props {
    rootId?: string;
    nodeId?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    rootId: '',
    nodeId: '',
  });

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const selectFileName = ref('');
  const fileImportMode = ref('');
  const fileList = ref<string[]>([]);
  const renderLog = shallowRef<any[]>([]);

  // 执行状态
  const { flowStatus } = useFlowStatus(props.rootId);
  // 执行日志
  const { fileLogMap } = useLog(props.rootId, props.nodeId);

  const fileDataList = computed<IFileItem[]>(() => fileList.value.map(name => ({
    name,
    isPending: fileLogMap.value[name]?.status === 'RUNNING',
    isSuccessed: fileLogMap.value[name]?.status === 'SUCCEEDED',
    isFailed: fileLogMap.value[name]?.status === 'FAILED',
    isWaiting: fileLogMap.value[name]?.status === 'PENDING',
  })));

  const currentSelectFileData = computed(() =>
    _.find(fileDataList.value, (item) => item.name === selectFileName.value),
  );

  const executedStatusDisplayText = computed(() => {
    if (currentSelectFileData.value?.isSuccessed) {
      return t('执行成功');
    } if (currentSelectFileData.value?.isPending) {
      return t('执行中');
    } if (currentSelectFileData.value?.isWaiting) {
      return t('待执行');
    }
    return t('执行失败');
  });

  watch([fileImportMode, selectFileName, fileLogMap], () => {
    renderLog.value = fileLogMap.value[selectFileName.value]?.match_logs ?? [];
  });

  onMounted(() => {
    querySemanticData({
      bk_biz_id: currentBizId,
      root_id: props.rootId,
    }).then((data) => {
      fileImportMode.value = data.import_mode;
      fileList.value = data.semantic_data.execute_sql_files.map((item) => item.replace(/[^_]+_/, ''));
      // 默认选中第一个问题件
      [selectFileName.value] = fileList.value;
    });
  });
</script>
<style lang="less" scoped>
  .log-layout {
    display: flex;
    width: 928px;
    height: 100%;
    margin: 0 auto;
    overflow: hidden;
    border-radius: 2px;
    justify-content: center;

    .layout-left {
      width: 238px;
    }

    .layout-right {
      flex: 1;
    }

    .log-header {
      display: flex;
      height: 40px;
      padding: 0 20px;
      font-size: 14px;
      color: #fff;
      background: #2e2e2e;
      align-items: center;
    }

    .log-status {
      display: flex;
      padding-left: 14px;
      align-items: center;
      font-size: 12px;
    }
  }

  .bk-log {
    position: relative;
    z-index: 1;
  }

  .sql-execute-more-action-box {
    display: flex;
    justify-content: center;
    height: 52px;
    background: #fff;
    box-shadow: 0 -1px 0 0 #dcdee5;
    align-items: center;
  }
</style>
