<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <DbOriginalTable
    :columns="columns"
    :data="dataList" />
  <InfoList>
    <InfoItem :label="t('忽略业务连接：')">
      {{ ticketDetails.details.force ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('备份源：')">
      {{ ticketDetails.details.backup_source === 'local' ? t('本地备份') : t('远程备份') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { MySQLMigrateUpgradeDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';
  import { getPackages } from '@services/source/package';

  import InfoList, {
    Item as InfoItem,
  } from '@views/tickets/common/components/demand-factory/components/info-list/Index.vue';

  import VersionContent from './components/VersionContent.vue'

  interface DataItem {
    cluster_id: number,
    immute_domain: string,
    name: string,
    currentVersion: {
      version: string;
      package: string;
      charSet: string;
      moduleName: string;
    }
    targetVersion: {
      pkg_id: number,
      new_db_module_id: number,
      version: string;
      package: string;
      charSet: string;
      moduleName: string;
    },
    ip: string[];
    old_master_slave: string;
    old_readonly_slaves: string[];
    new_readonly_slaves: string[];
  }

  interface Props {
    ticketDetails: TicketModel<MySQLMigrateUpgradeDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const dataList = ref<DataItem[]>([])

  const columns = [
    // {
    //   label: t('集群ID'),
    //   field: 'cluster_id',
    //   width: 100,
    //   render: ({ cell }: { cell: [] }) => <span>{cell || '--'}</span>,
    // },
    {
      label: t('集群名称'),
      field: 'immute_domain',
      showOverflowTooltip: false,
      render: ({ data }: { data: any }) => (
        <div class="cluster-name text-overflow"
          v-overflow-tips={{
            content: `
              <p>${t('域名')}：${data.immute_domain}</p>
              ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
            `,
            allowHTML: true,
          }}>
          <span>{data.immute_domain}</span><br />
          <span class="cluster-name__alias">{data.name}</span>
        </div>
      ),
    },
    {
      label: t('主从主机'),
      field: 'old_master_slave',
      render: ({ data }: { data: DataItem }) => data.old_master_slave.length ? (
        <div class="old-master-slave-host">
          <div class="host-item">
            <div class="host-tag host-tag-master">M</div>
            <div>{data.old_master_slave[0]}</div>
          </div>
          <div class="host-item mt-4">
            <div class="host-tag host-tag-slave">S</div>
            <div>{data.old_master_slave[1]}</div>
          </div>
        </div>
      ) : '--'
    },
    {
      label: t('只读主机'),
      field: 'old_readonly_slaves',
      render: ({ data }: { data: DataItem }) => data.old_readonly_slaves.length ? data.old_readonly_slaves.map(item => <p>{item}</p>) : '--'
    },
    {
      label: t('当前版本'),
      field: 'new_master',
      minWidth: 200,
      render: ({ data }: { data: DataItem }) => <VersionContent data={data.currentVersion} />
    },
    {
      label: t('目标版本'),
      field: 'new_version',
      minWidth: 200,
      render: ({ data }: { data: DataItem }) => <VersionContent data={data.targetVersion} />
    },
    {
      label: t('新主从主机'),
      field: 'ip',
      render: ({ data }: { data: DataItem }) => data.ip.map(item => <p>{item}</p>)
    },
    {
      label: t('新只读主机'),
      field: 'new_readonly_slaves',
      render: ({ data }: { data: DataItem }) => data.new_readonly_slaves.length ? data.new_readonly_slaves.map(item => <p>{item}</p>) : '--'
    }
  ];

  const list: DataItem[] = [];
  const infosData = props.ticketDetails.details.infos;
  const clusterIds = props.ticketDetails.details.clusters;
  infosData.forEach((item) => {
    item.cluster_ids.forEach((id) => {
      const clusterData = clusterIds[id];
      const readonlySlaves = item.read_only_slaves || [];
      const readonlySlaveMap = readonlySlaves.reduce<{
        old: string[],
        new: string[]
      }>((prevMap, slaveItem) => Object.assign({}, prevMap, {
          old: prevMap.old.concat([slaveItem.old_slave.ip]),
          new: prevMap.new.concat([slaveItem.new_slave.ip])
        }), {
        old: [],
        new: []
      })
      list.push(Object.assign({
        // cluster_id: id,
        immute_domain: clusterData.immute_domain,
        name: clusterData.name,
        currentVersion: {
          version: item.display_info.current_version,
          package: item.display_info.current_package,
          charSet: item.display_info.charset,
          moduleName: item.display_info.current_module_name
        },
        targetVersion: {
          pkg_id: item.pkg_id,
          new_db_module_id: item.new_db_module_id,
          version: '',
          package: '',
          charSet: item.display_info.charset,
          moduleName: item.display_info.target_module_name,
        },
        ip: [item.new_master.ip, item.new_slave.ip],
        old_master_slave: item.display_info.old_master_slave || [],
        old_readonly_slaves: readonlySlaveMap.old,
        new_readonly_slaves: readonlySlaveMap.new
      }));
    });
  });
  dataList.value = list

  useRequest(getPackages, {
    defaultParams: [{
      pkg_type: 'mysql',
      db_type: 'mysql'
    }],
    onSuccess(packageResult) {
      const packageMap = packageResult.results.reduce((prev, item) => Object.assign(prev, { [item.id]: {
        name: item.name,
        version: item.version
      } }), {} as Record<number, {
        name: string,
        version: string
      }>)
      dataList.value = dataList.value.map(item => Object.assign(item, {
        targetVersion: {
          ...item.targetVersion,
          version: packageMap[item.targetVersion.pkg_id].version,
          package: packageMap[item.targetVersion.pkg_id].name
        }
      }))
    }
  })
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';

  :deep(.old-master-slave-host) {
    .host-item {
      display: flex;
      align-items: center;

      .host-tag {
        width: 16px;
        height: 16px;
        margin-right: 4px;
        font-size: @font-size-mini;
        font-weight: bolder;
        line-height: 16px;
        text-align: center;
      }

      .host-tag-master {
        color: @primary-color;
        background-color: #cad7eb;
      }

      .host-tag-slave {
        color: #2dcb56;
        background-color: #c8e5cd;
      }
    }
  }
</style>
