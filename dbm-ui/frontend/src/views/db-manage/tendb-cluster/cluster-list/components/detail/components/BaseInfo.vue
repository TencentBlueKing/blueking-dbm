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
  <EditInfo
    class="pt-20"
    :columns="columns"
    :data="data" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import EditInfo, { type InfoColumn } from '@components/editable-info/index.vue';

  interface Props {
    data: TendbClusterModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns: InfoColumn[][] = [
    [
      {
        key: 'cluster_name',
        label: t('集群名称'),
      },
      {
        key: 'master_domain',
        label: t('主访问入口'),
      },
      {
        key: 'slave_domain',
        label: t('从访问入口'),
      },
      {
        key: 'major_version',
        label: t('MySQL版本'),
      },
      {
        key: 'bk_cloud_name',
        label: t('管控区域'),
        render: () => (props.data.bk_cloud_name ? `${props.data.bk_cloud_name}[${props.data.bk_cloud_id}]` : '--'),
      },
      {
        key: 'creator',
        label: t('创建人'),
      },
      {
        key: 'create_at',
        label: t('创建时间'),
      },
      {
        key: 'spec_name',
        label: t('规格'),
        render: () => props.data.cluster_spec.spec_name || '--',
      },
    ],
    [
      {
        key: 'spider_master',
        label: 'Spider Master',
        render: () => props.data.spider_master.map((item) => item.instance).join(','),
      },
      {
        key: 'spider_slave',
        label: 'Spider Slave',
        render: () => props.data.spider_slave.map((item) => item.instance).join(',') || '--',
      },
      {
        key: 'spider_ctl_primary',
        label: 'Spider Ctl Primary',
        render: () => props.data.spider_ctl_primary || '--',
      },
      {
        key: 'spider_mnt',
        label: t('运维节点'),
        render: () => props.data.spider_mnt.map((item) => item.instance).join(',') || '--',
      },
      {
        key: 'remote_db',
        label: 'RemoteDB',
        render: () => props.data.remote_db.map((item) => item.instance).join(','),
      },
      {
        key: 'remote_dr',
        label: 'RemoteDR',
        render: () => props.data.remote_dr.map((item) => item.instance).join(','),
      },
      {
        key: 'disasterToleranceLevelName',
        label: t('容灾要求'),
      },
    ],
  ];
</script>
