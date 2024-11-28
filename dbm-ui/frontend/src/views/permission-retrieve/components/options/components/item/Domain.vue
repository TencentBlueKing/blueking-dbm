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
  import { filterClusters } from '@services/source/dbbase';
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

  interface Emits {
    (e: 'change'): void;
  }

  interface Expose {
    reset: () => void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });
  const clusterType = defineModel<ClusterTypes>('clusterType', {
    required: true,
  });
  const isMaster = defineModel<boolean>('isMaster', {
    required: true,
  });

  const { t } = useI18n();

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

    emits('change');
  };

  const getDomainDiffInfo = (
    oldDomains: string[],
    newDomains: string[],
  ): {
    added?: string[];
    deleted?: string[];
    unchanged?: string[];
  } => {
    // 使用 Set 提高性能
    const oldSet = new Set(oldDomains);
    const newSet = new Set(newDomains);

    // 初始化结果数组
    const result: { domain: string; status: 'added' | 'deleted' | 'unchanged' }[] = [];

    // 遍历新域名集合，检查每个域名的状态
    for (const domain of newSet) {
      if (oldSet.has(domain)) {
        result.push({ domain, status: 'unchanged' });
      } else {
        result.push({ domain, status: 'added' });
      }
    }

    // 遍历旧域名集合，检查每个域名的状态
    for (const domain of oldSet) {
      if (!newSet.has(domain)) {
        result.push({ domain, status: 'deleted' });
      }
    }

    // 按状态分类结果
    const classifiedResult = result.reduce<Record<string, string[]>>((acc, item) => {
      if (!acc[item.status]) {
        acc[item.status] = [];
      }
      acc[item.status].push(item.domain);
      return acc;
    }, {});

    // 输出分类结果
    return classifiedResult;
  };

  const handleDomainChange = (value: string) => {
    // 减少或增加，需要与选择器联动
    const newDomainList = value.split(batchSplitRegex).filter((item) => item);
    const newValidDomainList = newDomainList.filter((item) => domainRegex.test(item));
    const selectDomainList = Object.values(selectedClusters.value).flatMap((item) => item);

    const diffResult = getDomainDiffInfo(
      selectDomainList.map((item) => item.master_domain),
      newValidDomainList,
    );

    const addList = diffResult.added || [];
    const deleteList = diffResult.deleted || [];
    const deleteSet = new Set(deleteList);

    if (addList.length) {
      filterClusters({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        exact_domain: addList.join(','),
      }).then((clusterResultList) => {
        // 删除时，删去已选集群
        deleteSelectedCluster(deleteSet);

        // 新增时，查询集群信息，同步已选集群
        const selected = selectedClusters.value;
        clusterResultList.forEach((clusterItem) => {
          selected[clusterItem.cluster_type] = selected[clusterItem.cluster_type].concat(clusterItem);
        });
        selectedClusters.value = selected;

        const clusterList = Object.values(selected).find((clusterList) => clusterList.length > 0);
        clusterType.value = (clusterList?.[0].cluster_type || ClusterTypes.TENDBSINGLE) as ClusterTypes;
        isMaster.value = !selectedClusters.value?.tendbhaSlave?.length;

        nextTick(() => {
          emits('change');
        });
      });
    } else {
      // 删除时，删去已选集群
      deleteSelectedCluster(deleteSet);

      emits('change');
    }
  };

  const deleteSelectedCluster = (deleteSet: Set<string>) => {
    if (deleteSet.size) {
      Object.keys(selectedClusters.value).forEach((key) => {
        const clusterList = selectedClusters.value[key];
        selectedClusters.value[key] = clusterList.filter((clusterItem) => !deleteSet.has(clusterItem.master_domain));
      });
    }
  };

  defineExpose<Expose>({
    reset() {
      selectedClusters.value = getDefaultSelectedClusters();
    },
  });
</script>
