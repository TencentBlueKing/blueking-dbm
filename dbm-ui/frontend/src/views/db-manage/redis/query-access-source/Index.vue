<template>
  <div class="query-access-source-main-page">
    <BkAlert
      closable
      theme="info"
      :title="t('查询集群具体的访问信息')" />
    <BkForm
      ref="formRef"
      class="web-query-form"
      form-type="vertical"
      :model="formData"
      :rules="rules"
      @validate="handleFormValidate">
      <BkFormItem
        :label="t('查询集群')"
        property="clusters"
        required>
        <div class="query-cluster-main">
          <BkInput
            v-model="formData.clusters"
            :autosize="autoSizeConf"
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
      <div class="query-opeartion-main">
        <BkButton
          class="w-88"
          :disabled="!queryAvailable"
          :loading="queryLoading"
          theme="primary"
          @click="handleQuery">
          {{ t('查询') }}
        </BkButton>
        <DbPopconfirm
          :confirm-handler="handleReset"
          :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
          :title="t('确认重置页面')">
          <BkButton
            class="w-88 ml-8"
            :disabled="!formData.clusters"
            outline>
            {{ t('重置') }}
          </BkButton>
        </DbPopconfirm>
      </div>
      <BkFormItem :label="t('查询结果')">
        <Result
          ref="resultRef"
          :clusters="clusterList"
          @finish="handleQueryFinish" />
      </BkFormItem>
    </BkForm>
  </div>
  <ClusterSelector
    v-model:is-show="isShowSelector"
    :cluster-types="[ClusterTypes.REDIS]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handelClusterChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { filterClusters } from '@services/source/dbbase';
  import { getRedisList } from '@services/source/redis';

  import { ClusterTypes } from '@common/const';
  import { batchInputSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  import Result from './components/Result.vue';

  type RedisModel = ServiceReturnType<typeof getRedisList>['results'][number];

  const { t } = useI18n();
  const route = useRoute();

  const resultRef = ref<InstanceType<typeof Result>>();
  const isShowSelector = ref(false);
  const formRef = ref();
  const formData = ref({
    clusters: (route.query.domain as string) || '',
  });
  const queryAvailable = ref(false);
  const queryLoading = ref(false);
  const clusterList = ref<
    {
      domain: string;
      id: number;
    }[]
  >([]);

  const selectedClusters = shallowRef<{ [key: string]: Array<RedisModel> }>({ [ClusterTypes.REDIS]: [] });

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
          ].join(','),
          ...params,
        }),
    } as unknown as TabConfig,
  };

  const autoSizeConf = {
    maxRows: 22,
    minRows: 5,
  };

  const rules = {
    clusters: [
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
            if (item.db_type === 'redis') {
              dataSet.add(item.master_domain);
            }
            return dataSet;
          }, new Set());
          const invalidClusters = clusterList.filter((item) => !validClustersSet.has(item));
          return !invalidClusters.length || t('无效集群：m', { m: invalidClusters.join(' , ') });
        },
      },
    ],
  };

  watch(selectedClusters, () => {
    const selectedClusterList = selectedClusters.value[ClusterTypes.REDIS].map((item) => item.master_domain);
    const inputedClusterList = formData.value.clusters.split(batchInputSplitRegex);
    const newList = _.difference(selectedClusterList, inputedClusterList);
    const handledInput = formData.value.clusters.trim();
    const existedInput = handledInput.length > 0 ? `${handledInput}\n` : '';
    formData.value.clusters = existedInput + newList.join('\n');
  });

  const handelClusterChange = (selected: { [key: string]: Array<RedisModel> }) => {
    selectedClusters.value = selected;
  };

  const handleQuery = async () => {
    queryLoading.value = true;
    await formRef.value.validate();
    const domains = formData.value.clusters.trim().split(batchInputSplitRegex);
    const domainInfoList = await filterClusters({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      domain: domains.join(','),
    });
    clusterList.value = domainInfoList.map((item) => ({
      domain: item.master_domain,
      id: item.id,
    }));
  };

  const handleQueryFinish = () => {
    queryLoading.value = false;
  };

  const handleReset = () => {
    formData.value.clusters = '';
    resultRef.value!.reset();
  };

  const handleFormValidate = (_: unknown, isValid: boolean) => {
    queryAvailable.value = isValid;
  };

  onMounted(() => {
    if (route.query.domain) {
      formRef.value.validate();
    }
  });
</script>
<style lang="less">
  .query-access-source-main-page {
    height: 100%;

    .web-query-form {
      margin-top: 16px;

      .bk-form-label {
        font-weight: 700;
      }

      .query-cluster-main {
        position: relative;
        display: flex;
      }

      .query-opeartion-main {
        display: flex;
        margin-bottom: 24px;
      }
    }
  }
</style>
