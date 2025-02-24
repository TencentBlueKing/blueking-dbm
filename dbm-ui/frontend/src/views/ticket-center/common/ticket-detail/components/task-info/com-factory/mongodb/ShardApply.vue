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

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';
  import { getInfrasCities } from '@services/source/ticket';

  import { TicketTypes } from '@common/const';

  import { useAffinity } from '../../hooks/useAffinity';
  import DemandInfo from '../components/DemandInfo.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Mongodb.ShardApply>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_SHARD_APPLY,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { affinity } = useAffinity(props.ticketDetails);

  const {
    mongo_config: configServerSpec,
    mongodb: shardSvrSpec,
    mongos: mongosSpec,
  } = props.ticketDetails.details.resource_spec;

  const config = [
    {
      list: [
        {
          key: 'bk_biz_name',
          label: t('所属业务'),
        },
        {
          key: 'db_app_abbr',
          label: t('业务英文名'),
        },
        {
          key: 'details.cluster_id',
          label: t('集群ID'),
        },
        {
          key: 'details.cluster_name',
          label: t('集群名称'),
        },
        {
          key: 'details.cluster_alias',
          label: t('集群别名'),
        },
        {
          key: 'details.bk_cloud_name',
          label: t('管控区域'),
        },
      ],
      title: t('部署模块'),
    },
    {
      list: [
        {
          label: t('数据库部署地域'),
          render: () => cityName.value || '--',
        },
      ],
      title: t('地域要求'),
    },
    {
      list: [
        {
          label: t('容灾要求'),
          render: () => affinity.value || '--',
        },
        {
          key: 'details.db_version',
          label: t('MongoDB版本'),
        },
        {
          key: 'details.start_port',
          label: t('访问端口'),
        },
      ],
      title: t('数据库部署信息'),
    },
    {
      list: [
        {
          label: t('Config Server资源规格'),
          render: () => (
            <bk-popover
              placement='top'
              theme='light'>
              {{
                content: () => <SpecInfos data={configServerSpec} />,
                default: () => (
                  <span
                    class='pb-2'
                    style='cursor: pointer;border-bottom: 1px dashed #979ba5;'>
                    {configServerSpec.spec_name}（{`${configServerSpec.count} ${t('台')}`}）
                  </span>
                ),
              }}
            </bk-popover>
          ),
        },
        {
          label: t('Mongos资源规格'),
          render: () => (
            <bk-popover
              placement='top'
              theme='light'>
              {{
                content: () => <SpecInfos data={mongosSpec} />,
                default: () => (
                  <span
                    class='pb-2'
                    style='cursor: pointer;border-bottom: 1px dashed #979ba5;'>
                    {mongosSpec.spec_name}（{`${mongosSpec.count} ${t('台')}`}）
                  </span>
                ),
              }}
            </bk-popover>
          ),
        },
        {
          label: t('ShardSvr资源规格'),
          render: () => (
            <bk-popover
              placement='top'
              theme='light'>
              {{
                content: () => <SpecInfos data={shardSvrSpec} />,
                default: () => (
                  <span
                    class='pb-2'
                    style='cursor: pointer;border-bottom: 1px dashed #979ba5;'>
                    {shardSvrSpec.spec_name}（{`${shardSvrSpec.count} ${t('台')}`}）
                  </span>
                ),
              }}
            </bk-popover>
          ),
        },
        {
          key: 'details.oplog_percent',
          label: t('每台主机oplog容量占比'),
        },
      ],
      title: t('需求信息'),
    },
  ];

  const cityName = ref('--');

  useRequest(getInfrasCities, {
    onSuccess: (cityList) => {
      const cityCode = props.ticketDetails.details.city_code;
      const name = cityList.find((item) => item.city_code === cityCode)?.city_name;
      cityName.value = name ?? '--';
    },
  });
</script>
