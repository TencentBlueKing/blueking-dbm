<template>
  <div class="ticket-details-info-title mt-20">{{ t('容灾要求') }}</div>
  <InfoList>
    <InfoItem :label="t('容灾级别')">
      {{ affinityText }}
    </InfoItem>
    <InfoItem :label="t('管控区域')">
      {{ details.bk_cloud_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('地域')">
      {{ cityName }}
    </InfoItem>
    <InfoItem
      v-if="showZoneItem"
      :label="t('可用区')">
      {{ zonesText }}
    </InfoItem>
  </InfoList>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasCities } from '@services/source/infras';

  import { Affinity, affinityMap, getCloudZoneName } from '@common/const';

  import InfoList, { Item as InfoItem } from './info-list/Index.vue';

  interface Props {
    details: {
      bk_cloud_name?: string;
      // 追加部署类单据没有 city_code
      city_code?: string;
      // 手动部署的单据没有 resource_spec
      resource_spec?: {
        [key: string]: {
          affinity: string;
          location_spec?: {
            city: string;
            include_or_exclue?: boolean;
            /** 可用区名称（随机时不传）；历史单据为园区数字 id */
            sub_zone_ids?: Array<number | string>;
          };
        };
      };
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const firstSpec = Object.values(props.details.resource_spec ?? {})[0];
  const affinity = firstSpec?.affinity;
  const zoneIds = firstSpec?.location_spec?.sub_zone_ids;

  const affinityText = affinityMap[affinity as Affinity] || '--';

  // 仅跨可用区 / 指定可用区展示可用区行
  const showZoneItem = computed(() =>
    [Affinity.CROS_SUBZONE, Affinity.SAME_SUBZONE_CROSS_SWTICH].includes(affinity as Affinity),
  );

  const cityName = ref('--');
  const zonesText = ref('--');

  useRequest(getInfrasCities, {
    onSuccess: (cityList) => {
      const cityCode = props.details.city_code;
      const name = cityList.find((item) => item.city_code === cityCode)?.city_name;
      cityName.value = name ?? '--';
    },
  });

  // sub_zone_ids 存可用区标识（历史单据的数字 id 无映射，仅新单据展示）；为空显示「随机」
  if (zoneIds && zoneIds.length > 0) {
    const zoneNames = zoneIds.filter((zoneId) => typeof zoneId === 'string').map((zoneId) => getCloudZoneName(zoneId));
    // 历史单据全是园区数字 id 时无可展示的可用区名
    zonesText.value = zoneNames.join('，') || '--';
  } else if (showZoneItem.value) {
    zonesText.value = t('随机');
  }
</script>

<style lang="less" scoped>
  .ticket-details-info-title {
    font-weight: bold;
  }
</style>
