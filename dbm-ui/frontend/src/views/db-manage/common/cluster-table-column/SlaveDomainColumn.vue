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
      <div
        v-if="data.slaveEntryList.length > 0"
        @mouseenter="handleToolsShow">
        <TextOverflowLayout>
          <div
            v-for="slaveItem in data.slaveEntryList.slice(0, renderCount)"
            :key="slaveItem.entry"
            style="line-height: 26px">
            {{ slaveItem.entry }}:{{ slaveItem.port }}
          </div>
          <template
            v-if="isToolsShow"
            #append>
            <PopoverCopy>
              <div @click="handleCopyDomain(data.slaveEntryList)">{{ t('复制域名') }}</div>
              <div @click="handleCopyDomainPort(data.slaveEntryList)">{{ t('复制域名:端口') }}</div>
            </PopoverCopy>
            <span v-db-console="accessEntryDbConsole">
              <EditEntryConfig
                :id="data.id"
                :biz-id="data.bk_biz_id"
                :permission="data.permission.access_entry_edit"
                :resource="clusterTypeInfos[clusterType].dbType"
                @success="fetchTableData">
              </EditEntryConfig>
            </span>
          </template>
        </TextOverflowLayout>
      </div>
      <span v-if="data.slaveEntryList.length < 1">--</span>
      <div v-if="data.slaveEntryList.length > renderCount">
        <span>... </span>
        <BkPopover
          placement="top"
          theme="light">
          <BkTag>
            <I18nT keypath="共n个">{{ data.slaveList.length }}</I18nT>
          </BkTag>
          <template #content>
            <div style="max-height: 280px; overflow: scroll">
              <div
                v-for="slaveItem in data.slaveEntryList"
                :key="slaveItem.entry"
                style="line-height: 20px">
                {{ slaveItem.entry }}:{{ slaveItem.port }}
              </div>
            </div>
          </template>
        </BkPopover>
      </div>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import _ from 'lodash';
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import PopoverCopy from '@components/popover-copy/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import EditEntryConfig from '@views/db-manage/common/cluster-entry-config/Index.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import { execCopy } from '@utils';

  import type { ClusterModel } from './types';

  export type ISupportClusterType =
    | ClusterTypes.TENDBCLUSTER
    | ClusterTypes.TENDBHA
    | ClusterTypes.REDIS_INSTANCE
    | ClusterTypes.SQLSERVER_HA;

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
    selectedList: ClusterModel<clusterType>[];
    isFilter: boolean;
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  export interface Emits {
    (e: 'refresh'): void;
  }

  type IRowData = ClusterModel<T>;

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const dbConsoleMap: Record<ISupportClusterType, string> = {
    [ClusterTypes.TENDBCLUSTER]: 'tendbCluster.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.TENDBHA]: 'mysql.haClusterList.modifyEntryConfiguration',
    [ClusterTypes.REDIS_INSTANCE]: 'redis.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.SQLSERVER_HA]: 'sqlserver.haClusterList.modifyEntryConfiguration',
  };

  const { t } = useI18n();

  const renderCount = 6;
  const isToolsShow = ref(false);
  const accessEntryDbConsole = computed(() => dbConsoleMap[props.clusterType]);

  const fetchTableData = () => {
    emits('refresh');
  };

  const handleToolsShow = () => {
    setTimeout(() => {
      isToolsShow.value = true;
    }, 1000);
  };

  const copyDomain = (data: IRowData['slaveEntryList']) => {
    const copyList = _.uniq(data.map(({ entry }) => entry));
    execCopy(copyList.join('\n'), t('复制成功，共n条', { n: copyList.length }));
  };

  const copyDomainPort = (data: IRowData['slaveEntryList']) => {
    const copyList = _.uniq(data.map(({ entry, port }) => `${entry}:${port}`));
    execCopy(copyList.join('\n'), t('复制成功，共n条', { n: copyList.length }));
  };

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

  const handleCopyDomain = (data: IRowData['slaveEntryList']) => {
    copyDomain(data);
  };

  const handleCopyDomainPort = (data: IRowData['slaveEntryList']) => {
    copyDomainPort(data);
  };
</script>
<style lang="less">
  .cluster-table-slave-domain-column {
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

    .layout-append {
      align-self: flex-start;
    }
  }
</style>
