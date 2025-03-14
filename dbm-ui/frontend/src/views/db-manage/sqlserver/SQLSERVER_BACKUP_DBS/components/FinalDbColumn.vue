<template>
  <EditableColumn
    :append-rules="rules"
    field="backup_dbs"
    :label="t('最终 DB')"
    :min-width="300"
    required>
    <BkLoading :loading="isLoading">
      <EditableBlock>
        <BkButton
          :disabled="Boolean(disabledTips)"
          text
          theme="primary"
          @click="handleShowEditName">
          {{ modelValue.length < 1 ? '--' : modelValue.length }}
        </BkButton>
      </EditableBlock>
    </BkLoading>
  </EditableColumn>
  <BkSideslider
    v-model:is-show="isShowEditName"
    class="sqlserver-manage-db-backup-fianal-db"
    :width="900">
    <template #header>
      <span>{{ t('预览 DB 结果列表') }}</span>
      <BkTag class="ml-8">{{ cluster.master_domain }}</BkTag>
    </template>
    <BkLoading :loading="isLoading">
      <EditableTable :model="model">
        <EditableRow>
          <DbNameColumn
            v-model="dbList"
            check-not-exist
            :cluster-id="cluster.id"
            field="db_list"
            :label="t('指定 DB 名')"
            :show-batch-edit="false" />
          <DbNameColumn
            v-model="ignoreDbList"
            :allow-asterisk="false"
            field="ignore_db_list"
            :label="t('忽略 DB 名')"
            :required="false"
            :show-batch-edit="false" />
        </EditableRow>
      </EditableTable>
      <div class="mt-24">
        <span style="font-weight: bold; color: #313238">{{ t('最终 DB') }}</span>
        <I18nT keypath="(共 n 个)">
          <span>{{ modelValue.length }}</span>
        </I18nT>
      </div>
      <div class="db-wrapper">
        <div
          v-for="(tagItem, index) in modelValue"
          :key="index">
          {{ tagItem }}
        </div>
      </div>
    </BkLoading>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSqlserverDbs } from '@services/source/sqlserver';

  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';

  import { makeMap } from '@utils';

  interface Props {
    cluster: {
      id: number;
      master_domain?: string;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    required: true,
  });
  const dbList = defineModel<string[]>('dbList', {
    required: true,
  });
  const ignoreDbList = defineModel<string[]>('ignoreDbList', {
    required: true,
  });

  const { t } = useI18n();

  const isShowEditName = ref(false);

  const rules = [
    {
      message: t('最终 DB 和指定的备份 DB 数量不匹配'),
      validator: () => {
        const ignoreDbListMap = makeMap(ignoreDbList.value);
        const cleanDbsPatternList = dbList.value.filter(
          (item) => !/\*/.test(item) && !/%/.test(item) && !ignoreDbListMap[item],
        );
        return cleanDbsPatternList.length <= modelValue.value.length;
      },
    },
  ];

  const disabledTips = computed(() => {
    if (props.cluster.id && dbList.value.length > 0) {
      return '';
    }
    return t('请先设置目标集群、备份 DB');
  });

  const model = computed(() => {
    return [
      {
        db_list: dbList.value,
        ignore_db_list: ignoreDbList.value,
      },
    ];
  });

  const { loading: isLoading, run: fetchSqlserverDbs } = useRequest(getSqlserverDbs, {
    manual: true,
    onSuccess(data) {
      modelValue.value = data;
    },
  });

  watch(
    () => [props.cluster.id, dbList.value, ignoreDbList.value],
    () => {
      if (!props.cluster.id || dbList.value.length < 1) {
        modelValue.value = [];
        return;
      }
      fetchSqlserverDbs({
        cluster_id: props.cluster.id,
        db_list: dbList.value,
        ignore_db_list: ignoreDbList.value,
      });
    },
    {
      immediate: true,
    },
  );

  const handleShowEditName = () => {
    isShowEditName.value = true;
  };
</script>

<style lang="less">
  .sqlserver-manage-db-backup-fianal-db {
    .bk-sideslider-content {
      padding: 20px 24px 0;
    }

    .db-wrapper {
      padding: 16px;
      margin-top: 16px;
      background: #f5f7fa;
      border-radius: 2px;
    }
  }
</style>
