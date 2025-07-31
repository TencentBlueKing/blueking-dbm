<template>
  <div class="mongodb-query-access-source-main-page">
    <BkAlert
      closable
      theme="info"
      :title="t('查询集群具体的访问信息')" />
    <BkForm
      ref="formRef"
      class="web-query-form toolbox-form"
      form-type="vertical"
      :model="formData"
      @validate="handleFormValidate">
      <ClusterItem
        v-model="formData.clusters"
        :db-type="DBTypes.MONGODB" />
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
      <ResultItem
        ref="resultRef"
        :clusters="clusterList"
        :db-type="DBTypes.MONGODB"
        @finish="handleQueryFinish" />
    </BkForm>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { filterClusters } from '@services/source/dbbase';

  import { DBTypes } from '@common/const';
  import { batchInputSplitRegex } from '@common/regex';

  import ClusterItem from '@views/db-manage/common/query-access-source/ClusterItem.vue';
  import ResultItem from '@views/db-manage/common/query-access-source/result-item/Index.vue';

  const { t } = useI18n();
  const route = useRoute();

  const formRef = useTemplateRef('formRef');
  const resultRef = useTemplateRef('resultRef');

  const queryAvailable = ref(false);
  const queryLoading = ref(false);

  const clusterList = shallowRef<
    {
      domain: string;
      id: number;
    }[]
  >([]);

  const formData = reactive({
    clusters: (route.query.masterDomain as string) || '',
  });

  const handleQuery = async () => {
    queryLoading.value = true;
    await formRef.value!.validate();
    const domains = formData.clusters.trim().split(batchInputSplitRegex);
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
    formData.clusters = '';
    resultRef.value!.reset();
  };

  const handleFormValidate = (_: unknown, isValid: boolean) => {
    queryAvailable.value = isValid;
  };

  onMounted(() => {
    if (route.query.masterDomain) {
      formRef.value!.validate();
    }
  });
</script>

<style lang="less">
  .mongodb-query-access-source-main-page {
    height: 100%;

    .web-query-form {
      margin-top: 16px;

      .query-opeartion-main {
        display: flex;
        margin-bottom: 24px;
      }
    }
  }
</style>
