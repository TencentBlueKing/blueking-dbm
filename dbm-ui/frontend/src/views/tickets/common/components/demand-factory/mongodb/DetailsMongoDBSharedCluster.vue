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
  <DemandInfo
    :config="config"
    :data="ticketDetails" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasCities } from '@services/ticket';
  import type { TicketDetails } from '@services/types/ticket';

  import { useSystemEnviron } from '@stores';

  import SpecInfos from '../../SpecInfos.vue';
  import type { DetailsMongoDBSharedCluster } from '../common/types';
  import DemandInfo from '../components/DemandInfo.vue';

  interface Props{
    ticketDetails: TicketDetails<DetailsMongoDBSharedCluster>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { AFFINITY: affinityList } = useSystemEnviron().urls;

  const {
    mongo_config: configServerSpec,
    mongos: mongosSpec,
    mongodb: shardSvrSpec,
  } = props.ticketDetails.details.resource_spec;

  const config = [
    {
      title: t('部署模块'),
      list: [
        {
          label: t('所属业务'),
          key: 'bk_biz_name',
        },
        {
          label: t('业务英文名'),
          key: 'db_app_abbr',
        },
        {
          label: t('集群ID'),
          key: 'details.cluster_id',
        },
        {
          label: t('集群名称'),
          key: 'details.cluster_name',
        },
        {
          label: t('集群别名'),
          key: 'details.cluster_alias',
        },
        {
          label: t('管控区域'),
          key: 'details.bk_cloud_name',
        },
      ],
    },
    {
      title: t('地域要求'),
      list: [
        {
          label: t('数据库部署地域'),
          render: () => cityName.value || '--',
        },
      ],
    },
    {
      title: t('数据库部署信息'),
      list: [
        {
          label: t('容灾要求'),
          render: () => affinity.value || '--',
        },
        {
          label: t('MongoDB版本'),
          key: 'details.db_version',
        },
        {
          label: t('访问端口'),
          key: 'details.start_port',
        },
      ],
    },
    {
      title: t('需求信息'),
      list: [
        {
          label: t('Config Server资源规格'),
          render: () => (
            <bk-popover
              placement="top"
              theme="light">
              {{
                default: () => (
                  <span
                    class="pb-2"
                    style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
                    {configServerSpec.spec_name }（{ `${configServerSpec.count} ${t('台')}`}）
                  </span>
                ),
                content: () => <SpecInfos data={configServerSpec} />,
              }}
            </bk-popover>
          ),
        },
        {
          label: t('Mongos资源规格'),
          render: () => (
            <bk-popover
              placement="top"
              theme="light">
              {{
                default: () => (
                  <span
                    class="pb-2"
                    style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
                    {mongosSpec.spec_name }（{ `${mongosSpec.count} ${t('台')}`}）
                  </span>
                ),
                content: () => <SpecInfos data={mongosSpec} />,
              }}
            </bk-popover>
          ),
        },
        {
          label: t('ShardSvr资源规格'),
          render: () => (
            <bk-popover
              placement="top"
              theme="light">
              {{
                default: () => (
                  <span
                    class="pb-2"
                    style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
                    {shardSvrSpec.spec_name }（{ `${shardSvrSpec.count} ${t('台')}`}）
                  </span>
                ),
                content: () => <SpecInfos data={shardSvrSpec} />,
              }}
            </bk-popover>
          ),
        },
        {
          label: t('每台主机oplog容量占比'),
          key: 'details.oplog_percent',
        },
      ],
    },
  ];

  const cityName = ref('--');

  const affinity = computed(() => {
    const level = props.ticketDetails?.details?.disaster_tolerance_level;
    if (level && affinityList) {
      return affinityList.find(item => item.value === level)?.label;
    }
    return '--';
  });

  useRequest(getInfrasCities, {
    onSuccess: (cityList) => {
      const cityCode = props.ticketDetails.details.city_code;
      const name = cityList.find(item => item.city_code === cityCode)?.city_name;
      cityName.value = name ?? '--';
    },
  });
</script>
