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

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';
  import { getInfrasCities } from '@services/source/ticket';

  import { TicketTypes } from '@common/const';

  import { useAffinity } from '../../hooks/useAffinity';
  import DemandInfo from '../components/DemandInfo.vue';
  import SpecInfos from '../components/SpecInfos.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.InsApply>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_INS_APPLY,
    inheritAttrs: false,
  });

  const { t } = useI18n();
  const { affinity } = useAffinity(props.ticketDetails);

  const { db_app_abbr: appAbbr, details } = props.ticketDetails;
  const { append_apply: isAppend, infos, port = 0, resource_spec: resourceSpec } = details;
  const tableData = infos.map((infoItem, index) => {
    const { cluster_name: clusterName } = infoItem;
    return {
      databases: infoItem.databases,
      mainDomain: `ins.${clusterName}.${appAbbr}.db${isAppend ? '' : `#${port + index}`}`,
      masterIp: infoItem.backend_group?.master.ip,
      slaveDomain: `ins.${clusterName}.${appAbbr}.dr#${isAppend ? '' : `#${port + index}`}`,
      slaveIp: infoItem.backend_group?.slave.ip,
    };
  });

  const columns = [
    {
      field: 'mainDomain',
      label: t('主域名'),
      showOverflowTooltip: true,
    },
    // {
    //   label: t('从域名'),
    //   field: 'slaveDomain',
    //   showOverflowTooltip: true,
    // },
    {
      field: 'databases',
      label: 'Databases',
      showOverflowTooltip: true,
    },
  ];

  if (isAppend) {
    columns.push(
      ...[
        {
          field: 'masterIp',
          label: t('待部署主库主机'),
          showOverflowTooltip: true,
        },
        {
          field: 'slaveIp',
          label: t('待部署从库主机'),
          showOverflowTooltip: true,
        },
      ],
    );
  }

  const config = [
    {
      list: [
        {
          key: 'bk_biz_name',
          label: t('所属业务'),
        },
        {
          key: 'bk_biz_name',
          label: t('业务英文名'),
        },
        // {
        //   label: t('管控区域'),
        //   key: 'details.bk_cloud_name',
        // },
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
          key: 'details.append_apply',
          label: t('部署方式'),
          render: () => (props.ticketDetails.details.append_apply ? t('已有主从所在主机追加部署') : t('全新主机部署')),
        },
        {
          isHidden: isAppend,
          label: t('容灾要求'),
          render: () => affinity.value || '--',
        },
      ],
      title: t('数据库部署信息'),
    },
    {
      list: [
        {
          isHidden: isAppend,
          key: 'details.port',
          label: t('Redis 起始端口'),
        },
        {
          label: t('服务器选择'),
          render: () => t('自动从资源池匹配'),
        },
        {
          isHidden: isAppend,
          label: t('后端存储规格'),
          render: () => {
            const backendSpec = resourceSpec.backend_group;
            return (
              <bk-popover
                placement='top'
                theme='light'>
                {{
                  content: () => <SpecInfos data={backendSpec} />,
                  default: () => (
                    <span
                      class='pb-2'
                      style='cursor: pointer;border-bottom: 1px dashed #979ba5;'>
                      {backendSpec.spec_name}（{`${backendSpec.count} ${t('台')}`}）
                    </span>
                  ),
                }}
              </bk-popover>
            );
          },
        },
        {
          isTable: true,
          label: t('域名设置'),
          render: () => (
            <db-original-table
              columns={columns}
              data={tableData}
              max-height={240}
              min-height={0}
            />
          ),
        },
      ],
      title: t('需求信息'),
    },
  ];

  const cityName = ref('--');

  // const affinity = computed(() => {
  //   const level = props.ticketDetails?.details?.disaster_tolerance_level;
  //   if (level && affinityList) {
  //     return affinityList.find(item => item.value === level)?.label;
  //   }
  //   return '--';
  // });

  useRequest(getInfrasCities, {
    onSuccess: (cityList) => {
      const cityCode = props.ticketDetails.details.city_code;
      const name = cityList.find((item) => item.city_code === cityCode)?.city_name;
      cityName.value = name ?? '--';
    },
  });
</script>
