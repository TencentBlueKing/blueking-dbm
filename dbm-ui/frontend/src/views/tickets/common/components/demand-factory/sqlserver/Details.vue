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

  import { TicketTypes } from '@common/const';

  import PreviewTable from '@views/sqlserver-manage/apply/components/PreviewTable.vue';

  import SpecInfos from '../../SpecInfos.vue';
  import type { DetailsSqlserver } from '../common/types';
  import DemandInfo, {
    type DemandInfoConfig,
  } from '../components/DemandInfo.vue';

  interface Props {
    ticketDetails: TicketDetails<DetailsSqlserver>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { AFFINITY: affinityList } = useSystemEnviron().urls;

  const {
    details,
    ticket_type: ticketType
  } = props.ticketDetails;
  const {
    ip_source: ipSource,
    resource_spec: resourceSpec
  } = details
  const isSingleType = ticketType === TicketTypes.SQLSERVER_SINGLE_APPLY;
  const isFromResourcePool = ipSource === 'resource_pool';
  const backendSpec = resourceSpec.backend;

  const config: DemandInfoConfig[] = [
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
          label: t('DB模块名'),
          key: 'details.db_module_name',
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
      title: t('需求信息'),
      list: [
        {
          label: t('集群数量'),
          key: 'details.cluster_count',
        },
        {
          label: t('每组主机部署集群'),
          key: 'details.inst_num',
        },
        {
          label: t('服务器选择'),
          render: () => isFromResourcePool ? t('自动从资源池匹配') : t('业务空闲机')
        },
        {
          label: t('后端存储规格'),
          render: () => (
            <bk-popover
              placement="top"
              theme="light">
              {{
                default: () => (
                  <span
                    class="pb-2"
                    style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
                    {backendSpec.spec_name }（{ `${backendSpec.count} ${t('台')}`}）
                  </span>
                ),
                content: () => <SpecInfos data={backendSpec} />,
              }}
            </bk-popover>
          ),
        },
        {
          label: t('备注'),
          key: 'remark',
        },
        {
          label: t('集群设置'),
          isTable: true,
          render: () => (
            <PreviewTable
              data={tableData.value}
              is-show-nodes={!isFromResourcePool}
              is-single-type={isSingleType}
              max-height={240}
              min-height={0}
              nodes={props.ticketDetails.details.nodes || []} />
          ),
        },
      ],
    },
  ];

  if (!isSingleType) {
    config.splice(1, 0,     {
      title: t('数据库部署信息'),
      list: [
        {
          label: t('数据库部署信息'),
          render: () => affinity.value || '--',
        },
        {
          label: t('SQLServer起始端口'),
          key: 'details.start_mssql_port',
        },
      ],
    },)
  }

  const cityName = ref('--');

  /**
   * preview table data
   */
  const tableData = computed(() =>
    (props.ticketDetails.details.domains || []).map((domainItem) => {
      const { details } = props.ticketDetails;
      return {
        domain: domainItem.master,
        slaveDomain: domainItem.slave,
        disasterDefence: t('同城跨园区'),
        deployStructure: isSingleType ? t('单节点部署') : t('主从部署'),
        version: details.db_version,
        charset: details.charset,
      };
    }
    ),
  );

  const affinity = computed(() => {
    const level = props.ticketDetails.details.disaster_tolerance_level;
    if (level && affinityList) {
      return affinityList.find((item) => item.value === level)?.label;
    }
    return '--';
  });

  useRequest(getInfrasCities, {
    onSuccess: (cityList) => {
      const cityCode = props.ticketDetails.details.city_code;
      const name = cityList.find((item) => item.city_code === cityCode)?.city_name;
      cityName.value = name ?? '--';
    },
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
