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
  <HostPreview
    v-model:is-show="isPreviewShow"
    :fetch-nodes="getTicketHostNodes"
    :fetch-params="fetchNodesParams"
    :title="previewTitle" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasCities,getTicketHostNodes  } from '@services/source/ticket';
    import type { TicketDetails } from '@services/types/ticket';

  import { useSystemEnviron } from '@stores';

  import HostPreview from '@components/host-preview/HostPreview.vue';

  import { firstLetterToUpper } from '@utils';

  import SpecInfos from '../../SpecInfos.vue';
  import type { DorisCluster } from '../common/types';
  import DemandInfo, {
    type DemandInfoConfig
  } from '../components/DemandInfo.vue';

  interface Props {
    ticketDetails: TicketDetails<DorisCluster>
  }

  // type ResouceSpec = NonNullable<DorisCluster['resource_spec']>

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { AFFINITY: affinityList } = useSystemEnviron().urls;

  const isFromResourcePool = props.ticketDetails.details.ip_source === 'resource_pool';

  const {
    resource_spec: resourceSpec,
  } = props.ticketDetails.details;
  const followerSpec = resourceSpec?.follower
  const observerSpec = resourceSpec?.observer
  const hotSpec = resourceSpec?.hot
  const coldSpec = resourceSpec?.cold

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
          label: t('集群名称'),
          key: 'details.cluster_name',
        },
        {
          label: t('集群别名'),
          key: 'details.cluster_alias',
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
      title: t('部署需求'),
      list: [
        {
          label: t('容灾要求'),
          render: () => affinity.value || '--',
        },
        {
          label: t('Doris版本'),
          key: 'details.db_version',
        },
        {
          label: t('服务器选择方式'),
          render: () => isFromResourcePool ? t('从资源池匹配') : t('手动选择'),
        },
        {
          label: t('查询端口'),
          key: 'details.query_port',
        },
        {
          label: t('http端口'),
          key: 'details.http_port',
        },
        {
          label: t('备注'),
          key: 'remark',
        },
      ],
    },
  ];

  if (isFromResourcePool) {
    config[2].list.push(
      {
        label: t('Follower节点'),
        render: () => (
          followerSpec ? (
            <bk-popover
              placement="top"
              theme="light">
              {{
                default: () => (
                  <span
                    class="pb-2"
                    style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
                    {followerSpec.spec_name }（{ `${followerSpec.count} ${t('台')}`}）
                  </span>
                ),
                content: () => <SpecInfos data={followerSpec} />,
              }}
            </bk-popover>
            ) : '--'
        ),
      },
      {
        label: t('Observer节点'),
        render: () => (
          observerSpec ? (
            <bk-popover
              placement="top"
              theme="light">
              {{
                default: () => (
                  <span
                    class="pb-2"
                    style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
                    {observerSpec.spec_name }（{ `${observerSpec.count} ${t('台')}`}）
                  </span>
                ),
                content: () => <SpecInfos data={observerSpec} />,
              }}
            </bk-popover>
            ) : '--'
        ),
      },
      {
        label: t('热节点'),
        render: () => (
          hotSpec ? (
            <bk-popover
              placement="top"
              theme="light">
              {{
                default: () => (
                  <span
                    class="pb-2"
                    style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
                    {hotSpec.spec_name }（{ `${hotSpec.count} ${t('台')}`}）
                  </span>
                ),
                content: () => <SpecInfos data={hotSpec} />,
              }}
            </bk-popover>
            ) : '--'
        ),
      },
      {
        label: t('冷节点'),
        render: () => (
          coldSpec ? (
            <bk-popover
              placement="top"
              theme="light">
              {{
                default: () => (
                  <span
                    class="pb-2"
                    style="cursor: pointer;border-bottom: 1px dashed #979ba5;">
                    {coldSpec.spec_name }（{ `${coldSpec.count} ${t('台')}`}）
                  </span>
                ),
                content: () => <SpecInfos data={coldSpec} />,
              }}
            </bk-popover>
            ) : '--'
        ),
      },
    )
  } else {
    config[2].list.push(
      {
        label: t('Follower节点IP'),
        render: () => (
          getServiceNums('follower') > 0
            ? <bk-button
                text
                theme="primary"
                onClick={() => handleShowPreview('follower')}>
                {t('台')}
              </bk-button>
            : '--'
        ),
      },
      {
        label: t('Observer节点IP'),
        render: () => (
          getServiceNums('observer') > 0
            ? <bk-button
                text
                theme="primary"
                onClick={() => handleShowPreview('observer')}>
                {t('台')}
              </bk-button>
            : '--'
        ),
      },
      {
        label: t('热节点IP'),
        render: () => (
          getServiceNums('hot') > 0
            ? <bk-button
                text
                theme="primary"
                onClick={() => handleShowPreview('hot')}>
                {t('台')}
              </bk-button>
            : '--'
        ),
      },
      {
        label: t('冷节点IP'),
        render: () => (
          getServiceNums('cold') > 0
            ? <bk-button
                text
                theme="primary"
                onClick={() => handleShowPreview('cold')}>
                {t('台')}
              </bk-button>
            : '--'
        ),
      },
    )
  }

  const cityName = ref('--');
  const isPreviewShow = ref(false)
  const previewRole = ref('')
  const previewTitle = ref('')

  const affinity = computed(() => {
    const level = props.ticketDetails.details.disaster_tolerance_level;
    if (level && affinityList) {
      return affinityList.find(item => item.value === level)?.label;
    }
    return '--';
  });

  const fetchNodesParams = computed(() => ({
    bk_biz_id: props.ticketDetails.bk_biz_id,
    id: props.ticketDetails.id,
    role: previewRole.value,
  }));

  useRequest(getInfrasCities, {
    onSuccess: (cityList) => {
      const cityCode = props.ticketDetails.details.city_code;
      const name = cityList.find(item => item.city_code === cityCode)?.city_name;
      cityName.value = name ?? '--';
    },
  });

  const getServiceNums = (key: 'follower' | 'observer' | 'hot' | 'cold') => {
    const nodes = props.ticketDetails.details?.nodes;
    return nodes?.[key].length ?? 0;
  }

  const handleShowPreview = (role: 'follower' | 'observer' | 'hot' | 'cold') => {
    isPreviewShow.value = true;
    previewRole.value = role;
    previewTitle.value = `【${firstLetterToUpper(role)}】${t('主机预览')}`;
  }
</script>
