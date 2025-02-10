<template>
  <BkTableColumn
    class-name="cluster-table-role-column"
    :field="field"
    :label="label"
    :min-width="minWidth"
    :show-overflow="false">
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
        :is-filter="isFilter"
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
        <template
          v-if="slots.default"
          #default="{ data: instanceData }">
          <slot
            name="default"
            v-bind="{ data: instanceData as any }" />
        </template>
        <template #nodeTag="{ data: instanceData }">
          <slot
            name="nodeTag"
            v-bind="{
              data: instanceData as any,
            }" />
        </template>
        <template #instanceListTitle>
          <slot
            name="instanceListTitle"
            v-bind="{ data }" />
        </template>
        <template #instanceList>
          <slot
            name="instanceList"
            v-bind="{
              instanceList: getRoleInstanceList(data) as any,
              clusterData: data,
            }">
            <RenderInstanceList
              :data="getRoleInstanceList(data)"
              :role="String(field)" />
          </slot>
        </template>
      </CellContent>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType, F extends keyof ClusterModel<T>">
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

  export interface Props<clusterType extends ISupportClusterType, F extends keyof ClusterModel<clusterType>> {
    field: F;
    label: string;
    searchIp?: string[];
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: clusterType;
    selectedList: ClusterModel<clusterType>[];
    minWidth?: number;
    isFilter: boolean;
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  export type ReturnArrayElement<T> = T extends (infer U)[] ? U : T;

  export interface Slots<clusterType extends ISupportClusterType, F extends keyof ClusterModel<clusterType>> {
    default?: (params: { data: ReturnArrayElement<ClusterModel<clusterType>[F]> }) => void;
    nodeTag: (params: { data: ReturnArrayElement<ClusterModel<clusterType>[F]> }) => void;
    instanceListTitle: (params: { data: ClusterModel<clusterType> }) => VNode;
    instanceList: (params: {
      instanceList: ClusterModel<clusterType>[F];
      clusterData: ClusterModel<clusterType>;
    }) => VNode;
  }

  type IRowData = ClusterModel<T>;

  const props = withDefaults(defineProps<Props<T, F>>(), {
    searchIp: undefined,
    minWidth: 200,
  });
  const slots = defineSlots<Slots<T, F>>();

  const { t } = useI18n();

  const getCopyList = (data: ClusterModel<T>[], field: 'ip' | 'instance') =>
    _.uniq(
      data.reduce(
        (result, item) =>
          result.concat(
            (item[props.field as keyof typeof item] as ClusterListNode[]).map((nodeItem) => nodeItem[field]),
          ),
        [] as string[],
      ),
    );

  const getRoleInstanceList = (data: IRowData) => (_.get(data, props.field) || []) as ClusterListNode[];

  const handleHeadCopySelected = (field: 'ip' | 'instance') => {
    const copyList = getCopyList(props.selectedList, field);
    execCopy(copyList.join('\n'), t('复制成功，共n条', { n: copyList.length }));
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
        execCopy(copyList.join('\n'), t('复制成功，共n条', { n: copyList.length }));
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

    [class*=' db-icon'] {
      display: none;
      margin-top: 1px;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }
</style>
