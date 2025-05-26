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
  <BkResizeLayout
    :border="false"
    class="editor-resize-wrapper"
    :initial-divide="250"
    :max="600"
    :min="100"
    placement="bottom"
    :style="resizeLayoutStyle"
    @after-resize="handleAfterResize">
    <template #main>
      <Editor
        ref="editorRef"
        :db-type="dbType"
        :hide-my-collection="isMysqlProxy"
        :is-execut-disabled="!executable || instances.length === 0"
        :is-execut-loading="isExecuting"
        :is-proxy="isMysqlProxy"
        @execute="handleExecute" />
    </template>
    <template #aside>
      <QueryResult
        :key="queryType"
        :data="queryResult"
        :db-type="dbType"
        :query-seconds="querySeconds" />
    </template>
  </BkResizeLayout>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';

  import { checkInstance, dbConsole } from '@services/source/dbbase';

  import { DBTypes } from '@common/const';

  import Editor from './components/editor/Index.vue';
  import QueryResult from './components/query-result/Index.vue';

  export type DbConsoleResults = ServiceReturnType<typeof dbConsole>;

  interface Props {
    dbType?: DBTypes;
    executable?: boolean;
    instances?: string[];
    queryType?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
    executable: true,
    instances: () => [],
    queryType: '',
  });

  const editorRef = ref<InstanceType<typeof Editor>>();
  const resizeLayoutStyle = ref();
  const isExecuting = ref(false);
  const queryResult = ref<DbConsoleResults>([]);
  const querySeconds = ref(0);
  const isMysqlProxy = computed(() => props.dbType === DBTypes.MYSQL && props.queryType === 'proxy');

  const handleExecute = async (sql: string) => {
    queryResult.value = [];
    const startTime = dayjs();
    isExecuting.value = true;
    try {
      const instancesResult = await checkInstance({ instance_addresses: props.instances });
      const instanceInfoList = instancesResult.map((item) => ({
        bk_cloud_id: item.bk_cloud_id,
        instance: item.instance_address,
      }));
      queryResult.value = await dbConsole({
        cmd: sql,
        db_type: props.dbType,
        instances: instanceInfoList,
        is_proxy: isMysqlProxy.value,
      });
    } finally {
      isExecuting.value = false;
      const endTime = dayjs();
      querySeconds.value = endTime.diff(startTime, 'second');
    }
  };

  const handleAfterResize = () => {
    editorRef.value!.updateCollectPanel();
  };

  onMounted(() => {
    nextTick(() => {
      resizeLayoutStyle.value = {
        height: `${window.innerHeight - 400}px`,
      };
    });
  });
</script>
<style lang="less">
  .result-panel-main {
    height: 100%;
    background: #fff;
  }

  .editor-resize-wrapper {
    height: 600px !important;

    .bk-resize-layout-aside-content {
      height: auto !important;
      overflow: auto !important;
    }
  }
</style>
