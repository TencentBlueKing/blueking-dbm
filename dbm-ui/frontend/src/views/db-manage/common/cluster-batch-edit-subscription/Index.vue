<template>
  <BkDialog
    class="batch-edit-alarm-subscription-dialog"
    :close-icon="false"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    :width="912">
    <BkResizeLayout
      :border="false"
      collapsible
      :initial-divide="365"
      :min="365"
      placement="right"
      style="height: 100%">
      <template #aside>
        <DomainList
          v-model="domainMapList"
          :show-update="showUpdate" />
      </template>
      <template #main>
        <EditContent
          ref="editContentRef"
          :cluster-types="clusterTypes"
          :metrics-map="metricsMap"
          :show-update="showUpdate" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <BkButton
        :disabled="isEmpty"
        :loading="saveLoading"
        style="width: 88px"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml-8"
        style="width: 88px"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { saveSubscribe } from '@services/source/monitorSubscribe';

  import { useAlarmSubscribe } from '@stores';

  import { messageSuccess } from '@utils';

  import EditContent from './components/content/Index.vue';
  import DomainList, { type DomainInfo } from './components/domain-list/Index.vue';

  interface Props {
    selected?: {
      cluster_type: string;
      master_domain: string;
    }[];
    showUpdate?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    selected: () => [],
    showUpdate: true,
  });

  const isShow = defineModel<boolean>('isShow', { default: false });

  const { t } = useI18n();
  const { initSubscribedDomainInfo, metricsMap, subscribedDomainInfo } = useAlarmSubscribe();

  const editContentRef = ref<InstanceType<typeof EditContent>>();
  const domainMapList = ref<Record<string, DomainInfo[]>>({});

  const clusterTypes = computed(() => [...new Set(props.selected.map((item) => item.cluster_type))]);

  const isEmpty = computed(() => !Object.values(domainMapList.value).flat().length);

  const { loading: saveLoading, run: runSaveSubscribe } = useRequest(saveSubscribe, {
    manual: true,
    onSuccess: () => {
      messageSuccess('保存成功');
      initSubscribedDomainInfo();
      editContentRef.value!.reset();
      isShow.value = false;
    },
  });

  watch(
    () => [isShow.value, props.selected],
    () => {
      if (isShow.value) {
        domainMapList.value = props.selected.reduce<
          Record<
            string,
            {
              clusterDomian: string;
              clusterType: string;
              isIgnore: boolean;
              isNew: boolean;
            }[]
          >
        >((dataMap, item) => {
          const displayName = metricsMap[item.cluster_type]?.displayName;
          if (!dataMap[displayName]) {
            Object.assign(dataMap, { [displayName]: [] });
          }
          dataMap[displayName].push({
            clusterDomian: item.master_domain,
            clusterType: item.cluster_type,
            isIgnore: !metricsMap[item.cluster_type].list.length,
            isNew: !subscribedDomainInfo.dataSet.has(item.master_domain),
          });
          return dataMap;
        }, {});
      }
    },
    {
      immediate: true,
    },
  );

  const handleConfirm = () => {
    const contentData = editContentRef.value!.getData();
    const domainList = Object.values(domainMapList.value).flat();
    const params = {
      ...contentData,
      clusters: domainList.map((item) => ({
        cluster_domain: item.clusterDomian,
        cluster_type: item.clusterType,
      })),
    };
    runSaveSubscribe(params);
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .batch-edit-alarm-subscription-dialog {
    .bk-modal-header {
      display: none;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }
  }
</style>
