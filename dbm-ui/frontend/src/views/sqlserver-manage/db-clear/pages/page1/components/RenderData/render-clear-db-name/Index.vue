<template>
  <BkLoading :loading="isLoading">
    <span
      v-bk-tooltips="{
        content: disabledTips,
        disabled: !Boolean(disabledTips),
      }">
      <TableEditElement
        ref="elementRef"
        :rules="rules">
        <BkButton
          :disabled="Boolean(disabledTips)"
          text
          theme="primary"
          @click="handleShowEditName">
          {{ localDbList.length < 1 ? '--' : localDbList.length }}
        </BkButton>
      </TableEditElement>
    </span>
  </BkLoading>
  <BkSideslider
    v-if="clusterData"
    v-model:is-show="isShowEditName"
    class="sqlserver-manage-db-clear-clean-db"
    :width="900">
    <template #header>
      <span>{{ t('手动修改回档的 DB 名 ') }}</span>
      <BkTag class="ml-8">{{ clusterData?.domain }}</BkTag>
    </template>
    <div>
      <EditDb
        :cluster-id="clusterData.id"
        :db-ignore-name="cleanIgnoreDbsPatterns"
        :db-name="cleanDbsPatterns"
        @change="handleEditDbChange" />
      <div class="mt-24">
        <span style="font-weight: bold; color: #313238">{{ t('最终 DB') }}</span>
        <I18nT keypath="(共 n 个)">
          <span>{{ localDbList.length }}</span>
        </I18nT>
      </div>
      <div class="clean-db-wrapper">
        <div
          v-for="(tagItem, index) in localDbList"
          :key="index">
          {{ tagItem }}
        </div>
      </div>
    </div>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { computed, ref, shallowRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSqlserverDbs } from '@services/source/sqlserver';

  import TableEditElement from '@components/render-table/columns/element/Index.vue';

  import EditDb from '@views/sqlserver-manage/common/EditDb.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    clusterData?: IDataRow['clusterData'];
  }

  interface Expose {
    getValue: () => Promise<Record<'clean_dbs', string[]>>;
  }

  const props = defineProps<Props>();

  const cleanDbsPatterns = defineModel<IDataRow['cleanDbsPatterns']>('cleanDbsPatterns', {
    required: true,
  });

  const cleanIgnoreDbsPatterns = defineModel<IDataRow['cleanIgnoreDbsPatterns']>('cleanIgnoreDbsPatterns', {
    required: true,
  });

  const { t } = useI18n();

  const elementRef = ref<InstanceType<typeof TableEditElement>>();
  const localDbList = shallowRef<string[]>([]);
  const isShowEditName = ref(false);
  const hasEditDbName = ref(false);

  const disabledTips = computed(() => {
    if (props.clusterData && cleanDbsPatterns.value.length > 0) {
      return '';
    }
    return t('请先设置集群、构造 DB');
  });

  const rules = [
    {
      validator: () => localDbList.value.length > 0,
      message: t('构造后 DB 名不能为空'),
    },
    {
      validator: () => hasEditDbName.value,
      message: t('构造后 DB 名待有冲突更新'),
    },
  ];

  const { loading: isLoading, run: fetchSqlserverDbs } = useRequest(getSqlserverDbs, {
    manual: true,
    onSuccess(data) {
      localDbList.value = data;
    },
  });

  watch(
    () => [props.clusterData, cleanDbsPatterns.value, cleanIgnoreDbsPatterns.value],
    () => {
      if (!props.clusterData || cleanDbsPatterns.value.length < 1) {
        return;
      }
      fetchSqlserverDbs({
        cluster_id: props.clusterData.id,
        db_list: cleanDbsPatterns.value,
        ignore_db_list: cleanIgnoreDbsPatterns.value,
      });
    },
    {
      immediate: true,
    },
  );

  const handleEditDbChange = (payload: {
    dbName: IDataRow['cleanDbsPatterns'];
    dbIgnoreName: IDataRow['cleanIgnoreDbsPatterns'];
  }) => {
    cleanDbsPatterns.value = payload.dbName;
    cleanIgnoreDbsPatterns.value = payload.dbIgnoreName;
  };

  const handleShowEditName = () => {
    isShowEditName.value = true;
  };

  defineExpose<Expose>({
    getValue() {
      return elementRef.value!.getValue().then(() => ({
        clean_dbs: localDbList.value,
      }));
    },
  });
</script>
<style lang="less">
  .sqlserver-manage-db-clear-clean-db {
    .bk-sideslider-content {
      padding: 20px 24px 0;
    }

    .clean-db-wrapper {
      padding: 16px;
      margin-top: 16px;
      background: #f5f7fa;
      border-radius: 2px;
    }
  }
</style>
