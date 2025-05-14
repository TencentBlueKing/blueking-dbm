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

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import MongodbDetailModel from '@services/model/mongodb/mongodb-detail';

  import EditInfo, { type InfoColumn } from '@components/editable-info/index.vue';

  import ClusterTagCell from '@views/db-manage/common/cluster-table-column/components/cluster-tag-cell/Index.vue';

  interface Props {
    data: MongodbDetailModel;
  }

  type Emits = (e: 'refresh') => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const columns: InfoColumn[][] = [
    [
      {
        key: 'cluster_name',
        label: t('集群名称'),
      },
      {
        key: 'cluster_alias',
        label: t('集群别名'),
      },
      {
        key: 'master_domain',
        label: t('域名'),
      },
      {
        key: 'region',
        label: t('地域'),
      },
      {
        key: 'bk_cloud_name',
        label: t('管控区域'),
        render: () => (props.data.bk_cloud_name ? `${props.data.bk_cloud_name}[${props.data.bk_cloud_id}]` : '--'),
      },
      {
        key: 'disasterToleranceLevelName',
        label: t('容灾要求'),
      },
      {
        key: 'sortedTags',
        label: t('标签'),
        render: () => (
          <ClusterTagCell
            data={props.data}
            onSuccess={() => emits('refresh')}
          />
        ),
      },
    ],
    [
      {
        key: 'major_version',
        label: t('数据库版本'),
      },
      {
        key: 'node',
        label: t('节点'),
        render: () => props.data.mongodb.map((item) => item.instance).join(','),
      },
      {
        key: 'creator',
        label: t('创建人'),
      },
      {
        key: 'createAtDisplay',
        label: t('创建时间'),
      },
      {
        key: 'spec_name',
        label: t('规格'),
        render: () => props.data.cluster_spec.spec_name || '--',
      },
    ],
  ];
</script>
