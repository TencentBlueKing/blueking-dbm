<template>
  <BkFormItem
    :label="t('域名')"
    property="immute_domains"
    required
    :rules="rules">
    <BatchInput
      v-model="modelValue"
      icon-type="host-select"
      :max-count="20"
      @change="handleDomainChange"
      @icon-click="() => (clusterSelectorShow = true)" />
  </BkFormItem>
  <ClusterSelector
    v-model:is-show="clusterSelectorShow"
    :cluster-types="accoutMap[accountType as keyof typeof accoutMap].clusterSelectorTypes"
    :disable-dialog-submit-method="disableClusterSubmitMethod"
    only-one-type
    :selected="selectedClusters"
    :tab-list-config="clusterTabListConfig"
    @change="handleClusterSelectorChange">
    <template #submitTips="{ clusterList: resultClusterList }">
      <I18nT
        keypath="至多n台_已选n台"
        style="font-size: 14px; color: #63656e"
        tag="span">
        <span
          class="number"
          style="color: #2dcb56">
          20
        </span>
        <span
          class="number"
          style="color: #3a84ff">
          {{ resultClusterList.length }}
        </span>
      </I18nT>
    </template>
  </ClusterSelector>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import SpiderModel from '@services/model/tendbcluster/tendbcluster';
  import { getTendbhaList, getTendbhaSalveList } from '@services/source/tendbha';

  import { AccountTypes, ClusterTypes } from '@common/const';
  import { batchSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  import accoutMap from '../../components/common/config';

  import BatchInput from './components/BatchInput.vue';

  type SelectorModelType = TendbhaModel | TendbsingleModel | SpiderModel;

  interface Props {
    accountType: AccountTypes;
  }

  interface Expose {
    reset: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const modelValue = defineModel<string>({
    required: true,
  });
  const clusterType = defineModel<ClusterTypes>('clusterType', {
    required: true,
  });
  const isMaster = defineModel<boolean>('isMaster', {
    required: true,
  });

  const getDefaultSelectedClusters = () =>
    accoutMap[props.accountType as keyof typeof accoutMap].clusterSelectorTypes.reduce(
      (prevMap, type) => Object.assign({}, prevMap, { [type]: [] }),
      {},
    );

  const clusterTabListConfig = {
    tendbhaSlave: {
      name: t('高可用-从域名'),
      showPreviewResultTitle: true,
      getResourceList: (params: ServiceParameters<typeof getTendbhaSalveList>) => {
        params.slave_domain = params.domain;
        delete params.domain;
        return getTendbhaSalveList(params);
      },
    },
    [ClusterTypes.TENDBHA]: {
      name: t('高可用-主域名'),
      showPreviewResultTitle: true,
      getResourceList: (params: ServiceParameters<typeof getTendbhaList>) => {
        params.master_domain = params.domain;
        delete params.domain;
        return getTendbhaList(params);
      },
    },
  } as unknown as Record<string, TabConfig>;

  const rules = [
    {
      required: true,
      message: t('域名不能为空'),
      validator: (value: string) => value !== '',
    },
    {
      message: t('格式错误'),
      validator: (value: string) => {
        const domainList = value.split(batchSplitRegex);
        return domainList.every((domain) => domainRegex.test(domain));
      },
    },
    {
      message: t('最多输入n个', { n: 20 }),
      validator: (value: string) => {
        const ipList = value.split(batchSplitRegex);
        return ipList.length <= 20;
      },
    },
  ];

  const clusterSelectorShow = ref(false);

  const selectedClusters = shallowRef<{ [key: string]: Array<SelectorModelType> }>(getDefaultSelectedClusters());

  const disableClusterSubmitMethod = (clusterList: string[]) =>
    clusterList.length <= 20 ? false : t('至多n台', { n: 20 });

  const handleClusterSelectorChange = (selected: Record<string, Array<SelectorModelType>>) => {
    selectedClusters.value = selected;
    const domainList = Object.keys(selected).reduce<string[]>(
      (prevList, key) => prevList.concat(selected[key].map((item) => item.master_domain)),
      [],
    );
    modelValue.value = domainList.join(',');

    const clusterList = Object.values(selected).find((clusterList) => clusterList.length > 0);
    clusterType.value = (clusterList?.[0].cluster_type || ClusterTypes.TENDBSINGLE) as ClusterTypes;
    isMaster.value = !selectedClusters.value?.tendbhaSlave?.length;
  };

  const handleDomainChange = (value: string) => {
    const newDomainList = value.split(batchSplitRegex).filter((item) => item);
    const domainSet = new Set(newDomainList);
    Object.keys(selectedClusters.value).forEach((key) => {
      const clusterList = selectedClusters.value[key];
      selectedClusters.value[key] = clusterList.filter((clusterItem) => domainSet.has(clusterItem.master_domain));
    });
  };

  defineExpose<Expose>({
    reset() {
      selectedClusters.value = getDefaultSelectedClusters();
    },
  });
</script>
