<template>
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="batchCluster.renderText"
    fixed="left"
    :label="t('目标集群')"
    :loading="loading"
    :min-width="300"
    required>
    <template #headAppend>
      <BkButton
        text
        theme="primary"
        @click="handleBatchSelectorShow">
        <DbIcon type="batch-host-select" />
      </BkButton>
    </template>
    <EditableTextarea
      v-model="modelValue.renderText"
      :placeholder="t('请输入集群域名_多个集群用分隔符输入')"
      @change="handleInputChange">
      <template #append>
        <span v-bk-tooltips="t('选择实例')">
          <span
            class="batch-host-select"
            @click="handleCellSelectorShow">
            <DbIcon type="host-select" />
          </span>
        </span>
      </template>
    </EditableTextarea>
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="isBatchSelectorShow"
    :cluster-types="[ClusterTypes.REDIS]"
    :selected="batchSelectedClusters"
    :tab-list-config="tabListConfig"
    @change="handleBatchSelectChange" />
  <ClusterSelector
    v-model:is-show="isCellSelectorShow"
    :cluster-types="[ClusterTypes.REDIS]"
    :selected="cellSelectedClusters"
    :tab-list-config="tabListConfig"
    @change="handleCellClusterChange" />
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { batchSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      id: number;
      master_domain: string;
    }[];
    selectedMap: Record<string, boolean>;
    tabListConfig?: Record<string, TabConfig>;
  }

  type Emits = (e: 'batch-edit', value: RedisModel[]) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    clusters: Record<
      string,
      {
        bk_cloud_id: number;
        cluster_spec: RedisModel['cluster_spec'];
        cluster_type: string;
        id: number;
        major_version: string;
        master_domain: string;
        redis_master: RedisModel['redis_master'];
      }
    >;
    renderText: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const isBatchSelectorShow = ref(false);
  const isCellSelectorShow = ref(false);

  const batchSelectedClusters = computed<Record<string, RedisModel[]>>(() => ({
    [ClusterTypes.REDIS]: props.selected as RedisModel[],
  }));

  const cellSelectedClusters = computed<Record<string, RedisModel[]>>(() => ({
    [ClusterTypes.REDIS]: props.selected as RedisModel[],
  }));

  const selectedCounter = computed(() => _.countBy(props.selected, 'master_domain'));

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'blur',
      validator: (value: string) => !value || value.split(batchSplitRegex).every((item) => domainRegex.test(item)),
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        const repeats: string[] = [];
        const list = value.split(batchSplitRegex);
        list.forEach((domain, index) => {
          if (index !== list.indexOf(domain)) {
            repeats.push(domain);
          } else if (selectedCounter.value[domain] > 1) {
            repeats.push(domain);
          }
        });
        return repeats.length ? t('目标集群xx重复', [repeats.join(',')]) : true;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        const notFounds: string[] = [];
        value.split(batchSplitRegex).forEach((item) => {
          if (!props.selectedMap[item]) {
            notFounds.push(item);
          }
        });
        return notFounds.length ? t('目标集群xx不存在', [notFounds.join(',')]) : true;
      },
    },
  ];

  const { loading, run: queryCluster } = useRequest(filterClusters<RedisModel>, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        let clusters = {} as UnwrapRef<typeof modelValue>['clusters'];
        data.forEach((item) => {
          clusters = {
            ...clusters,
            [item.master_domain]: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_spec: item.cluster_spec,
              cluster_type: item.cluster_type,
              id: item.id,
              major_version: item.major_version,
              master_domain: item.master_domain,
              redis_master: item.redis_master,
            },
          };
        });
        modelValue.value.clusters = clusters;
      }
    },
  });

  watch(
    modelValue,
    () => {
      if (modelValue.value.renderText && _.isEmpty(modelValue.value.clusters)) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          // cluster_type: ClusterTypes.TENDBHA,
          db_type: DBTypes.REDIS,
          exact_domain: modelValue.value.renderText.split(batchSplitRegex).join(','),
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleBatchSelectorShow = () => {
    isBatchSelectorShow.value = true;
  };

  const handleCellSelectorShow = () => {
    isCellSelectorShow.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      clusters: {},
      renderText: value
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
        .join('\n'),
    };
  };

  const handleBatchSelectChange = (selected: Record<string, RedisModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };

  const handleCellClusterChange = (selected: Record<string, RedisModel[]>) => {
    const list = Object.values(selected).flatMap((selectedList) => selectedList);
    handleInputChange(list.map((item) => item.master_domain).join('\n'));
  };
</script>
