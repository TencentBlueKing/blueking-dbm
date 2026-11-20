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
  <InfoItem :label="t('地域')">
    {{ regionName }}
  </InfoItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRegions } from '@services/source/kubernetesToolbox';

  import { getCloudRegionNameDisplay } from '@common/const';

  import { Item as InfoItem } from './info-list/Index.vue';

  interface Props {
    ticketDetails: {
      details: {
        /** 新协议：地域标识（取 get_regions 的 bkCloudRegion）；存量单据用 city_code */
        bk_cloud_region?: string;
        city_code?: string;
      };
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const regionName = ref('--');

  // 新协议单据的 bk_cloud_region 直接展示；存量单据按 city_code（regionCode）反查 get_regions 的 regionName
  useRequest(getRegions, {
    onSuccess: (cityList) => {
      if (props.ticketDetails.details.bk_cloud_region) {
        regionName.value = getCloudRegionNameDisplay(props.ticketDetails.details.bk_cloud_region) || '--';
        return;
      }
      const cityCode = props.ticketDetails.details.city_code;
      const name = cityList.find((item) => item.regionCode === cityCode)?.regionName;
      regionName.value = name ?? '--';
    },
  });
</script>
