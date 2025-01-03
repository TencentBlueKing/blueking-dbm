<template>
  <BkSideslider
    class="sql-log-sideslider"
    :is-show="isShow"
    :title="t('执行SQL变更_内容详情')"
    :width="960"
    @close="handleClose">
    <template
      v-if="executeObject"
      #header>
      <span>{{ t('SQL 内容') }}</span>
      <span style="margin-left: 30px; font-size: 12px; font-weight: normal; color: #63656e">
        <span>{{ t('变更的 DB:') }}</span>
        <span class="ml-4">
          <BkTag
            v-for="item in executeObject.dbnames.slice(0, 3)"
            :key="item">
            {{ item }}
          </BkTag>
          <BkTag
            v-if="executeObject.dbnames.length > 3"
            v-bk-tooltips="{
              content: executeObject.dbnames.join('\n'),
            }">
            ...
          </BkTag>
          <template v-if="executeObject.dbnames.length < 1">--</template>
        </span>
        <span class="ml-25">{{ t('忽略的 DB:') }}</span>
        <span class="ml-4">
          <BkTag
            v-for="item in executeObject.ignore_dbnames.slice(0, 3)"
            :key="item">
            {{ item }}
          </BkTag>
          <BkTag
            v-if="executeObject.ignore_dbnames.length > 3"
            v-bk-tooltips="{
              content: executeObject.ignore_dbnames.join('\n'),
            }">
            ...
          </BkTag>
          <template v-if="executeObject.ignore_dbnames.length < 1">--</template>
        </span>
      </span>
    </template>
    <BkLoading :loading="isContentLoading">
      <div
        v-if="executeObject"
        class="editor-layout">
        <div class="editor-layout-left">
          <RenderFileList
            v-model="localSelectFileName"
            :data="executeObject.sql_files" />
        </div>
        <div class="editor-layout-right">
          <RenderFileContent
            :model-value="currentFileContent"
            readonly
            :title="localSelectFileName" />
        </div>
      </div>
    </BkLoading>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { type Sqlserver } from '@services/model/ticket/ticket';
  import { batchFetchFile } from '@services/source/storage';

  import RenderFileContent from '@views/ticket-center/common/ticket-detail/components/common/SqlFileContent.vue';
  import RenderFileList from '@views/ticket-center/common/ticket-detail/components/common/SqlFileList.vue';

  interface Props {
    executeObject: Sqlserver.ImportSqlFile['execute_objects'][number];
    selectFileName: string;
    path: string;
    wholeFileList: string[];
  }
  const props = defineProps<Props>();
  const { t } = useI18n();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });
  const localSelectFileName = ref('');
  const fileContentMap = shallowRef<Record<string, string>>({});

  const currentFileContent = computed(() => fileContentMap.value[localSelectFileName.value] || '');

  const { loading: isContentLoading, run: runBatchFetchFile } = useRequest(
    () => {
      const filePathList = props.wholeFileList.reduce<string[]>((result, item) => {
        result.push([props.path, item].join('/'));
        return result;
      }, []);

      return batchFetchFile({
        file_path_list: filePathList,
      });
    },
    {
      manual: true,
      onSuccess(result) {
        fileContentMap.value = result.reduce<Record<string, string>>((result, fileInfo) => {
          const fileName = fileInfo.path.split('/').pop() as string;
          return Object.assign(result, {
            [fileName]: fileInfo.content,
          });
        }, {});
      },
    },
  );

  watch(
    () => isShow,
    () => {
      if (isShow.value) {
        localSelectFileName.value = props.selectFileName;
        if (props.wholeFileList.length > 0) {
          runBatchFetchFile();
        }
      }
    },
    {
      immediate: true,
    },
  );

  const handleClose = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .sql-log-sideslider {
    .editor-layout {
      display: flex;
      background: #2e2e2e;

      .editor-layout-left {
        width: 238px;
      }

      .editor-layout-right {
        position: relative;
        height: 100%;
        flex: 1;
      }
    }
  }
</style>
