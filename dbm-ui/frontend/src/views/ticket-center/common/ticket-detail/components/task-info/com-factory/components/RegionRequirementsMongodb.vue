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
      {{ details.bk_cloud_region === 'default' ? t('随机') : details.bk_cloud_region || '--' }}
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

  import { Affinity, getCloudZoneName, mongodbAffinityMap } from '@common/const';

  import InfoList, { Item as InfoItem } from './info-list/Index.vue';

  interface Props {
    details: {
      bk_cloud_name: string;
      /** 新协议：地域标识（随机时 default）；存量单据用 city_code */
      bk_cloud_region?: string;
      resource_spec: {
        [key: string]: {
          affinity: string;
          location_spec: {
            /** 新协议：地域 + 可用区名列表（随机时不传） */
            bk_cloud_region?: string;
            bk_cloud_zone_list?: string[];
            include_or_exclue?: boolean;
          };
        };
      };
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { affinity, location_spec: locationSpec } = Object.values(props.details.resource_spec)[0];
  const zoneList = locationSpec.bk_cloud_zone_list ?? locationSpec.bk_cloud_zone_list;

  const affinityText = mongodbAffinityMap[affinity as Affinity] || '--';

  // 仅跨可用区（强/弱）/ 指定可用区展示可用区行
  const showZoneItem = computed(() =>
    [Affinity.CROSS_SUBZONE_STRONG, Affinity.CROSS_SUBZONE_WEAK, Affinity.SAME_SUBZONE_CROSS_SWTICH].includes(
      affinity as Affinity,
    ),
  );

  const zonesText = ref('--');

  // 可用区名列表（存量单据的园区数字 id 无映射）；为空显示「随机」
  if (zoneList && zoneList.length > 0) {
    const zoneNames = zoneList
      .filter((zoneItem) => typeof zoneItem === 'string')
      .map((zoneItem) => getCloudZoneName(zoneItem));
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
