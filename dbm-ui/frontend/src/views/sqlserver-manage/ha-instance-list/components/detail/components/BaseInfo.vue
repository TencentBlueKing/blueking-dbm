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
    class="base-info pt-20"
    :columns="columns"
    :data="data" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import SqlServerHaInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';

  import DbStatus from '@components/db-status/index.vue';
  import EditInfo, {
    type InfoColumn,
  } from '@components/editable-info/index.vue';
  import RenderTextEllipsisOneLine from '@components/text-ellipsis-one-line/index.vue';

  interface Props {
    data: SqlServerHaInstanceModel
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  const columns: InfoColumn[][] = [
    [
      {
        label: t('实例'),
        key: 'instance_address',
      },
      {
        label: t('主机IP'),
        key: 'bk_host_innerip',
      },
      {
        label: t('状态'),
        key: 'status',
        render: () => {
          const {
            theme,
            text,
          } = props.data.statusInfo;
          return <DbStatus theme={theme}>{text}</DbStatus>;
        },
      },
      {
        label: t('主访问入口'),
        key: 'master_domain',
        render: () => (
          <RenderTextEllipsisOneLine
            text={props.data.master_domain}
            onClick={handleToClusterDetails}>
            <db-icon
              type="link"
              class="ml-4" />
          </RenderTextEllipsisOneLine>
        ),
      },
      {
        label: t('从访问入口'),
        key: 'slave_domain',
      },
      {
        label: t('管控区域'),
        key: 'bk_cloud_name',
      },
      {
        label: t('所在城市'),
        key: 'idc_city_name',
      },
      {
        label: t('所在机房'),
        key: 'bk_idc_name',
      },
    ],
    [
      {
        label: t('部署架构'),
        key: 'cluster_type_display',
      },
      {
        label: t('部署角色'),
        key: 'role',
      },
      {
        label: t('部署时间'),
        key: 'create_at',
      },
    ],
  ];

  /**
   * 查看集群详情
   */
  const handleToClusterDetails = () => {
    router.push({
      name: 'SqlServerHaClusterList',
      query: {
        cluster_id: props.data.cluster_id,
      },
    });
  };
</script>

<style lang="less" scoped>
.base-info {
  box-shadow: unset;

  :deep(.inline-item) {
    display: flex;
    align-items: center;

    .db-icon-link {
      color: @primary-color;
      cursor: pointer;
      flex-shrink: 0;
    }
  }
}
</style>
