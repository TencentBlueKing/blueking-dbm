<template>
  <BkTableColumn
    class-name="cluster-table-role-column"
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
        @handle-copy-all="handleHeadCopyAll"
        @handle-copy-selected="handleHeadCopySelected">
        {{ label }}
      </RenderHeadCopy>
    </template>
    <template #default="{ data }: { data: IRowData }">
      <CellContent
        :cluster-data="data"
        :data="getRoleInstanceList(data)"
        :field="field"
        :hightlight-key="searchIp"
        :label="label">
        <template #nodeTag="{ data: instanceData }">
          <slot
            name="nodeTag"
            v-bind="{ data: instanceData }" />
        </template>
        <template #instanceList>
          <slot
            name="instanceList"
            v-bind="{ instanceList: getRoleInstanceList(data), clusterData: data }">
            <RenderInstanceList
              :data="getRoleInstanceList(data)"
              :role="field" />
          </slot>
        </template>
      </CellContent>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { ClusterListNode } from '@services/types';

  import DbTable from '@components/db-table/index.vue';

  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  import type { ClusterModel, ISupportClusterType } from '../../types';

  import CellContent from './components/CellContent.vue';
  import RenderInstanceList from './components/InstanceList.vue';

  export interface Props<clusterType extends ISupportClusterType> {
    field: string;
    label: string;
    searchIp?: string[];
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: clusterType;
    selectedList: ClusterModel<clusterType>[];
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  export interface Slots<clusterType extends ISupportClusterType> {
    nodeTag: (params: { data: { ip: string; port: number; status: string } }) => VNode;
    instanceList: (params: { instanceList: ClusterListNode[]; clusterData: ClusterModel<clusterType> }) => VNode;
  }

  type IRowData = ClusterModel<T>;

  const props = defineProps<Props<T>>();
  defineSlots<Slots<T>>();

  const { t } = useI18n();

  const getCopyList = (data: ClusterModel<T>[], field: 'ip' | 'instance') =>
    data.reduce(
      (result, item) =>
        result.concat((item[props.field as keyof typeof item] as ClusterListNode[]).map((nodeItem) => nodeItem[field])),
      [] as string[],
    );

  const getRoleInstanceList = (data: IRowData) => (_.get(data, props.field) || []) as ClusterListNode[];

  const handleHeadCopySelected = (field: 'ip' | 'instance') => {
    const copyList = getCopyList(props.selectedList, field);

    execCopy(
      copyList.join('\n'),
      t('成功复制n个', {
        n: copyList.length,
      }),
    );
  };

  const handleHeadCopyAll = (field: 'ip' | 'instance') => {
    props
      .getTableInstance()!
      .getAllData<ClusterModel<T>>()
      .then((data) => {
        if (data.length < 1) {
          messageWarn(t('暂无数据可复制'));
          return;
        }
        const copyList = getCopyList(data, field);

        execCopy(
          copyList.join('\n'),
          t('成功复制n个', {
            n: copyList.length,
          }),
        );
      });
  };
</script>
<style lang="less">
  .cluster-table-role-column {
    &:hover {
      [class*=' db-icon'] {
        display: inline !important;
      }
    }
  }
</style>
