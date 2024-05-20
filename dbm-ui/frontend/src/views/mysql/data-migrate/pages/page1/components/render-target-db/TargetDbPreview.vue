<template>
  <div class="preview-main">
    <RenderTable>
      <template #default>
        <RenderTableHeadColumn
          :min-width="90"
          :width="210">
          {{ t('迁移DB名 ') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="90"
          :required="false"
          :width="210">
          {{ t('忽略DB名') }}
        </RenderTableHeadColumn>
      </template>

      <template #data>
        <tr>
          <td style="padding: 0">
            <RenderDbName
              ref="dbPatternsRef"
              v-model="dbInfo.dbs"
              :cluster-id="data.sourceClusterId"
              required
              @change="handleDbsChange" />
          </td>
          <td style="padding: 0">
            <RenderDbName
              ref="ignoreDbsRef"
              v-model="dbInfo.ignoreDbs"
              :cluster-id="data.sourceClusterId"
              :required="false"
              @change="handleDbsChange" />
          </td>
        </tr>
      </template>
    </RenderTable>
    <div class="preview-header">
      <span class="title">{{ t('最终DB') }}</span>
      <span>（{{ t('共n个', [previewDataList.length]) }}）</span>
    </div>
    <div class="preview-copy">
      <BkButton
        text
        theme="primary"
        @click="handleCopy">
        <DbIcon type="copy" />
        <span class="ml-6">{{ t('复制') }}</span>
      </BkButton>
    </div>
    <div class="preview-content">
      <div
        v-for="name in previewDataList"
        :key="name"
        class="name-item">
        {{ name }}
      </div>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { showDatabasesWithPatterns } from '@services/source/remoteService';

  import { useCopy } from '@hooks';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  import RenderDbName from '@views/mysql/common/edit-field/DbName.vue';

  export type DbsType = Omit<Props['data'], 'sourceClusterId' | 'targetClusters'>

  interface Props {
    data: {
      sourceClusterId: number;
      dbs: string[];
      ignoreDbs: string[];
    };
  }

  interface Emits {
    (e: 'change', value: DbsType): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const copy = useCopy();

  const previewDataList = ref<string[]>([]);

  const dbInfo = reactive({
    dbs: [] as string[],
    ignoreDbs: [] as string[],
  });

  watch(
    () => props.data,
    () => {
      dbInfo.dbs = props.data.dbs;
      dbInfo.ignoreDbs = props.data.ignoreDbs;
    },
    {
      immediate: true,
      deep: true,
    },
  );

  const { run: fetchDatabasesWithPattern } = useRequest(showDatabasesWithPatterns, {
    manual: true,
    onSuccess(data) {
      previewDataList.value = data[0].databases;
    },
  });

  const handleDbsChange = () => {
    const { sourceClusterId } = props.data;
    if (!sourceClusterId) {
      return;
    }

    emits('change', dbInfo);
    fetchDatabasesWithPattern({
      infos: [
        {
          cluster_id: sourceClusterId,
          dbs: dbInfo.dbs,
          ignore_dbs: dbInfo.ignoreDbs,
        },
      ],
    });
    window.changeConfirm = false;
  };

  const handleCopy = () => {
    copy(previewDataList.value.join('\n'));
  };

  onMounted(() => {
    handleDbsChange();
  });
</script>
<style lang="less" scoped>
.preview-main {
  padding: 16px 24px;

  .preview-header {
    margin: 24px 0 16px;
    display: flex;
    .title {
      font-weight: 700;
      color: #313238;
    }
  }

  .preview-copy {
    width: 100%;
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
    margin-top: -24px;
  }

  .preview-content {
    display: flex;
    flex-wrap: wrap;
    padding: 16px;
    background: #f5f7fa;

    .name-item {
      width: 260px;
      line-height: 24px;
      margin: 0 13px 0 0;
    }
  }
}

</style>
