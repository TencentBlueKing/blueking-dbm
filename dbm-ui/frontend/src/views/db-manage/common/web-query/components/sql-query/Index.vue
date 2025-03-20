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
    :initial-divide="500"
    :max="600"
    :min="150"
    placement="bottom"
    :style="resizeLayoutStyle"
    @after-resize="handleAfterResize">
    <template #main>
      <Editor
        ref="editorRef"
        :db-type="dbType"
        :hide-my-collection="isMysqlProxy"
        :is-execut-disabled="instances.length === 0"
        :is-execut-loading="isExecuting"
        :read-only="isMysqlProxy"
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
    instances?: string[];
    queryType?: string;
  }

  type Emits = (e: 'execute') => void;

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
    instances: () => [],
    queryType: '',
  });

  const emits = defineEmits<Emits>();

  const editorRef = ref<InstanceType<typeof Editor>>();
  const resizeLayoutStyle = ref();
  const isExecuting = ref(false);
  const queryResult = ref<DbConsoleResults>([]);
  const querySeconds = ref(0);

  const isMysqlProxy = computed(() => props.dbType === DBTypes.MYSQL && props.queryType === 'proxy');

  const handleExecute = async (sql: string) => {
    emits('execute');
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
      });
      console.log(queryResult);
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
<style lang="less" scoped>
  .sql-execute-editor {
    position: relative;
    z-index: 0;
    height: 100%;

    &.is-full-screen {
      display: flex;
      height: 100vh;
      flex-direction: column;

      .editor-resize-wrapper {
        flex: 1;
      }
    }

    .editor-layout-header {
      display: flex;
      align-items: center;
      height: 40px;
      padding-right: 16px;
      padding-left: 25px;
      font-size: 14px;
      color: #c4c6cc;
      background: #2e2e2e;

      .query-operation-main {
        display: flex;
        font-size: 12px;
        cursor: pointer;
        flex: 1;
        justify-content: flex-end;

        .operation-item {
          display: flex;
          width: 90px;
          align-items: center;
          justify-content: center;

          &.operation-item-active {
            color: #699df4;
          }
        }
      }

      .editro-action-box {
        display: flex;
        margin-left: auto;
        color: #979ba5;
        align-items: center;

        & > * {
          cursor: pointer;
        }
      }
    }

    .editor-resize-wrapper {
      height: calc(100% - 40px);
      background: #212121;

      // &.resize-disabled {
      //   :deep(.bk-resize-layout-aside) {
      //     &::after {
      //       display: none;
      //     }
      //   }
      // }
    }
  }
</style>
<style lang="less">
  .bk-resize-layout-main {
    position: relative;
  }

  .result-panel-main {
    height: 100%;
    background: #fff;
  }
</style>
