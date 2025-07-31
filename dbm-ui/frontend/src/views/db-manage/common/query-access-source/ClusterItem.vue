<template>
  <BkFormItem
    :label="t('查询集群')"
    property="clusters"
    required
    :rules="rules">
    <div class="query-access-source-cluster-item">
      <BkInput
        v-model="modleValue"
        :autosize="{
          maxRows: 22,
          minRows: 5,
        }"
        clearable
        :placeholder="t('请输入查询集群或从拓扑选择，多个逗号或换行分隔')"
        :resize="false"
        style="width: 750px"
        type="textarea" />
      <BkButton
        class="ml-8"
        @click="() => (isShowSelector = true)">
        <DbIcon
          style="margin-right: 6px; color: #979ba5"
          type="add" />
        {{ t('选择集群') }}
      </BkButton>
    </div>
  </BkFormItem>
  <ClusterSelector
    v-model:is-show="isShowSelector"
    :cluster-types="clusterTypes[dbType]"
    :selected="selectedClusters"
    @change="handelClusterChange" />
</template>

<script lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import RedisModel from '@services/model/redis/redis';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { batchInputSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface ClusterModelMap {
    [DBTypes.MONGODB]: MongodbModel;
    [DBTypes.REDIS]: RedisModel;
  }
</script>
<script setup lang="ts" generic="T extends keyof ClusterModelMap">
  export interface Props<IDbType extends keyof ClusterModelMap> {
    dbType: IDbType;
  }

  const props = defineProps<Props<T>>();

  const modleValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const clusterTypes: Record<keyof ClusterModelMap, ClusterTypes[]> = {
    [DBTypes.MONGODB]: [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER],
    [DBTypes.REDIS]: [ClusterTypes.REDIS],
  };

  const isShowSelector = ref(false);

  const selectedClusters = shallowRef<{ [key: string]: Array<ClusterModelMap[T]> }>(
    Object.fromEntries(clusterTypes[props.dbType].map((type) => [type, []])),
  );

  const rules = [
    {
      trigger: 'blur',
      validator: (value: string) => !!value || t('不能为空'),
    },
    {
      trigger: 'blur',
      validator: (value: string) => {
        const inputValue = value.trim();
        const clusterList = inputValue.split(batchInputSplitRegex);
        const formatErrorList = clusterList.reduce<string[]>((results, item) => {
          if (!domainRegex.test(item)) {
            results.push(item);
          }
          return results;
        }, []);
        return !formatErrorList.length || t('格式错误：m', { m: formatErrorList.join(' , ') });
      },
    },
    {
      trigger: 'blur',
      validator: async (value: string) => {
        const inputValue = value.trim();
        const clusterList = inputValue.split(batchInputSplitRegex);
        const clusterInfoList = await filterClusters({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          domain: clusterList.join(','),
        });
        const validClustersSet = clusterInfoList.reduce<Set<string>>((dataSet, item) => {
          if (item.db_type === props.dbType) {
            dataSet.add(item.master_domain);
          }
          return dataSet;
        }, new Set());
        const invalidClusters = clusterList.filter((item) => !validClustersSet.has(item));
        return !invalidClusters.length || t('无效集群：m', { m: invalidClusters.join(' , ') });
      },
    },
  ];

  watch(selectedClusters, () => {
    const selectedClusterList = Object.values(selectedClusters.value).flatMap((selectedItem) =>
      selectedItem.map((item) => item.master_domain),
    );
    const inputedClusterList = modleValue.value.split(batchInputSplitRegex);
    const newList = _.difference(selectedClusterList, inputedClusterList);
    const handledInput = modleValue.value.trim();
    const existedInput = handledInput.length > 0 ? `${handledInput}\n` : '';
    modleValue.value = existedInput + newList.join('\n');
  });

  const handelClusterChange = (selected: { [key: string]: Array<ClusterModelMap[T]> }) => {
    selectedClusters.value = selected;
  };
</script>

<style lang="less">
  .query-access-source-cluster-item {
    position: relative;
    display: flex;

    .bk-textarea {
      flex-direction: row;

      .bk-textarea--clear-icon {
        margin: 0;
      }
    }
  }
</style>
