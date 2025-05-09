<template>
  <BkTableColumn
    class-name="cluster-table-slave-domain-column"
    field="slave_domain"
    :label="t('从访问入口')"
    :min-width="280"
    :show-overflow="false"
    visiable>
    <template #header>
      <RenderHeadCopy
        :config="[
          {
            field: 'domain',
            label: t('域名'),
          },
          {
            field: 'instance',
            label: t('域名:端口'),
          },
        ]"
        :has-selected="selectedList.length > 0"
        :is-filter="isFilter"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ t('从访问入口') }}
      </RenderHeadCopy>
    </template>
    <template #default="{ data }: { data: IRowData }">
      <SlaveDomainCell :data="data" />
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import DbTable from '@components/db-table/index.vue';

  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import SlaveDomainCell, {
    copyDomain,
    copyDomainPort,
    type ISupportClusterType,
  } from './components/SlaveDomainCell.vue';
  import type { ClusterModel } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: clusterType;
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
    isFilter: boolean;
    selectedList: ClusterModel<clusterType>[];
  }

  type IRowData = ClusterModel<T>;

  const props = defineProps<Props<T>>();

  const { t } = useI18n();

  const handleCopyAll = (field: string) => {
    if (field === 'domain') {
      props
        .getTableInstance()!
        .getAllData<ClusterModel<T>>()
        .then((data) => {
          copyDomain(_.flatten(data.map((item) => item.slaveEntryList)));
        });
    } else if (field === 'instance') {
      props
        .getTableInstance()!
        .getAllData<ClusterModel<T>>()
        .then((data) => {
          copyDomainPort(_.flatten(data.map((item) => item.slaveEntryList)));
        });
    }
  };

  const handleCopySelected = (field: string) => {
    if (field === 'domain') {
      copyDomain(_.flatten(props.selectedList.map((item) => item.slaveEntryList)));
    } else if (field === 'instance') {
      copyDomainPort(_.flatten(props.selectedList.map((item) => item.slaveEntryList)));
    }
  };
</script>
<style lang="less">
  .cluster-table-slave-domain-column {
    &:hover {
      [class*='db-icon'] {
        display: inline !important;
      }
    }

    [class*='db-icon'] {
      display: none;
      margin-top: 1px;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }

    .layout-append {
      align-self: flex-start;
    }
  }
</style>
