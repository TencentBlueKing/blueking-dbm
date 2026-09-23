<template>
  <div class="cluster-tag-list-box">
    <span v-if="!totalList.length">--</span>
    <template v-else>
      <div
        v-if="isVertical"
        class="list-display-main">
        <TextOverflowLayout
          v-for="(item, index) in renderList"
          :key="index">
          {{ item.key }} : {{ item.value.join(' , ') }}
          <template
            v-if="index === 0"
            #append>
            <AuthButton
              :action-id="actionId"
              class="edit-main"
              :permission="permission"
              :resource="data.id"
              text
              theme="primary"
              @click="handleOpenAddTag">
              <DbIcon type="edit" />
            </AuthButton>
          </template>
        </TextOverflowLayout>
        <template v-if="isShowMore">
          <BkButton
            v-bk-tooltips="tooltip"
            text
            theme="primary">
            {{ t('共n个', [totalList.length]) }}
          </BkButton>
        </template>
      </div>
      <div
        v-else
        class="list-display-main">
        <TagBlock :data="horizontalTagList" />
      </div>
    </template>
    <AuthButton
      v-if="!isVertical || (isVertical && !totalList.length)"
      :action-id="actionId"
      class="edit-main"
      :permission="permission"
      :resource="data.id"
      text
      theme="primary"
      @click="handleOpenAddTag">
      <DbIcon type="edit" />
    </AuthButton>
  </div>
  <ClusterAddTag
    v-model:is-show="isShowAddTag"
    :bk-biz-id="data.bk_biz_id"
    :cluster-id="data.id"
    :data="data.availableTags"
    :domain="data.masterDomain"
    :is-public="data.is_public"
    @success="handleOperateSuccess" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ClusterCommonInfo } from '@services/types';

  import { DBTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAddTag from './components/AddTag.vue';

  interface Props {
    data: { permission: Record<string, boolean> } & ClusterCommonInfo;
    mode?: 'horizontal' | 'vertical';
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    mode: 'horizontal',
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const renderInstanceCount = 6;

  // 数据库类型对应的编辑权限 actionId
  const editActionIdMap: Record<DBTypes, string> = {
    [DBTypes.DORIS]: 'doris_edit',
    [DBTypes.ES]: 'es_edit',
    [DBTypes.HDFS]: 'hdfs_edit',
    [DBTypes.INFLUXDB]: 'influxdb_edit',
    [DBTypes.K8S_QDRANT]: 'k8s_qdrant_edit',
    [DBTypes.K8S_SURREALDB]: 'k8s_surrealdb_edit',
    [DBTypes.KAFKA]: 'kafka_edit',
    [DBTypes.MONGODB]: 'mongodb_edit',
    [DBTypes.MYSQL]: 'mysql_edit',
    [DBTypes.ORACLE]: 'oracle_edit',
    [DBTypes.PULSAR]: 'pulsar_edit',
    [DBTypes.REDIS]: 'redis_edit',
    [DBTypes.RIAK]: 'riak_edit',
    [DBTypes.SQLSERVER]: 'sqlserver_edit',
    [DBTypes.TENDBCLUSTER]: 'tendbcluster_edit',
  };

  const isShowAddTag = ref(false);

  const isVertical = computed(() => props.mode === 'vertical');

  const totalList = computed(() =>
    props.data.availableTags.map((item) => ({
      key: item.key,
      value: [item.value],
    })),
  );
  const renderList = computed(() => totalList.value.slice(0, renderInstanceCount));
  const isShowMore = computed(() => totalList.value.length > renderInstanceCount);
  const tooltip = computed(() => totalList.value.map((item) => `${item.key}: ${item.value.join(',')}`).join('\n'));
  const actionId = computed(() => editActionIdMap[props.data.db_type as DBTypes]);
  const permission = computed(() => props.data.permission[actionId.value]);
  const horizontalTagList = computed(() => renderList.value.map((item) => `${item.key} : ${item.value.join(' , ')}`));

  const handleOperateSuccess = () => {
    emits('success');
  };

  const handleOpenAddTag = () => {
    isShowAddTag.value = true;
  };
</script>

<style lang="less">
  .cluster-tag-list-box {
    display: flex;
    align-items: center;

    &:hover {
      .edit-main {
        display: block;
      }
    }

    .empty-main {
      display: flex;
      align-items: center;
    }

    .list-display-main {
      flex: 1;
      overflow: hidden;
    }

    .edit-main {
      display: none;
      margin-left: 8px;
    }
  }
</style>
