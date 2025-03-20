<template>
  <div class="ticket-details-info-title mt-20">{{ t('地域要求') }}</div>
  <InfoList>
    <InfoItem :label="t('容灾要求')">
      {{ affinityText }}
    </InfoItem>
    <InfoItem :label="t('地域')">
      {{ cityName }}
    </InfoItem>
    <InfoItem
      v-if="showSubZone"
      :label="t('园区')">
      {{ subZonesText }}
    </InfoItem>
  </InfoList>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasCities, getInfrasSubzonesByCity } from '@services/source/infras';

  import { Affinity, affinityMap } from '@common/const';

  import InfoList, { Item as InfoItem } from './info-list/Index.vue';

  interface Props {
    details: {
      city_code: string;
      resource_spec: {
        [key: string]: {
          affinity: string;
          location_spec: {
            city: string;
            include_or_exclue?: boolean;
            sub_zone_ids?: number[];
          };
        };
      };
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { affinity, location_spec: locationSpec } = Object.values(props.details.resource_spec)[0];
  const { sub_zone_ids: subZoneIds } = locationSpec;
  const showSubZone = subZoneIds && subZoneIds.length > 0;

  const affinityText = affinityMap[affinity as Affinity];

  const cityName = ref('--');
  const subZonesText = ref('--');

  useRequest(getInfrasCities, {
    onSuccess: (cityList) => {
      const cityCode = props.details.city_code;
      const name = cityList.find((item) => item.city_code === cityCode)?.city_name;
      cityName.value = name ?? '--';
    },
  });

  const { run: runGetInfrasSubzonesByCity } = useRequest(getInfrasSubzonesByCity, {
    manual: true,
    onSuccess: (subZoneList) => {
      const subZoneMap = subZoneList.reduce<Record<number, string>>((prevMap, subZoneItem) => {
        return Object.assign(prevMap, { [subZoneItem.bk_sub_zone_id]: subZoneItem.bk_sub_zone });
      }, {});
      if (subZoneIds) {
        subZonesText.value = subZoneIds.map((subZoneId) => subZoneMap[subZoneId]).join('，');
      }
    },
  });

  if (showSubZone) {
    runGetInfrasSubzonesByCity({
      city_code: props.details.city_code,
    });
  } else {
    subZonesText.value = t('随机可用区');
  }
</script>

<style lang="less" scoped>
  .ticket-details-info-title {
    font-weight: bold;
  }
</style>
