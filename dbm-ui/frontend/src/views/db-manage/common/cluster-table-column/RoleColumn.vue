<template>
  <BkTableColumn
    :field="field"
    :label="label"
    :min-width="200">
    <template #header>
      <RenderHeadCopy
        :config="[
          {
            label: 'IP',
            field: 'ip',
          },
          {
            label: t('实例'),
            field: 'instance',
          },
        ]"
        :has-selected="selectedList.length > 0"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ label }}
      </RenderHeadCopy>
    </template>
    <template #default="{ data }: { data: TendnclusterModel }">
      <!-- prettier-ignore -->
      <RenderInstances
        :cluster-id="data.id"
        :data="(data[field as keyof typeof data] as ClusterListNode[])"
        :data-source="dataSource"
        :highlight-ips="searchIp"
        :role="field"
        :title="
          t('【inst】实例预览', {
            inst: data.master_domain,
            title: label,
          })
        ">
        <template #append="instanceData">
          <slot
            name="nodeTag"
            v-bind="instanceData.data" />
        </template>
      </RenderInstances>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import TendnclusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getTendbclusterInstanceList } from '@services/source/tendbcluster';
  import type { ClusterListNode } from '@services/types';

  import DbTable from '@components/db-table/index.vue';

  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';
  import RenderInstances from '@views/db-manage/common/render-instances/RenderInstances.vue';

  import { execCopy, messageWarn } from '@utils';

  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    field: string;
    label: string;
    searchIp?: string[];
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: clusterType;
    selectedList: ClusterModel<clusterType>[];
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  export interface Slots {
    nodeTag: (params: { ip: string; port: number; status: string }) => void;
  }

  const props = defineProps<Props<T>>();
  defineSlots<Slots>();

  const { t } = useI18n();

  const dataSource = getTendbclusterInstanceList;

  const getCopyList = (data: ClusterModel<T>[], field: 'ip' | 'instance') =>
    data.reduce(
      (result, item) =>
        result.concat((item[props.field as keyof typeof item] as ClusterListNode[]).map((nodeItem) => nodeItem[field])),
      [] as string[],
    );

  const handleCopySelected = (field: 'ip' | 'instance') => {
    const copyList = getCopyList(props.selectedList, field);

    execCopy(copyList.join('\n'));
  };

  const handleCopyAll = (field: 'ip' | 'instance') => {
    props
      .getTableInstance()!
      .getAllData<ClusterModel<T>>()
      .then((data) => {
        if (data.length < 1) {
          messageWarn(t('暂无数据可复制'));
          return;
        }
        const copyList = getCopyList(data, field);

        execCopy(copyList.join('\n'));
      });
  };
</script>
