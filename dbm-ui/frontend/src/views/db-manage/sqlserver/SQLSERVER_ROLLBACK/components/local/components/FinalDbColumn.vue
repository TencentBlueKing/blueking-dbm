<template>
  <EditableColumn
    field="rename_infos"
    :label="t('构造后 DB 名')"
    :min-width="300"
    required
    :rules="rules">
    <BkLoading :loading="isLoading">
      <EditableBlock>
        <span
          v-bk-tooltips="{
            content: disabledTips,
            disabled: !Boolean(disabledTips),
          }"
          @click="handleShowEditName">
          <BkButton
            :disabled="Boolean(disabledTips)"
            text
            theme="primary">
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
        </span>
      </EditableBlock>
    </BkLoading>
  </EditableColumn>
  <BkSideslider
    v-model:is-show="isShowEditName"
    render-directive="if"
    :width="900">
    <template #header>
      <span>{{ t('手动修改回档的 DB 名') }}</span>
      <BkTag class="ml-8">{{ cluster.master_domain }}</BkTag>
    </template>
    <EditName
      v-if="cluster.id"
      ref="editNameRef"
      :cluster-id="cluster.id"
      :db-ignore-name="dbIgnoreName"
      :db-name="dbName"
      :rename-info-list="moduleValue"
      :target-cluster-id="cluster.id" />
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
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryBackupLogs, queryDbsByBackupLog } from '@services/source/sqlserver';

  import EditName from '@views/db-manage/sqlserver/common/edit-rename-info-new/Index.vue';

  interface Props {
    cluster: {
      id: number;
      master_domain: string;
    };
    restoreBackupFile?: ServiceReturnType<typeof queryBackupLogs>[number];
    restoreTime?: string;
  }

  const props = defineProps<Props>();

  const moduleValue = defineModel<
    {
      db_name: string;
      rename_db_name: string;
      target_db_name: string;
    }[]
  >({
    required: true,
  });

  const dbName = defineModel<string[]>('dbName', {
    required: true,
  });

  const dbIgnoreName = defineModel<string[]>('dbIgnoreName', {
    required: true,
  });

  const { t } = useI18n();

  const editNameRef = ref<InstanceType<typeof EditName>>();
  const isShowEditName = ref(false);
  const hasEditDbName = ref(false);

  const disabledTips = computed(() => {
    if (props.cluster.id && dbName.value.length > 0 && (props.restoreBackupFile || props.restoreTime)) {
      return '';
    }
    return t('请先设置集群、构造 DB、回档信息');
  });

  const rules = [
    {
      message: t('构造后 DB 名不能为空'),
      required: true,
      trigger: 'change',
      validator: () => moduleValue.value.length > 0,
    },
    {
      message: t('构造后 DB 名待有冲突更新'),
      trigger: 'change',
      validator: () => hasEditDbName.value,
    },
  ];

  const { loading: isLoading, run: fetchSqlserverDbs } = useRequest(queryDbsByBackupLog, {
    manual: true,
    onSuccess(data) {
      moduleValue.value = data.map((item) => ({
        db_name: item,
        rename_db_name: '',
        target_db_name: item,
      }));
      hasEditDbName.value = false;
    },
  });

  watch(
    () => [props.cluster.id, props.restoreTime, props.restoreBackupFile, dbName.value, dbIgnoreName.value],
    () => {
      if (!props.cluster.id || dbName.value.length < 1 || (!props.restoreTime && !props.restoreBackupFile)) {
        return;
      }
      fetchSqlserverDbs({
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

  const handleShowEditName = () => {
    if (disabledTips.value) {
      return;
    }
    isShowEditName.value = true;
  };

  const handleSubmit = () => {
    editNameRef.value!.submit().then((result) => {
      isShowEditName.value = false;
      hasEditDbName.value = true;
      dbName.value = result.dbName;
      dbIgnoreName.value = result.dbIgnoreName;
      moduleValue.value = result.renameInfoList;
    });
  };

  const handleCancel = () => {
    isShowEditName.value = false;
  };
</script>

<style lang="less" scoped>
  .render-rename {
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
