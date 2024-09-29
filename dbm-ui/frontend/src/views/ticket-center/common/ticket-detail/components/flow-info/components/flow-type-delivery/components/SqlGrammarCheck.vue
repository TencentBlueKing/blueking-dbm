<template>
  <div class="flow-type-delivery-sql-grammar-check">
    <I18nT
      keypath="共n个文件，含有m个高危语句"
      tag="div">
      <span style="font-weight: 700; color: #63656e">
        {{ executeSqlFileList.length }}
      </span>
      <span style="font-weight: 700; color: #ea3636">
        {{ totalWarnCount }}
      </span>
    </I18nT>
    <div
      v-for="fileName in renderSqlFileList"
      :key="fileName">
      <BkButton
        text
        @click="() => handleClickFile(fileName)">
        <DbIcon
          style="color: #3a84ff"
          type="file" />
        <span style="margin-left: 4px; color: #3a84ff">
          {{ getSQLFilename(fileName) }}
        </span>

        <span v-if="ticketDetail.details.grammar_check_info[fileName].highrisk_warnings?.length > 0">
          <span>，</span>
          <span style="color: #ff9c01">{{ t('跳过检查') }}</span>
          <span>，</span>
          <I18nT
            keypath="含有n个高危语句"
            scope="global">
            <span class="danger-count">
              {{ ticketDetail.details.grammar_check_info[fileName].highrisk_warnings.length }}
            </span>
          </I18nT>
        </span>
        <span v-else>
          <span>，</span>
          <span style="color: #2dcb56">{{ t('检查通过') }}</span>
          <span>，</span>
          {{ t('无高危语句') }}
        </span>
      </BkButton>
    </div>
    <div v-if="isShowMore">
      <BkButton
        text
        @click="handleToggleShowMore">
        <span style="color: #3a84ff">
          {{ isShowCollapse ? t('收起') : t('更多') }}
        </span>
        <DbIcon
          class="collapse-dropdown-icon"
          :class="{ 'collapse-dropdown-icon-active': isShowCollapse }"
          style="color: #3a84ff"
          type="down-big" />
      </BkButton>
    </div>
  </div>

  <BkSideslider
    class="sql-log-sideslider"
    :is-show="isShowSqlFile"
    :width="960"
    @closed="() => (isShowSqlFile = false)">
    <template
      v-if="currentFileExecuteObject"
      #header>
      <span>{{ t('SQL 内容') }}</span>
      <span style="margin-left: 30px; font-size: 12px; font-weight: normal; color: #63656e">
        <span>{{ t('变更的 DB:') }}</span>
        <span class="ml-4">
          <BkTag
            v-for="item in currentFileExecuteObject.dbnames"
            :key="item">
            {{ item }}
          </BkTag>
          <template v-if="currentFileExecuteObject.dbnames.length < 1">--</template>
        </span>
        <span class="ml-25">{{ t('忽略的 DB:') }}</span>
        <span class="ml-4">
          <BkTag
            v-for="item in currentFileExecuteObject.ignore_dbnames"
            :key="item">
            {{ item }}
          </BkTag>
          <template v-if="currentFileExecuteObject.ignore_dbnames.length < 1">--</template>
        </span>
      </span>
    </template>
    <div class="editor-layout">
      <div class="editor-layout-left">
        <RenderFileList
          v-model="selectFileName"
          :data="executeSqlFileList" />
      </div>
      <div class="editor-layout-right">
        <RenderFileContent
          :model-value="currentFileContent"
          readonly
          :title="selectFileName" />
      </div>
    </div>
  </BkSideslider>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { batchFetchFile } from '@services/source/storage';

  import RenderFileContent from '@views/ticket-center/common/ticket-detail/components/common/SqlFileContent.vue';
  import RenderFileList from '@views/ticket-center/common/ticket-detail/components/common/SqlFileList.vue';

  import { getSQLFilename } from '@utils';

  interface Props {
    ticketDetail: TicketModel<Mysql.ImportSqlFile>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const renderFileCount = 3;

  const isShowCollapse = ref(false);
  const isShowSqlFile = ref(false);
  const selectFileName = ref('');

  const fileContentMap = shallowRef<Record<string, string>>({});
  const executeSqlFileList = computed(() =>
    _.flatten(props.ticketDetail.details.execute_objects.map((item) => item.sql_files)),
  );

  const isShowMore = computed(() => executeSqlFileList.value.length > renderFileCount);

  const renderSqlFileList = computed(() => {
    if (isShowMore.value && !isShowCollapse.value) {
      return executeSqlFileList.value.slice(0, renderFileCount);
    }
    return executeSqlFileList.value;
  });

  const totalWarnCount = computed(() =>
    Object.values(props.ticketDetail.details.grammar_check_info).reduce((results, item) => {
      const warnCount = item.highrisk_warnings?.length ?? 0;
      return results + warnCount;
    }, 0),
  );

  const currentFileContent = computed(() => fileContentMap.value[selectFileName.value] || '');

  const currentFileExecuteObject = computed(() =>
    _.find(props.ticketDetail.details.execute_objects, (item) => item.sql_files.includes(selectFileName.value)),
  );

  const handleToggleShowMore = () => {
    isShowCollapse.value = !isShowCollapse.value;
  };

  // 查看日志详情
  const handleClickFile = (value: string) => {
    isShowSqlFile.value = true;
    selectFileName.value = value;
  };

  onMounted(() => {
    const filePathList = executeSqlFileList.value.reduce((result, item) => {
      result.push(`${props.ticketDetail.details.path}/${item}`);
      return result;
    }, [] as string[]);

    batchFetchFile({
      file_path_list: filePathList,
    }).then((result) => {
      fileContentMap.value = result.reduce(
        (result, fileInfo) => {
          const fileName = fileInfo.path.split('/').pop() as string;
          return Object.assign(result, {
            [fileName]: fileInfo.content,
          });
        },
        {} as Record<string, string>,
      );
      [selectFileName.value] = executeSqlFileList.value;
    });
  });
</script>

<style lang="less">
  .flow-type-delivery-sql-grammar-check {
    display: flex;
    margin-top: 12px;
    margin-bottom: 10px;
    gap: 8px;
    flex-direction: column;

    .danger-count {
      display: inline-block;
      font-weight: 700;
      color: #ea3636;
    }

    .collapse-dropdown-icon {
      transform: rotate(0);
      transition: all 0.5s;
    }

    .collapse-dropdown-icon-active {
      transform: rotate(-180deg);
    }
  }

  .sql-log-sideslider {
    .editor-layout {
      display: flex;
      width: 100%;
      height: calc(100vh - 52px);
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
