<template>
  <BkLoading :loading="isLoading">
    <span
      v-bk-tooltips="{
        content: disabledTips,
        disabled: !Boolean(disabledTips),
      }"
      @click="handleShowEditName">
      <TableEditElement
        ref="elementRef"
        :rules="rules">
        <BkButton
          :disabled="Boolean(disabledTips)"
          text
          theme="primary">
          <span v-if="localRenameInfoList.length < 1">--</span>
          <template v-else>
            <span v-if="hasEditDbName">
              {{ t('已更新') }}
            </span>
            <I18nT
              v-else
              keypath="n项待修改">
              <span style="padding-right: 4px; font-weight: bold; color: #ea3636">
                {{ localRenameInfoList.length }}
              </span>
            </I18nT>
          </template>
        </BkButton>
      </TableEditElement>
    </span>
  </BkLoading>
  <BkSideslider
    v-model:is-show="isShowEditName"
    render-directive="if"
    :width="900">
    <template #header>
      <span>{{ t('手动修改回档的 DB 名 ') }}</span>
      <BkTag class="ml-8">{{ clusterData?.domain }}</BkTag>
    </template>
    <EditName
      v-if="clusterData"
      ref="editNameRef"
      :cluster-id="clusterData.id"
      :db-ignore-name="dbIgnoreName"
      :db-name="dbName"
      :rename-info-list="localRenameInfoList"
      :target-cluster-id="clusterData.id" />
    <template #footer>
      <BkButton
        class="w-88"
        theme="primary"
        @click="handleSubmit">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { computed, ref, shallowRef, watch } from 'vue';
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryBackupLogs, queryDbsByBackupLog } from '@services/source/sqlserver';

  import TableEditElement from '@components/render-table/columns/element/Index.vue';

  import EditName, { type IValue } from '@views/sqlserver-manage/common/edit-rename-info/Index.vue';

  interface Props {
    clusterData?: {
      id: number;
      domain: string;
    };
    restoreTime?: string;
    restoreBackupFile?: ServiceReturnType<typeof queryBackupLogs>[number];
  }

  interface Expose {
    getValue: () => Promise<Record<'rename_infos', IValue[]>>;
  }

  const props = defineProps<Props>();

  const dbName = defineModel<string[]>('dbName', {
    required: true,
  });

  const dbIgnoreName = defineModel<string[]>('dbIgnoreName', {
    required: true,
  });

  const { t } = useI18n();

  const elementRef = ref<ComponentExposed<typeof TableEditElement>>();
  const editNameRef = ref<InstanceType<typeof EditName>>();
  const localRenameInfoList = shallowRef<
    {
      db_name: string;
      target_db_name: string;
      rename_db_name: string;
    }[]
  >([]);
  const isShowEditName = ref(false);
  const hasEditDbName = ref(false);

  const disabledTips = computed(() => {
    if (props.clusterData && dbName.value.length > 0) {
      return '';
    }
    return t('请先设置集群、构造 DB');
  });

  const rules = [
    {
      validator: () => localRenameInfoList.value.length > 0,
      message: t('构造后 DB 名不能为空'),
    },
    {
      validator: () => hasEditDbName.value,
      message: t('构造后 DB 名待有冲突更新'),
    },
  ];

  const { loading: isLoading, run: fetchSqlserverDbs } = useRequest(queryDbsByBackupLog, {
    manual: true,
    onSuccess(data) {
      localRenameInfoList.value = data.map((item) => ({
        db_name: item,
        target_db_name: item,
        rename_db_name: '',
      }));
    },
  });

  watch(
    () => [props.clusterData, props.restoreTime, props.restoreBackupFile, dbName.value, dbIgnoreName.value],
    () => {
      if (!props.clusterData || dbName.value.length < 1 || (!props.restoreTime && !props.restoreBackupFile)) {
        return;
      }
      fetchSqlserverDbs({
        cluster_id: props.clusterData.id,
        db_pattern: dbName.value,
        ignore_db: dbIgnoreName.value,
        backup_logs: props.restoreBackupFile ? { logs: props.restoreBackupFile.logs } : undefined,
        restore_time: props.restoreTime,
      });
    },
    {
      immediate: true,
    },
  );

  const handleShowEditName = () => {
    isShowEditName.value = true;
  };

  const handleSubmit = () => {
    editNameRef.value!.submit().then((result) => {
      isShowEditName.value = false;
      hasEditDbName.value = true;
      dbName.value = result.dbName;
      dbIgnoreName.value = result.dbIgnoreName;
      localRenameInfoList.value = result.renameInfoList;
    });
  };

  const handleCancel = () => {
    isShowEditName.value = false;
  };

  defineExpose<Expose>({
    getValue() {
      return elementRef.value!.getValue().then(() => ({
        rename_infos: localRenameInfoList.value,
      }));
    },
  });
</script>
<style lang="less" scoped>
  .render-rename {
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
