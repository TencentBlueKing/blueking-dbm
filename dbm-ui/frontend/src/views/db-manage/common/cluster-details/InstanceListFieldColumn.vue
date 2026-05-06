<template>
  <TableColumn
    col-key="id"
    :filter="columnFilter?.['id']"
    title="ID"
    :width="80">
    <template #default="{ row }: { row: IColumnData }">
      {{ row.id }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="status"
    :filter="columnFilter?.['status']"
    :min-width="80"
    :title="t('状态')">
    <template #default="{ row }: { row: IColumnData }">
      <ClusterInstanceStatus :data="row.status" />
    </template>
  </TableColumn>
  <TableColumn
    col-key="role"
    :filter="columnFilter?.['role']"
    :min-width="150"
    :title="t('部署角色')">
    <template #default="{ row }: { row: IColumnData }">
      <RenderClusterRole :data="[row.roleDisplay || row.role]" />
    </template>
  </TableColumn>
  <TableColumn
    col-key="version"
    :filter="columnFilter?.['version']"
    :min-width="240"
    :title="t('版本')">
    <template #default="{ row }: { row: IColumnData }">
      {{ row.version || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="ip"
    :filter="columnFilter?.['ip']"
    :min-width="150"
    :title="t('主机IP')">
    <template #default="{ row }: { row: IColumnData }">
      <RouterLink
        :to="{
          query: {
            ...getSearchParams(),
            [URL_CLUSTER_DETAIL_MEMO_KEY]: 'host',
            [URL_HOST_MEMO_KEY]: encodeURIComponent(
              JSON.stringify({
                ip: row.ip,
              }),
            ),
          },
        }">
        {{ row.ip }}
      </RouterLink>
    </template>
  </TableColumn>
  <TableColumn
    col-key="bk_sub_zone"
    :filter="columnFilter?.['bk_sub_zone']"
    :min-width="120"
    :title="t('园区')">
    <template #default="{ row }: { row: IColumnData }">
      <RouterLink
        v-if="row.bk_sub_zone"
        :to="{
          query: {
            ...getSearchParams(),
            [URL_CLUSTER_DETAIL_MEMO_KEY]: 'host',
            [URL_HOST_MEMO_KEY]: encodeURIComponent(
              JSON.stringify({
                bk_sub_zone: row.bk_sub_zone,
              }),
            ),
          },
        }">
        {{ row.bk_sub_zone }}
      </RouterLink>
      <span v-else>--</span>
    </template>
  </TableColumn>
  <TableColumn
    col-key="bk_os_name"
    :filter="columnFilter?.['bk_os_name']"
    :min-width="250"
    :title="t('操作系统')">
    <template #default="{ row }: { row: IColumnData }">
      <RouterLink
        v-if="row.bk_os_name"
        :to="{
          query: {
            ...getSearchParams(),
            [URL_CLUSTER_DETAIL_MEMO_KEY]: 'host',
            [URL_HOST_MEMO_KEY]: encodeURIComponent(
              JSON.stringify({
                bk_os_name: row.bk_os_name,
              }),
            ),
          },
        }">
        {{ row.bk_os_name }}
      </RouterLink>
      <span v-else>--</span>
    </template>
  </TableColumn>
  <!-- <TableColumn
    col-key="bk_svr_device_cls_name"
    :min-width="250"
    :title="t('机型')">
    <template #default="{ row }: { row: IColumnData }">
      {{ row.bk_svr_device_cls_name || '--' }}
    </template>
  </TableColumn> -->
  <TableColumn
    col-key="create_at"
    :filter="columnFilter?.['create_at']"
    :min-width="250"
    sorter
    :title="t('部署时间')" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useInstanceColumnFilter, useUrlSearch } from '@hooks';

  import type { ClusterTypes } from '@common/const';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  import RenderClusterRole from '@views/db-manage/common/RenderRole.vue';
  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';

  import { URL_CLUSTER_DETAIL_MEMO_KEY, URL_HOST_MEMO_KEY } from './constants';

  type IColumnData = {
    roleDisplay?: string;
  } & ServiceReturnType<ReturnType<typeof useClusterInstanceList>>['results'][number];

  interface Props {
    clusterId: number;
    clusterType: ClusterTypes;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { getSearchParams } = useUrlSearch();
  const { data: columnFilter } = useInstanceColumnFilter({
    cluster_id: props.clusterId,
    cluster_type: props.clusterType,
    instance_attrs: ['role', 'version', 'bk_os_name', 'bk_sub_zone'] as const,
  });
</script>
