<template>
  <Select
    :clearable="false"
    :filter-option="handleSearch"
    filterable
    :input-search="false"
    :model-value="localValue"
    :no-match-text="t('无匹配数据')"
    :placeholder="t('请输入搜索（国家，城市，简称）')"
    :popover-options="{ 'ext-cls': '__bk-date-picker-popover__' }"
    :search-placeholder="t('请输入搜索（国家，城市，简称）')"
    @change="handleChange">
    <template #trigger>
      <div
        id="timezone-picker-trigger"
        class="timezone-picker-trigger-box"
        :class="{'timezone-picker-trigger-box-active': isActive}"
        @click="handleClickTriggerBox">
        <div class="diaplay-content">
          <span class="option-name">{{ isBrowserTimezone ? t('浏览器时区') : '' }} {{ selected.label }}</span>
          <span
            v-show="selected.country"
            v-overflow-tips
            class="option-country">{{ selected.country }}, {{ selected.abbreviation }}</span>
          <span
            v-show="selected.utc"
            class="option-utc">{{ selected.utc }}</span>
        </div>
        <DbIcon
          class="down-icon"
          type="down-big" />
      </div>
    </template>
    <template v-for="group in timezoneData">
      <template v-if="group.label.length < 1">
        <Option
          v-for="item in group.options"
          v-bind="item"
          :id="item.label"
          :key="item.label"
          :name="item.label">
          <div
            class="timezone-picker-option"
            :class="{
              'timezone-picker-option-selected': item.label === localValue,
            }">
            <span class="option-name">{{ t('浏览器时区') }} {{ item.label }}</span>
            <span
              v-overflow-tips
              class="option-country">{{ item.country }}, {{ item.abbreviation }}</span>
            <span class="option-utc">{{ item.utc }}</span>
          </div>
        </Option>
      </template>
      <template v-else>
        <Group
          v-if="group.options.length"
          :key="group.label"
          :label="group.label">
          <Option
            v-for="item in group.options"
            v-bind="item"
            :id="item.label"
            :key="item.label"
            :name="item.label">
            <div
              class="timezone-picker-option"
              :class="{
                'timezone-picker-option-selected': item.label === localValue,
              }">
              <span class="option-name">{{ item.label }}</span>
              <span
                v-overflow-tips
                class="option-country">{{ item.country }}, {{ item.abbreviation }}</span>
              <span class="option-utc">{{ item.utc }}</span>
            </div>
          </Option>
        </Group>
      </template>
    </template>
  </Select>
</template>
<script setup lang="ts">
  import { Select } from 'bkui-vue';
  import dayjs from 'dayjs';
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useTimeZone } from '@stores';

  import { encodeRegexp } from '@utils';

  export interface TimezoneItem {
    abbreviation: string;
    country: string;
    countryCode: string;
    label: string;
    utc: string;
  }

  interface Emits {
    (e: 'change', value: string, info: TimezoneItem): void
  }

  interface TimeZoneGroup {
    label: string;
    options: TimezoneItem[];
  }

  const emits = defineEmits<Emits>();

  const { Option, Group } = Select;

  const timezoneList = [
    {
      label: 'Africa',
      options: [
        {
          label: 'Africa/Abidjan',
          searchIndex:
            'africa/abidjan|gmt|utc|burkina faso|bf|cote d\'ivoire|ci|ghana|gh|gambia|gm|guinea|gn|iceland|is|mali|ml|mauritania|mr|saint helena|sh|sierra leone|sl|senegal|sn|togo|tg',
          value: 'Africa/Abidjan',
        },
        { label: 'Africa/Accra', searchIndex: 'africa/accra|gmt|utc|ghana|gh', value: 'Africa/Accra' },
        {
          label: 'Africa/Addis_Ababa',
          searchIndex: 'africa/addis_ababa|eat|utc+03:00|ethiopia|et',
          value: 'Africa/Addis_Ababa',
        },
        { label: 'Africa/Algiers', searchIndex: 'africa/algiers|cet|utc+01:00|algeria|dz', value: 'Africa/Algiers' },
        { label: 'Africa/Asmara', searchIndex: 'africa/asmara|eat|utc+03:00|eritrea|er', value: 'Africa/Asmara' },
        { label: 'Africa/Bamako', searchIndex: 'africa/bamako|gmt|utc|mali|ml', value: 'Africa/Bamako' },
        {
          label: 'Africa/Bangui',
          searchIndex: 'africa/bangui|wat|utc+01:00|central african republic|cf',
          value: 'Africa/Bangui',
        },
        { label: 'Africa/Banjul', searchIndex: 'africa/banjul|gmt|utc|gambia|gm', value: 'Africa/Banjul' },
        { label: 'Africa/Bissau', searchIndex: 'africa/bissau|gmt|utc|guinea-bissau|gw', value: 'Africa/Bissau' },
        { label: 'Africa/Blantyre', searchIndex: 'africa/blantyre|cat|utc+02:00|malawi|mw', value: 'Africa/Blantyre' },
        {
          label: 'Africa/Brazzaville',
          searchIndex: 'africa/brazzaville|wat|utc+01:00|congo|cg',
          value: 'Africa/Brazzaville',
        },
        {
          label: 'Africa/Bujumbura',
          searchIndex: 'africa/bujumbura|cat|utc+02:00|burundi|bi',
          value: 'Africa/Bujumbura',
        },
        { label: 'Africa/Cairo', searchIndex: 'africa/cairo|eest|utc+03:00|egypt|eg', value: 'Africa/Cairo' },
        {
          label: 'Africa/Casablanca',
          searchIndex: 'africa/casablanca||utc+01:00|morocco|ma',
          value: 'Africa/Casablanca',
        },
        { label: 'Africa/Ceuta', searchIndex: 'africa/ceuta|cest|utc+02:00|spain|es', value: 'Africa/Ceuta' },
        { label: 'Africa/Conakry', searchIndex: 'africa/conakry|gmt|utc|guinea|gn', value: 'Africa/Conakry' },
        { label: 'Africa/Dakar', searchIndex: 'africa/dakar|gmt|utc|senegal|sn', value: 'Africa/Dakar' },
        {
          label: 'Africa/Dar_es_Salaam',
          searchIndex: 'africa/dar_es_salaam|eat|utc+03:00|tanzania|tz',
          value: 'Africa/Dar_es_Salaam',
        },
        { label: 'Africa/Djibouti', searchIndex: 'africa/djibouti|eat|utc+03:00|djibouti|dj', value: 'Africa/Djibouti' },
        { label: 'Africa/Douala', searchIndex: 'africa/douala|wat|utc+01:00|cameroon|cm', value: 'Africa/Douala' },
        {
          label: 'Africa/El_Aaiun',
          searchIndex: 'africa/el_aaiun||utc+01:00|western sahara|eh',
          value: 'Africa/El_Aaiun',
        },
        { label: 'Africa/Freetown', searchIndex: 'africa/freetown|gmt|utc|sierra leone|sl', value: 'Africa/Freetown' },
        { label: 'Africa/Gaborone', searchIndex: 'africa/gaborone|cat|utc+02:00|botswana|bw', value: 'Africa/Gaborone' },
        { label: 'Africa/Harare', searchIndex: 'africa/harare|cat|utc+02:00|zimbabwe|zw', value: 'Africa/Harare' },
        {
          label: 'Africa/Johannesburg',
          searchIndex: 'africa/johannesburg|sast|utc+02:00|lesotho|ls|swaziland|sz|south africa|za',
          value: 'Africa/Johannesburg',
        },
        { label: 'Africa/Kampala', searchIndex: 'africa/kampala|eat|utc+03:00|uganda|ug', value: 'Africa/Kampala' },
        { label: 'Africa/Khartoum', searchIndex: 'africa/khartoum|cat|utc+02:00|sudan|sd', value: 'Africa/Khartoum' },
        { label: 'Africa/Kigali', searchIndex: 'africa/kigali|cat|utc+02:00|rwanda|rw', value: 'Africa/Kigali' },
        {
          label: 'Africa/Kinshasa',
          searchIndex: 'africa/kinshasa|wat|utc+01:00|congo, democratic republic|cd',
          value: 'Africa/Kinshasa',
        },
        {
          label: 'Africa/Lagos',
          searchIndex:
            'africa/lagos|wat|utc+01:00|angola|ao|benin|bj|congo, democratic republic|cd|central african republic|cf|congo|cg|cameroon|cm|gabon|ga|equatorial guinea|gq|niger|ne|nigeria|ng',
          value: 'Africa/Lagos',
        },
        {
          label: 'Africa/Libreville',
          searchIndex: 'africa/libreville|wat|utc+01:00|gabon|ga',
          value: 'Africa/Libreville',
        },
        { label: 'Africa/Lome', searchIndex: 'africa/lome|gmt|utc|togo|tg', value: 'Africa/Lome' },
        { label: 'Africa/Luanda', searchIndex: 'africa/luanda|wat|utc+01:00|angola|ao', value: 'Africa/Luanda' },
        {
          label: 'Africa/Lubumbashi',
          searchIndex: 'africa/lubumbashi|cat|utc+02:00|congo, democratic republic|cd',
          value: 'Africa/Lubumbashi',
        },
        { label: 'Africa/Lusaka', searchIndex: 'africa/lusaka|cat|utc+02:00|zambia|zm', value: 'Africa/Lusaka' },
        {
          label: 'Africa/Malabo',
          searchIndex: 'africa/malabo|wat|utc+01:00|equatorial guinea|gq',
          value: 'Africa/Malabo',
        },
        {
          label: 'Africa/Maputo',
          searchIndex:
            'africa/maputo|cat|utc+02:00|burundi|bi|botswana|bw|congo, democratic republic|cd|malawi|mw|mozambique|mz|rwanda|rw|zambia|zm|zimbabwe|zw',
          value: 'Africa/Maputo',
        },
        { label: 'Africa/Maseru', searchIndex: 'africa/maseru|sast|utc+02:00|lesotho|ls', value: 'Africa/Maseru' },
        { label: 'Africa/Mbabane', searchIndex: 'africa/mbabane|sast|utc+02:00|swaziland|sz', value: 'Africa/Mbabane' },
        {
          label: 'Africa/Mogadishu',
          searchIndex: 'africa/mogadishu|eat|utc+03:00|somalia|so',
          value: 'Africa/Mogadishu',
        },
        { label: 'Africa/Monrovia', searchIndex: 'africa/monrovia|gmt|utc|liberia|lr', value: 'Africa/Monrovia' },
        {
          label: 'Africa/Nairobi',
          searchIndex:
            'africa/nairobi|eat|utc+03:00|djibouti|dj|eritrea|er|ethiopia|et|kenya|ke|comoros|km|madagascar|mg|somalia|so|tanzania|tz|uganda|ug|mayotte|yt',
          value: 'Africa/Nairobi',
        },
        { label: 'Africa/Ndjamena', searchIndex: 'africa/ndjamena|wat|utc+01:00|chad|td', value: 'Africa/Ndjamena' },
        { label: 'Africa/Niamey', searchIndex: 'africa/niamey|wat|utc+01:00|niger|ne', value: 'Africa/Niamey' },
        {
          label: 'Africa/Nouakchott',
          searchIndex: 'africa/nouakchott|gmt|utc|mauritania|mr',
          value: 'Africa/Nouakchott',
        },
        {
          label: 'Africa/Ouagadougou',
          searchIndex: 'africa/ouagadougou|gmt|utc|burkina faso|bf',
          value: 'Africa/Ouagadougou',
        },
        {
          label: 'Africa/Porto-Novo',
          searchIndex: 'africa/porto-novo|wat|utc+01:00|benin|bj',
          value: 'Africa/Porto-Novo',
        },
        {
          label: 'Africa/Sao_Tome',
          searchIndex: 'africa/sao_tome|gmt|utc|sao tome and principe|st',
          value: 'Africa/Sao_Tome',
        },
        {
          label: 'Africa/Tripoli',
          searchIndex: 'africa/tripoli|eet|utc+02:00|libyan arab jamahiriya|ly',
          value: 'Africa/Tripoli',
        },
        { label: 'Africa/Tunis', searchIndex: 'africa/tunis|cet|utc+01:00|tunisia|tn', value: 'Africa/Tunis' },
        { label: 'Africa/Windhoek', searchIndex: 'africa/windhoek|cat|utc+02:00|namibia|na', value: 'Africa/Windhoek' },
      ],
    },
    {
      label: 'America',
      options: [
        { label: 'America/Adak', searchIndex: 'america/adak|hdt|utc-09:00|united states|us', value: 'America/Adak' },
        {
          label: 'America/Anchorage',
          searchIndex: 'america/anchorage|akdt|utc-08:00|united states|us',
          value: 'America/Anchorage',
        },
        {
          label: 'America/Anguilla',
          searchIndex: 'america/anguilla|ast|utc-04:00|anguilla|ai',
          value: 'America/Anguilla',
        },
        {
          label: 'America/Antigua',
          searchIndex: 'america/antigua|ast|utc-04:00|antigua and barbuda|ag',
          value: 'America/Antigua',
        },
        { label: 'America/Araguaina', searchIndex: 'america/araguaina||utc-03:00|brazil|br', value: 'America/Araguaina' },
        {
          label: 'America/Argentina/Buenos_Aires',
          searchIndex: 'america/argentina/buenos_aires||utc-03:00|argentina|ar',
          value: 'America/Argentina/Buenos_Aires',
        },
        {
          label: 'America/Argentina/Catamarca',
          searchIndex: 'america/argentina/catamarca||utc-03:00|argentina|ar',
          value: 'America/Argentina/Catamarca',
        },
        {
          label: 'America/Argentina/Cordoba',
          searchIndex: 'america/argentina/cordoba||utc-03:00|argentina|ar',
          value: 'America/Argentina/Cordoba',
        },
        {
          label: 'America/Argentina/Jujuy',
          searchIndex: 'america/argentina/jujuy||utc-03:00|argentina|ar',
          value: 'America/Argentina/Jujuy',
        },
        {
          label: 'America/Argentina/La_Rioja',
          searchIndex: 'america/argentina/la_rioja||utc-03:00|argentina|ar',
          value: 'America/Argentina/La_Rioja',
        },
        {
          label: 'America/Argentina/Mendoza',
          searchIndex: 'america/argentina/mendoza||utc-03:00|argentina|ar',
          value: 'America/Argentina/Mendoza',
        },
        {
          label: 'America/Argentina/Rio_Gallegos',
          searchIndex: 'america/argentina/rio_gallegos||utc-03:00|argentina|ar',
          value: 'America/Argentina/Rio_Gallegos',
        },
        {
          label: 'America/Argentina/Salta',
          searchIndex: 'america/argentina/salta||utc-03:00|argentina|ar',
          value: 'America/Argentina/Salta',
        },
        {
          label: 'America/Argentina/San_Juan',
          searchIndex: 'america/argentina/san_juan||utc-03:00|argentina|ar',
          value: 'America/Argentina/San_Juan',
        },
        {
          label: 'America/Argentina/San_Luis',
          searchIndex: 'america/argentina/san_luis||utc-03:00|argentina|ar',
          value: 'America/Argentina/San_Luis',
        },
        {
          label: 'America/Argentina/Tucuman',
          searchIndex: 'america/argentina/tucuman||utc-03:00|argentina|ar',
          value: 'America/Argentina/Tucuman',
        },
        {
          label: 'America/Argentina/Ushuaia',
          searchIndex: 'america/argentina/ushuaia||utc-03:00|argentina|ar',
          value: 'America/Argentina/Ushuaia',
        },
        { label: 'America/Aruba', searchIndex: 'america/aruba|ast|utc-04:00|aruba|aw', value: 'America/Aruba' },
        { label: 'America/Asuncion', searchIndex: 'america/asuncion||utc-03:00|paraguay|py', value: 'America/Asuncion' },
        { label: 'America/Atikokan', searchIndex: 'america/atikokan|est|utc-05:00|canada|ca', value: 'America/Atikokan' },
        { label: 'America/Bahia', searchIndex: 'america/bahia||utc-03:00|brazil|br', value: 'America/Bahia' },
        {
          label: 'America/Bahia_Banderas',
          searchIndex: 'america/bahia_banderas|cst|utc-06:00|mexico|mx',
          value: 'America/Bahia_Banderas',
        },
        {
          label: 'America/Barbados',
          searchIndex: 'america/barbados|ast|utc-04:00|barbados|bb',
          value: 'America/Barbados',
        },
        { label: 'America/Belem', searchIndex: 'america/belem||utc-03:00|brazil|br', value: 'America/Belem' },
        { label: 'America/Belize', searchIndex: 'america/belize|cst|utc-06:00|belize|bz', value: 'America/Belize' },
        {
          label: 'America/Blanc-Sablon',
          searchIndex: 'america/blanc-sablon|ast|utc-04:00|canada|ca',
          value: 'America/Blanc-Sablon',
        },
        { label: 'America/Boa_Vista', searchIndex: 'america/boa_vista||utc-04:00|brazil|br', value: 'America/Boa_Vista' },
        { label: 'America/Bogota', searchIndex: 'america/bogota||utc-05:00|colombia|co', value: 'America/Bogota' },
        { label: 'America/Boise', searchIndex: 'america/boise|mdt|utc-06:00|united states|us', value: 'America/Boise' },
        {
          label: 'America/Cambridge_Bay',
          searchIndex: 'america/cambridge_bay|mdt|utc-06:00|canada|ca',
          value: 'America/Cambridge_Bay',
        },
        {
          label: 'America/Campo_Grande',
          searchIndex: 'america/campo_grande||utc-04:00|brazil|br',
          value: 'America/Campo_Grande',
        },
        { label: 'America/Cancun', searchIndex: 'america/cancun|est|utc-05:00|mexico|mx', value: 'America/Cancun' },
        { label: 'America/Caracas', searchIndex: 'america/caracas||utc-04:00|venezuela|ve', value: 'America/Caracas' },
        {
          label: 'America/Cayenne',
          searchIndex: 'america/cayenne||utc-03:00|french guiana|gf',
          value: 'America/Cayenne',
        },
        {
          label: 'America/Cayman',
          searchIndex: 'america/cayman|est|utc-05:00|cayman islands|ky',
          value: 'America/Cayman',
        },
        {
          label: 'America/Chicago',
          searchIndex: 'america/chicago|cdt|utc-05:00|united states|us',
          value: 'America/Chicago',
        },
        {
          label: 'America/Chihuahua',
          searchIndex: 'america/chihuahua|cst|utc-06:00|mexico|mx',
          value: 'America/Chihuahua',
        },
        {
          label: 'America/Ciudad_Juarez',
          searchIndex: 'america/ciudad_juarez|mdt|utc-06:00|mexico|mx',
          value: 'America/Ciudad_Juarez',
        },
        {
          label: 'America/Costa_Rica',
          searchIndex: 'america/costa_rica|cst|utc-06:00|costa rica|cr',
          value: 'America/Costa_Rica',
        },
        { label: 'America/Creston', searchIndex: 'america/creston|mst|utc-07:00|canada|ca', value: 'America/Creston' },
        { label: 'America/Cuiaba', searchIndex: 'america/cuiaba||utc-04:00|brazil|br', value: 'America/Cuiaba' },
        {
          label: 'America/Danmarkshavn',
          searchIndex: 'america/danmarkshavn|gmt|utc|greenland|gl',
          value: 'America/Danmarkshavn',
        },
        { label: 'America/Dawson', searchIndex: 'america/dawson|mst|utc-07:00|canada|ca', value: 'America/Dawson' },
        {
          label: 'America/Dawson_Creek',
          searchIndex: 'america/dawson_creek|mst|utc-07:00|canada|ca',
          value: 'America/Dawson_Creek',
        },
        {
          label: 'America/Denver',
          searchIndex: 'america/denver|mdt|utc-06:00|united states|us',
          value: 'America/Denver',
        },
        {
          label: 'America/Detroit',
          searchIndex: 'america/detroit|edt|utc-04:00|united states|us',
          value: 'America/Detroit',
        },
        {
          label: 'America/Dominica',
          searchIndex: 'america/dominica|ast|utc-04:00|dominica|dm',
          value: 'America/Dominica',
        },
        { label: 'America/Edmonton', searchIndex: 'america/edmonton|mdt|utc-06:00|canada|ca', value: 'America/Edmonton' },
        { label: 'America/Eirunepe', searchIndex: 'america/eirunepe||utc-05:00|brazil|br', value: 'America/Eirunepe' },
        {
          label: 'America/El_Salvador',
          searchIndex: 'america/el_salvador|cst|utc-06:00|el salvador|sv',
          value: 'America/El_Salvador',
        },
        {
          label: 'America/Fort_Nelson',
          searchIndex: 'america/fort_nelson|mst|utc-07:00|canada|ca',
          value: 'America/Fort_Nelson',
        },
        { label: 'America/Fortaleza', searchIndex: 'america/fortaleza||utc-03:00|brazil|br', value: 'America/Fortaleza' },
        {
          label: 'America/Glace_Bay',
          searchIndex: 'america/glace_bay|adt|utc-03:00|canada|ca',
          value: 'America/Glace_Bay',
        },
        {
          label: 'America/Goose_Bay',
          searchIndex: 'america/goose_bay|adt|utc-03:00|canada|ca',
          value: 'America/Goose_Bay',
        },
        {
          label: 'America/Grand_Turk',
          searchIndex: 'america/grand_turk|edt|utc-04:00|turks and caicos islands|tc',
          value: 'America/Grand_Turk',
        },
        { label: 'America/Grenada', searchIndex: 'america/grenada|ast|utc-04:00|grenada|gd', value: 'America/Grenada' },
        {
          label: 'America/Guadeloupe',
          searchIndex: 'america/guadeloupe|ast|utc-04:00|guadeloupe|gp',
          value: 'America/Guadeloupe',
        },
        {
          label: 'America/Guatemala',
          searchIndex: 'america/guatemala|cst|utc-06:00|guatemala|gt',
          value: 'America/Guatemala',
        },
        {
          label: 'America/Guayaquil',
          searchIndex: 'america/guayaquil||utc-05:00|ecuador|ec',
          value: 'America/Guayaquil',
        },
        { label: 'America/Guyana', searchIndex: 'america/guyana||utc-04:00|guyana|gy', value: 'America/Guyana' },
        { label: 'America/Halifax', searchIndex: 'america/halifax|adt|utc-03:00|canada|ca', value: 'America/Halifax' },
        { label: 'America/Havana', searchIndex: 'america/havana|cdt|utc-04:00|cuba|cu', value: 'America/Havana' },
        {
          label: 'America/Hermosillo',
          searchIndex: 'america/hermosillo|mst|utc-07:00|mexico|mx',
          value: 'America/Hermosillo',
        },
        {
          label: 'America/Indiana/Indianapolis',
          searchIndex: 'america/indiana/indianapolis|edt|utc-04:00|united states|us',
          value: 'America/Indiana/Indianapolis',
        },
        {
          label: 'America/Indiana/Knox',
          searchIndex: 'america/indiana/knox|cdt|utc-05:00|united states|us',
          value: 'America/Indiana/Knox',
        },
        {
          label: 'America/Indiana/Marengo',
          searchIndex: 'america/indiana/marengo|edt|utc-04:00|united states|us',
          value: 'America/Indiana/Marengo',
        },
        {
          label: 'America/Indiana/Petersburg',
          searchIndex: 'america/indiana/petersburg|edt|utc-04:00|united states|us',
          value: 'America/Indiana/Petersburg',
        },
        {
          label: 'America/Indiana/Tell_City',
          searchIndex: 'america/indiana/tell_city|cdt|utc-05:00|united states|us',
          value: 'America/Indiana/Tell_City',
        },
        {
          label: 'America/Indiana/Vevay',
          searchIndex: 'america/indiana/vevay|edt|utc-04:00|united states|us',
          value: 'America/Indiana/Vevay',
        },
        {
          label: 'America/Indiana/Vincennes',
          searchIndex: 'america/indiana/vincennes|edt|utc-04:00|united states|us',
          value: 'America/Indiana/Vincennes',
        },
        {
          label: 'America/Indiana/Winamac',
          searchIndex: 'america/indiana/winamac|edt|utc-04:00|united states|us',
          value: 'America/Indiana/Winamac',
        },
        { label: 'America/Inuvik', searchIndex: 'america/inuvik|mdt|utc-06:00|canada|ca', value: 'America/Inuvik' },
        { label: 'America/Iqaluit', searchIndex: 'america/iqaluit|edt|utc-04:00|canada|ca', value: 'America/Iqaluit' },
        { label: 'America/Jamaica', searchIndex: 'america/jamaica|est|utc-05:00|jamaica|jm', value: 'America/Jamaica' },
        {
          label: 'America/Juneau',
          searchIndex: 'america/juneau|akdt|utc-08:00|united states|us',
          value: 'America/Juneau',
        },
        {
          label: 'America/Kentucky/Louisville',
          searchIndex: 'america/kentucky/louisville|edt|utc-04:00|united states|us',
          value: 'America/Kentucky/Louisville',
        },
        {
          label: 'America/Kentucky/Monticello',
          searchIndex: 'america/kentucky/monticello|edt|utc-04:00|united states|us',
          value: 'America/Kentucky/Monticello',
        },
        { label: 'America/La_Paz', searchIndex: 'america/la_paz||utc-04:00|bolivia|bo', value: 'America/La_Paz' },
        { label: 'America/Lima', searchIndex: 'america/lima||utc-05:00|peru|pe', value: 'America/Lima' },
        {
          label: 'America/Los_Angeles',
          searchIndex: 'america/los_angeles|pdt|utc-07:00|united states|us',
          value: 'America/Los_Angeles',
        },
        { label: 'America/Maceio', searchIndex: 'america/maceio||utc-03:00|brazil|br', value: 'America/Maceio' },
        { label: 'America/Managua', searchIndex: 'america/managua|cst|utc-06:00|nicaragua|ni', value: 'America/Managua' },
        { label: 'America/Manaus', searchIndex: 'america/manaus||utc-04:00|brazil|br', value: 'America/Manaus' },
        {
          label: 'America/Marigot',
          searchIndex: 'america/marigot|ast|utc-04:00|saint martin|mf',
          value: 'America/Marigot',
        },
        {
          label: 'America/Martinique',
          searchIndex: 'america/martinique|ast|utc-04:00|martinique|mq',
          value: 'America/Martinique',
        },
        {
          label: 'America/Matamoros',
          searchIndex: 'america/matamoros|cdt|utc-05:00|mexico|mx',
          value: 'America/Matamoros',
        },
        { label: 'America/Mazatlan', searchIndex: 'america/mazatlan|mst|utc-07:00|mexico|mx', value: 'America/Mazatlan' },
        {
          label: 'America/Menominee',
          searchIndex: 'america/menominee|cdt|utc-05:00|united states|us',
          value: 'America/Menominee',
        },
        { label: 'America/Merida', searchIndex: 'america/merida|cst|utc-06:00|mexico|mx', value: 'America/Merida' },
        {
          label: 'America/Metlakatla',
          searchIndex: 'america/metlakatla|akdt|utc-08:00|united states|us',
          value: 'America/Metlakatla',
        },
        {
          label: 'America/Mexico_City',
          searchIndex: 'america/mexico_city|cst|utc-06:00|mexico|mx',
          value: 'America/Mexico_City',
        },
        {
          label: 'America/Miquelon',
          searchIndex: 'america/miquelon||utc-02:00|saint pierre and miquelon|pm',
          value: 'America/Miquelon',
        },
        { label: 'America/Moncton', searchIndex: 'america/moncton|adt|utc-03:00|canada|ca', value: 'America/Moncton' },
        {
          label: 'America/Monterrey',
          searchIndex: 'america/monterrey|cst|utc-06:00|mexico|mx',
          value: 'America/Monterrey',
        },
        {
          label: 'America/Montevideo',
          searchIndex: 'america/montevideo||utc-03:00|uruguay|uy',
          value: 'America/Montevideo',
        },
        {
          label: 'America/Montserrat',
          searchIndex: 'america/montserrat|ast|utc-04:00|montserrat|ms',
          value: 'America/Montserrat',
        },
        { label: 'America/Nassau', searchIndex: 'america/nassau|edt|utc-04:00|bahamas|bs', value: 'America/Nassau' },
        {
          label: 'America/New_York',
          searchIndex: 'america/new_york|edt|utc-04:00|united states|us',
          value: 'America/New_York',
        },
        { label: 'America/Nome', searchIndex: 'america/nome|akdt|utc-08:00|united states|us', value: 'America/Nome' },
        { label: 'America/Noronha', searchIndex: 'america/noronha||utc-02:00|brazil|br', value: 'America/Noronha' },
        {
          label: 'America/North_Dakota/Beulah',
          searchIndex: 'america/north_dakota/beulah|cdt|utc-05:00|united states|us',
          value: 'America/North_Dakota/Beulah',
        },
        {
          label: 'America/North_Dakota/Center',
          searchIndex: 'america/north_dakota/center|cdt|utc-05:00|united states|us',
          value: 'America/North_Dakota/Center',
        },
        {
          label: 'America/North_Dakota/New_Salem',
          searchIndex: 'america/north_dakota/new_salem|cdt|utc-05:00|united states|us',
          value: 'America/North_Dakota/New_Salem',
        },
        { label: 'America/Nuuk', searchIndex: 'america/nuuk||utc-02:00|greenland|gl', value: 'America/Nuuk' },
        { label: 'America/Ojinaga', searchIndex: 'america/ojinaga|cdt|utc-05:00|mexico|mx', value: 'America/Ojinaga' },
        {
          label: 'America/Panama',
          searchIndex: 'america/panama|est|utc-05:00|canada|ca|cayman islands|ky|panama|pa',
          value: 'America/Panama',
        },
        {
          label: 'America/Paramaribo',
          searchIndex: 'america/paramaribo||utc-03:00|suriname|sr',
          value: 'America/Paramaribo',
        },
        {
          label: 'America/Phoenix',
          searchIndex: 'america/phoenix|mst|utc-07:00|canada|ca|united states|us',
          value: 'America/Phoenix',
        },
        {
          label: 'America/Port-au-Prince',
          searchIndex: 'america/port-au-prince|edt|utc-04:00|haiti|ht',
          value: 'America/Port-au-Prince',
        },
        {
          label: 'America/Port_of_Spain',
          searchIndex: 'america/port_of_spain|ast|utc-04:00|trinidad and tobago|tt',
          value: 'America/Port_of_Spain',
        },
        {
          label: 'America/Porto_Velho',
          searchIndex: 'america/porto_velho||utc-04:00|brazil|br',
          value: 'America/Porto_Velho',
        },
        {
          label: 'America/Puerto_Rico',
          searchIndex:
            'america/puerto_rico|ast|utc-04:00|antigua and barbuda|ag|anguilla|ai|aruba|aw|saint barthelemy|bl|canada|ca|dominica|dm|grenada|gd|guadeloupe|gp|saint kitts and nevis|kn|saint lucia|lc|saint martin|mf|montserrat|ms|puerto rico|pr|trinidad and tobago|tt|saint vincent and grenadines|vc|virgin islands, british|vg|virgin islands, u.s.|vi',
          value: 'America/Puerto_Rico',
        },
        {
          label: 'America/Punta_Arenas',
          searchIndex: 'america/punta_arenas||utc-03:00|chile|cl',
          value: 'America/Punta_Arenas',
        },
        {
          label: 'America/Rankin_Inlet',
          searchIndex: 'america/rankin_inlet|cdt|utc-05:00|canada|ca',
          value: 'America/Rankin_Inlet',
        },
        { label: 'America/Recife', searchIndex: 'america/recife||utc-03:00|brazil|br', value: 'America/Recife' },
        { label: 'America/Regina', searchIndex: 'america/regina|cst|utc-06:00|canada|ca', value: 'America/Regina' },
        { label: 'America/Resolute', searchIndex: 'america/resolute|cdt|utc-05:00|canada|ca', value: 'America/Resolute' },
        {
          label: 'America/Rio_Branco',
          searchIndex: 'america/rio_branco||utc-05:00|brazil|br',
          value: 'America/Rio_Branco',
        },
        { label: 'America/Santarem', searchIndex: 'america/santarem||utc-03:00|brazil|br', value: 'America/Santarem' },
        { label: 'America/Santiago', searchIndex: 'america/santiago||utc-03:00|chile|cl', value: 'America/Santiago' },
        {
          label: 'America/Santo_Domingo',
          searchIndex: 'america/santo_domingo|ast|utc-04:00|dominican republic|do',
          value: 'America/Santo_Domingo',
        },
        { label: 'America/Sao_Paulo', searchIndex: 'america/sao_paulo||utc-03:00|brazil|br', value: 'America/Sao_Paulo' },
        {
          label: 'America/Scoresbysund',
          searchIndex: 'america/scoresbysund||utc|greenland|gl',
          value: 'America/Scoresbysund',
        },
        { label: 'America/Sitka', searchIndex: 'america/sitka|akdt|utc-08:00|united states|us', value: 'America/Sitka' },
        {
          label: 'America/St_Barthelemy',
          searchIndex: 'america/st_barthelemy|ast|utc-04:00|saint barthelemy|bl',
          value: 'America/St_Barthelemy',
        },
        { label: 'America/St_Johns', searchIndex: 'america/st_johns|ndt|utc-02:30|canada|ca', value: 'America/St_Johns' },
        {
          label: 'America/St_Kitts',
          searchIndex: 'america/st_kitts|ast|utc-04:00|saint kitts and nevis|kn',
          value: 'America/St_Kitts',
        },
        {
          label: 'America/St_Lucia',
          searchIndex: 'america/st_lucia|ast|utc-04:00|saint lucia|lc',
          value: 'America/St_Lucia',
        },
        {
          label: 'America/St_Thomas',
          searchIndex: 'america/st_thomas|ast|utc-04:00|virgin islands, u.s.|vi',
          value: 'America/St_Thomas',
        },
        {
          label: 'America/St_Vincent',
          searchIndex: 'america/st_vincent|ast|utc-04:00|saint vincent and grenadines|vc',
          value: 'America/St_Vincent',
        },
        {
          label: 'America/Swift_Current',
          searchIndex: 'america/swift_current|cst|utc-06:00|canada|ca',
          value: 'America/Swift_Current',
        },
        {
          label: 'America/Tegucigalpa',
          searchIndex: 'america/tegucigalpa|cst|utc-06:00|honduras|hn',
          value: 'America/Tegucigalpa',
        },
        { label: 'America/Thule', searchIndex: 'america/thule|adt|utc-03:00|greenland|gl', value: 'America/Thule' },
        { label: 'America/Tijuana', searchIndex: 'america/tijuana|pdt|utc-07:00|mexico|mx', value: 'America/Tijuana' },
        {
          label: 'America/Toronto',
          searchIndex: 'america/toronto|edt|utc-04:00|bahamas|bs|canada|ca',
          value: 'America/Toronto',
        },
        {
          label: 'America/Tortola',
          searchIndex: 'america/tortola|ast|utc-04:00|virgin islands, british|vg',
          value: 'America/Tortola',
        },
        {
          label: 'America/Vancouver',
          searchIndex: 'america/vancouver|pdt|utc-07:00|canada|ca',
          value: 'America/Vancouver',
        },
        {
          label: 'America/Whitehorse',
          searchIndex: 'america/whitehorse|mst|utc-07:00|canada|ca',
          value: 'America/Whitehorse',
        },
        { label: 'America/Winnipeg', searchIndex: 'america/winnipeg|cdt|utc-05:00|canada|ca', value: 'America/Winnipeg' },
        {
          label: 'America/Yakutat',
          searchIndex: 'america/yakutat|akdt|utc-08:00|united states|us',
          value: 'America/Yakutat',
        },
      ],
    },
    {
      label: 'Antarctica',
      options: [
        {
          label: 'Antarctica/Casey',
          searchIndex: 'antarctica/casey||utc+11:00|antarctica|aq',
          value: 'Antarctica/Casey',
        },
        {
          label: 'Antarctica/Davis',
          searchIndex: 'antarctica/davis||utc+07:00|antarctica|aq',
          value: 'Antarctica/Davis',
        },
        {
          label: 'Antarctica/DumontDUrville',
          searchIndex: 'antarctica/dumontdurville||utc+10:00|antarctica|aq',
          value: 'Antarctica/DumontDUrville',
        },
        {
          label: 'Antarctica/Macquarie',
          searchIndex: 'antarctica/macquarie|aedt|utc+11:00|australia|au',
          value: 'Antarctica/Macquarie',
        },
        {
          label: 'Antarctica/Mawson',
          searchIndex: 'antarctica/mawson||utc+05:00|antarctica|aq',
          value: 'Antarctica/Mawson',
        },
        {
          label: 'Antarctica/McMurdo',
          searchIndex: 'antarctica/mcmurdo|nzdt|utc+13:00|antarctica|aq',
          value: 'Antarctica/McMurdo',
        },
        {
          label: 'Antarctica/Palmer',
          searchIndex: 'antarctica/palmer||utc-03:00|antarctica|aq',
          value: 'Antarctica/Palmer',
        },
        {
          label: 'Antarctica/Rothera',
          searchIndex: 'antarctica/rothera||utc-03:00|antarctica|aq',
          value: 'Antarctica/Rothera',
        },
        {
          label: 'Antarctica/Syowa',
          searchIndex: 'antarctica/syowa||utc+03:00|antarctica|aq',
          value: 'Antarctica/Syowa',
        },
        {
          label: 'Antarctica/Troll',
          searchIndex: 'antarctica/troll||utc+02:00|antarctica|aq',
          value: 'Antarctica/Troll',
        },
        {
          label: 'Antarctica/Vostok',
          searchIndex: 'antarctica/vostok||utc+06:00|antarctica|aq',
          value: 'Antarctica/Vostok',
        },
      ],
    },
    {
      label: 'Arctic',
      options: [
        {
          label: 'Arctic/Longyearbyen',
          searchIndex: 'arctic/longyearbyen|cest|utc+02:00|svalbard and jan mayen|sj',
          value: 'Arctic/Longyearbyen',
        },
      ],
    },
    {
      label: 'Asia',
      options: [
        { label: 'Asia/Aden', searchIndex: 'asia/aden||utc+03:00|yemen|ye', value: 'Asia/Aden' },
        { label: 'Asia/Almaty', searchIndex: 'asia/almaty||utc+06:00|kazakhstan|kz', value: 'Asia/Almaty' },
        { label: 'Asia/Amman', searchIndex: 'asia/amman||utc+03:00|jordan|jo', value: 'Asia/Amman' },
        { label: 'Asia/Anadyr', searchIndex: 'asia/anadyr||utc+12:00|russian federation|ru', value: 'Asia/Anadyr' },
        { label: 'Asia/Aqtau', searchIndex: 'asia/aqtau||utc+05:00|kazakhstan|kz', value: 'Asia/Aqtau' },
        { label: 'Asia/Aqtobe', searchIndex: 'asia/aqtobe||utc+05:00|kazakhstan|kz', value: 'Asia/Aqtobe' },
        { label: 'Asia/Ashgabat', searchIndex: 'asia/ashgabat||utc+05:00|turkmenistan|tm', value: 'Asia/Ashgabat' },
        { label: 'Asia/Atyrau', searchIndex: 'asia/atyrau||utc+05:00|kazakhstan|kz', value: 'Asia/Atyrau' },
        { label: 'Asia/Baghdad', searchIndex: 'asia/baghdad||utc+03:00|iraq|iq', value: 'Asia/Baghdad' },
        { label: 'Asia/Bahrain', searchIndex: 'asia/bahrain||utc+03:00|bahrain|bh', value: 'Asia/Bahrain' },
        { label: 'Asia/Baku', searchIndex: 'asia/baku||utc+04:00|azerbaijan|az', value: 'Asia/Baku' },
        {
          label: 'Asia/Bangkok',
          searchIndex:
            'asia/bangkok||utc+07:00|christmas island|cx|cambodia|kh|lao people\'s democratic republic|la|thailand|th|viet nam|vn',
          value: 'Asia/Bangkok',
        },
        { label: 'Asia/Barnaul', searchIndex: 'asia/barnaul||utc+07:00|russian federation|ru', value: 'Asia/Barnaul' },
        { label: 'Asia/Beirut', searchIndex: 'asia/beirut|eest|utc+03:00|lebanon|lb', value: 'Asia/Beirut' },
        { label: 'Asia/Bishkek', searchIndex: 'asia/bishkek||utc+06:00|kyrgyzstan|kg', value: 'Asia/Bishkek' },
        { label: 'Asia/Brunei', searchIndex: 'asia/brunei||utc+08:00|brunei darussalam|bn', value: 'Asia/Brunei' },
        { label: 'Asia/Chita', searchIndex: 'asia/chita||utc+09:00|russian federation|ru', value: 'Asia/Chita' },
        { label: 'Asia/Choibalsan', searchIndex: 'asia/choibalsan||utc+08:00|mongolia|mn', value: 'Asia/Choibalsan' },
        { label: 'Asia/Colombo', searchIndex: 'asia/colombo||utc+05:30|sri lanka|lk', value: 'Asia/Colombo' },
        {
          label: 'Asia/Damascus',
          searchIndex: 'asia/damascus||utc+03:00|syrian arab republic|sy',
          value: 'Asia/Damascus',
        },
        { label: 'Asia/Dhaka', searchIndex: 'asia/dhaka||utc+06:00|bangladesh|bd', value: 'Asia/Dhaka' },
        { label: 'Asia/Dili', searchIndex: 'asia/dili||utc+09:00|timor-leste|tl', value: 'Asia/Dili' },
        {
          label: 'Asia/Dubai',
          searchIndex:
            'asia/dubai||utc+04:00|united arab emirates|ae|oman|om|reunion|re|seychelles|sc|french southern territories|tf',
          value: 'Asia/Dubai',
        },
        { label: 'Asia/Dushanbe', searchIndex: 'asia/dushanbe||utc+05:00|tajikistan|tj', value: 'Asia/Dushanbe' },
        { label: 'Asia/Famagusta', searchIndex: 'asia/famagusta|eest|utc+03:00|cyprus|cy', value: 'Asia/Famagusta' },
        { label: 'Asia/Gaza', searchIndex: 'asia/gaza|eest|utc+03:00|palestine, state of|ps', value: 'Asia/Gaza' },
        { label: 'Asia/Hebron', searchIndex: 'asia/hebron|eest|utc+03:00|palestine, state of|ps', value: 'Asia/Hebron' },
        { label: 'Asia/Ho_Chi_Minh', searchIndex: 'asia/ho_chi_minh||utc+07:00|viet nam|vn', value: 'Asia/Ho_Chi_Minh' },
        { label: 'Asia/Hong_Kong', searchIndex: 'asia/hong_kong|hkt|utc+08:00|hong kong|hk', value: 'Asia/Hong_Kong' },
        { label: 'Asia/Hovd', searchIndex: 'asia/hovd||utc+07:00|mongolia|mn', value: 'Asia/Hovd' },
        { label: 'Asia/Irkutsk', searchIndex: 'asia/irkutsk||utc+08:00|russian federation|ru', value: 'Asia/Irkutsk' },
        { label: 'Asia/Jakarta', searchIndex: 'asia/jakarta|wib|utc+07:00|indonesia|id', value: 'Asia/Jakarta' },
        { label: 'Asia/Jayapura', searchIndex: 'asia/jayapura|wit|utc+09:00|indonesia|id', value: 'Asia/Jayapura' },
        { label: 'Asia/Jerusalem', searchIndex: 'asia/jerusalem|idt|utc+03:00|israel|il', value: 'Asia/Jerusalem' },
        { label: 'Asia/Kabul', searchIndex: 'asia/kabul||utc+04:30|afghanistan|af', value: 'Asia/Kabul' },
        {
          label: 'Asia/Kamchatka',
          searchIndex: 'asia/kamchatka||utc+12:00|russian federation|ru',
          value: 'Asia/Kamchatka',
        },
        { label: 'Asia/Karachi', searchIndex: 'asia/karachi|pkt|utc+05:00|pakistan|pk', value: 'Asia/Karachi' },
        { label: 'Asia/Kathmandu', searchIndex: 'asia/kathmandu||utc+05:45|nepal|np', value: 'Asia/Kathmandu' },
        { label: 'Asia/Khandyga', searchIndex: 'asia/khandyga||utc+09:00|russian federation|ru', value: 'Asia/Khandyga' },
        { label: 'Asia/Kolkata', searchIndex: 'asia/kolkata|ist|utc+05:30|india|in', value: 'Asia/Kolkata' },
        {
          label: 'Asia/Krasnoyarsk',
          searchIndex: 'asia/krasnoyarsk||utc+07:00|russian federation|ru',
          value: 'Asia/Krasnoyarsk',
        },
        {
          label: 'Asia/Kuala_Lumpur',
          searchIndex: 'asia/kuala_lumpur||utc+08:00|malaysia|my',
          value: 'Asia/Kuala_Lumpur',
        },
        {
          label: 'Asia/Kuching',
          searchIndex: 'asia/kuching||utc+08:00|brunei darussalam|bn|malaysia|my',
          value: 'Asia/Kuching',
        },
        { label: 'Asia/Kuwait', searchIndex: 'asia/kuwait||utc+03:00|kuwait|kw', value: 'Asia/Kuwait' },
        { label: 'Asia/Macau', searchIndex: 'asia/macau|cst|utc+08:00|macao|mo', value: 'Asia/Macau' },
        { label: 'Asia/Magadan', searchIndex: 'asia/magadan||utc+11:00|russian federation|ru', value: 'Asia/Magadan' },
        { label: 'Asia/Makassar', searchIndex: 'asia/makassar|wita|utc+08:00|indonesia|id', value: 'Asia/Makassar' },
        { label: 'Asia/Manila', searchIndex: 'asia/manila|pst|utc+08:00|philippines|ph', value: 'Asia/Manila' },
        { label: 'Asia/Muscat', searchIndex: 'asia/muscat||utc+04:00|oman|om', value: 'Asia/Muscat' },
        { label: 'Asia/Nicosia', searchIndex: 'asia/nicosia|eest|utc+03:00|cyprus|cy', value: 'Asia/Nicosia' },
        {
          label: 'Asia/Novokuznetsk',
          searchIndex: 'asia/novokuznetsk||utc+07:00|russian federation|ru',
          value: 'Asia/Novokuznetsk',
        },
        {
          label: 'Asia/Novosibirsk',
          searchIndex: 'asia/novosibirsk||utc+07:00|russian federation|ru',
          value: 'Asia/Novosibirsk',
        },
        { label: 'Asia/Omsk', searchIndex: 'asia/omsk||utc+06:00|russian federation|ru', value: 'Asia/Omsk' },
        { label: 'Asia/Oral', searchIndex: 'asia/oral||utc+05:00|kazakhstan|kz', value: 'Asia/Oral' },
        { label: 'Asia/Phnom_Penh', searchIndex: 'asia/phnom_penh||utc+07:00|cambodia|kh', value: 'Asia/Phnom_Penh' },
        { label: 'Asia/Pontianak', searchIndex: 'asia/pontianak|wib|utc+07:00|indonesia|id', value: 'Asia/Pontianak' },
        { label: 'Asia/Qatar', searchIndex: 'asia/qatar||utc+03:00|bahrain|bh|qatar|qa', value: 'Asia/Qatar' },
        { label: 'Asia/Qostanay', searchIndex: 'asia/qostanay||utc+06:00|kazakhstan|kz', value: 'Asia/Qostanay' },
        { label: 'Asia/Qyzylorda', searchIndex: 'asia/qyzylorda||utc+05:00|kazakhstan|kz', value: 'Asia/Qyzylorda' },
        {
          label: 'Asia/Riyadh',
          searchIndex: 'asia/riyadh||utc+03:00|antarctica|aq|kuwait|kw|saudi arabia|sa|yemen|ye',
          value: 'Asia/Riyadh',
        },
        { label: 'Asia/Sakhalin', searchIndex: 'asia/sakhalin||utc+11:00|russian federation|ru', value: 'Asia/Sakhalin' },
        { label: 'Asia/Samarkand', searchIndex: 'asia/samarkand||utc+05:00|uzbekistan|uz', value: 'Asia/Samarkand' },
        { label: 'Asia/Seoul', searchIndex: 'asia/seoul|kst|utc+09:00|korea|kr', value: 'Asia/Seoul' },
        { label: 'Asia/Shanghai', searchIndex: 'asia/shanghai|cst|utc+08:00|china|cn', value: 'Asia/Shanghai' },
        {
          label: 'Asia/Singapore',
          searchIndex: 'asia/singapore||utc+08:00|malaysia|my|singapore|sg',
          value: 'Asia/Singapore',
        },
        {
          label: 'Asia/Srednekolymsk',
          searchIndex: 'asia/srednekolymsk||utc+11:00|russian federation|ru',
          value: 'Asia/Srednekolymsk',
        },
        { label: 'Asia/Taipei', searchIndex: 'asia/taipei|cst|utc+08:00|taiwan|tw', value: 'Asia/Taipei' },
        { label: 'Asia/Tashkent', searchIndex: 'asia/tashkent||utc+05:00|uzbekistan|uz', value: 'Asia/Tashkent' },
        { label: 'Asia/Tbilisi', searchIndex: 'asia/tbilisi||utc+04:00|georgia|ge', value: 'Asia/Tbilisi' },
        {
          label: 'Asia/Tehran',
          searchIndex: 'asia/tehran||utc+03:30|iran (islamic republic of)|ir',
          value: 'Asia/Tehran',
        },
        { label: 'Asia/Thimphu', searchIndex: 'asia/thimphu||utc+06:00|bhutan|bt', value: 'Asia/Thimphu' },
        { label: 'Asia/Tokyo', searchIndex: 'asia/tokyo|jst|utc+09:00|japan|jp', value: 'Asia/Tokyo' },
        { label: 'Asia/Tomsk', searchIndex: 'asia/tomsk||utc+07:00|russian federation|ru', value: 'Asia/Tomsk' },
        { label: 'Asia/Ulaanbaatar', searchIndex: 'asia/ulaanbaatar||utc+08:00|mongolia|mn', value: 'Asia/Ulaanbaatar' },
        { label: 'Asia/Urumqi', searchIndex: 'asia/urumqi||utc+06:00|antarctica|aq|china|cn', value: 'Asia/Urumqi' },
        { label: 'Asia/Ust-Nera', searchIndex: 'asia/ust-nera||utc+10:00|russian federation|ru', value: 'Asia/Ust-Nera' },
        {
          label: 'Asia/Vientiane',
          searchIndex: 'asia/vientiane||utc+07:00|lao people\'s democratic republic|la',
          value: 'Asia/Vientiane',
        },
        {
          label: 'Asia/Vladivostok',
          searchIndex: 'asia/vladivostok||utc+10:00|russian federation|ru',
          value: 'Asia/Vladivostok',
        },
        { label: 'Asia/Yakutsk', searchIndex: 'asia/yakutsk||utc+09:00|russian federation|ru', value: 'Asia/Yakutsk' },
        {
          label: 'Asia/Yangon',
          searchIndex: 'asia/yangon||utc+06:30|cocos (keeling) islands|cc|myanmar|mm',
          value: 'Asia/Yangon',
        },
        {
          label: 'Asia/Yekaterinburg',
          searchIndex: 'asia/yekaterinburg||utc+05:00|russian federation|ru',
          value: 'Asia/Yekaterinburg',
        },
        { label: 'Asia/Yerevan', searchIndex: 'asia/yerevan||utc+04:00|armenia|am', value: 'Asia/Yerevan' },
      ],
    },
    {
      label: 'Atlantic',
      options: [
        { label: 'Atlantic/Azores', searchIndex: 'atlantic/azores||utc|portugal|pt', value: 'Atlantic/Azores' },
        {
          label: 'Atlantic/Bermuda',
          searchIndex: 'atlantic/bermuda|adt|utc-03:00|bermuda|bm',
          value: 'Atlantic/Bermuda',
        },
        { label: 'Atlantic/Canary', searchIndex: 'atlantic/canary|west|utc+01:00|spain|es', value: 'Atlantic/Canary' },
        {
          label: 'Atlantic/Cape_Verde',
          searchIndex: 'atlantic/cape_verde||utc-01:00|cape verde|cv',
          value: 'Atlantic/Cape_Verde',
        },
        {
          label: 'Atlantic/Faroe',
          searchIndex: 'atlantic/faroe|west|utc+01:00|faroe islands|fo',
          value: 'Atlantic/Faroe',
        },
        {
          label: 'Atlantic/Madeira',
          searchIndex: 'atlantic/madeira|west|utc+01:00|portugal|pt',
          value: 'Atlantic/Madeira',
        },
        {
          label: 'Atlantic/Reykjavik',
          searchIndex: 'atlantic/reykjavik|gmt|utc|iceland|is',
          value: 'Atlantic/Reykjavik',
        },
        {
          label: 'Atlantic/South_Georgia',
          searchIndex: 'atlantic/south_georgia||utc-02:00|south georgia and sandwich isl.|gs',
          value: 'Atlantic/South_Georgia',
        },
        {
          label: 'Atlantic/St_Helena',
          searchIndex: 'atlantic/st_helena|gmt|utc|saint helena|sh',
          value: 'Atlantic/St_Helena',
        },
        {
          label: 'Atlantic/Stanley',
          searchIndex: 'atlantic/stanley||utc-03:00|falkland islands (malvinas)|fk',
          value: 'Atlantic/Stanley',
        },
      ],
    },
    {
      label: 'Australia',
      options: [
        {
          label: 'Australia/Adelaide',
          searchIndex: 'australia/adelaide|acdt|utc+10:30|australia|au',
          value: 'Australia/Adelaide',
        },
        {
          label: 'Australia/Brisbane',
          searchIndex: 'australia/brisbane|aest|utc+10:00|australia|au',
          value: 'Australia/Brisbane',
        },
        {
          label: 'Australia/Broken_Hill',
          searchIndex: 'australia/broken_hill|acdt|utc+10:30|australia|au',
          value: 'Australia/Broken_Hill',
        },
        {
          label: 'Australia/Darwin',
          searchIndex: 'australia/darwin|acst|utc+09:30|australia|au',
          value: 'Australia/Darwin',
        },
        { label: 'Australia/Eucla', searchIndex: 'australia/eucla||utc+08:45|australia|au', value: 'Australia/Eucla' },
        {
          label: 'Australia/Hobart',
          searchIndex: 'australia/hobart|aedt|utc+11:00|australia|au',
          value: 'Australia/Hobart',
        },
        {
          label: 'Australia/Lindeman',
          searchIndex: 'australia/lindeman|aest|utc+10:00|australia|au',
          value: 'Australia/Lindeman',
        },
        {
          label: 'Australia/Lord_Howe',
          searchIndex: 'australia/lord_howe||utc+11:00|australia|au',
          value: 'Australia/Lord_Howe',
        },
        {
          label: 'Australia/Melbourne',
          searchIndex: 'australia/melbourne|aedt|utc+11:00|australia|au',
          value: 'Australia/Melbourne',
        },
        {
          label: 'Australia/Perth',
          searchIndex: 'australia/perth|awst|utc+08:00|australia|au',
          value: 'Australia/Perth',
        },
        {
          label: 'Australia/Sydney',
          searchIndex: 'australia/sydney|aedt|utc+11:00|australia|au',
          value: 'Australia/Sydney',
        },
      ],
    },
    {
      label: 'Europe',
      options: [
        {
          label: 'Europe/Amsterdam',
          searchIndex: 'europe/amsterdam|cest|utc+02:00|netherlands|nl',
          value: 'Europe/Amsterdam',
        },
        { label: 'Europe/Andorra', searchIndex: 'europe/andorra|cest|utc+02:00|andorra|ad', value: 'Europe/Andorra' },
        {
          label: 'Europe/Astrakhan',
          searchIndex: 'europe/astrakhan||utc+04:00|russian federation|ru',
          value: 'Europe/Astrakhan',
        },
        { label: 'Europe/Athens', searchIndex: 'europe/athens|eest|utc+03:00|greece|gr', value: 'Europe/Athens' },
        {
          label: 'Europe/Belgrade',
          searchIndex:
            'europe/belgrade|cest|utc+02:00|bosnia and herzegovina|ba|croatia|hr|montenegro|me|macedonia|mk|serbia|rs|slovenia|si',
          value: 'Europe/Belgrade',
        },
        {
          label: 'Europe/Berlin',
          searchIndex: 'europe/berlin|cest|utc+02:00|germany|de|denmark|dk|norway|no|sweden|se|svalbard and jan mayen|sj',
          value: 'Europe/Berlin',
        },
        {
          label: 'Europe/Bratislava',
          searchIndex: 'europe/bratislava|cest|utc+02:00|slovakia|sk',
          value: 'Europe/Bratislava',
        },
        {
          label: 'Europe/Brussels',
          searchIndex: 'europe/brussels|cest|utc+02:00|belgium|be|luxembourg|lu|netherlands|nl',
          value: 'Europe/Brussels',
        },
        {
          label: 'Europe/Bucharest',
          searchIndex: 'europe/bucharest|eest|utc+03:00|romania|ro',
          value: 'Europe/Bucharest',
        },
        { label: 'Europe/Budapest', searchIndex: 'europe/budapest|cest|utc+02:00|hungary|hu', value: 'Europe/Budapest' },
        { label: 'Europe/Busingen', searchIndex: 'europe/busingen|cest|utc+02:00|germany|de', value: 'Europe/Busingen' },
        { label: 'Europe/Chisinau', searchIndex: 'europe/chisinau|eest|utc+03:00|moldova|md', value: 'Europe/Chisinau' },
        {
          label: 'Europe/Copenhagen',
          searchIndex: 'europe/copenhagen|cest|utc+02:00|denmark|dk',
          value: 'Europe/Copenhagen',
        },
        { label: 'Europe/Dublin', searchIndex: 'europe/dublin|ist|utc+01:00|ireland|ie', value: 'Europe/Dublin' },
        {
          label: 'Europe/Gibraltar',
          searchIndex: 'europe/gibraltar|cest|utc+02:00|gibraltar|gi',
          value: 'Europe/Gibraltar',
        },
        { label: 'Europe/Guernsey', searchIndex: 'europe/guernsey|bst|utc+01:00|guernsey|gg', value: 'Europe/Guernsey' },
        {
          label: 'Europe/Helsinki',
          searchIndex: 'europe/helsinki|eest|utc+03:00|aland islands|ax|finland|fi',
          value: 'Europe/Helsinki',
        },
        {
          label: 'Europe/Isle_of_Man',
          searchIndex: 'europe/isle_of_man|bst|utc+01:00|isle of man|im',
          value: 'Europe/Isle_of_Man',
        },
        { label: 'Europe/Istanbul', searchIndex: 'europe/istanbul||utc+03:00|turkey|tr', value: 'Europe/Istanbul' },
        { label: 'Europe/Jersey', searchIndex: 'europe/jersey|bst|utc+01:00|jersey|je', value: 'Europe/Jersey' },
        {
          label: 'Europe/Kaliningrad',
          searchIndex: 'europe/kaliningrad|eet|utc+02:00|russian federation|ru',
          value: 'Europe/Kaliningrad',
        },
        { label: 'Europe/Kirov', searchIndex: 'europe/kirov|msk|utc+03:00|russian federation|ru', value: 'Europe/Kirov' },
        { label: 'Europe/Kyiv', searchIndex: 'europe/kyiv|eest|utc+03:00|ukraine|ua', value: 'Europe/Kyiv' },
        { label: 'Europe/Lisbon', searchIndex: 'europe/lisbon|west|utc+01:00|portugal|pt', value: 'Europe/Lisbon' },
        {
          label: 'Europe/Ljubljana',
          searchIndex: 'europe/ljubljana|cest|utc+02:00|slovenia|si',
          value: 'Europe/Ljubljana',
        },
        {
          label: 'Europe/London',
          searchIndex: 'europe/london|bst|utc+01:00|united kingdom|gb|guernsey|gg|isle of man|im|jersey|je',
          value: 'Europe/London',
        },
        {
          label: 'Europe/Luxembourg',
          searchIndex: 'europe/luxembourg|cest|utc+02:00|luxembourg|lu',
          value: 'Europe/Luxembourg',
        },
        { label: 'Europe/Madrid', searchIndex: 'europe/madrid|cest|utc+02:00|spain|es', value: 'Europe/Madrid' },
        { label: 'Europe/Malta', searchIndex: 'europe/malta|cest|utc+02:00|malta|mt', value: 'Europe/Malta' },
        {
          label: 'Europe/Mariehamn',
          searchIndex: 'europe/mariehamn|eest|utc+03:00|aland islands|ax',
          value: 'Europe/Mariehamn',
        },
        { label: 'Europe/Minsk', searchIndex: 'europe/minsk||utc+03:00|belarus|by', value: 'Europe/Minsk' },
        { label: 'Europe/Monaco', searchIndex: 'europe/monaco|cest|utc+02:00|monaco|mc', value: 'Europe/Monaco' },
        {
          label: 'Europe/Moscow',
          searchIndex: 'europe/moscow|msk|utc+03:00|russian federation|ru',
          value: 'Europe/Moscow',
        },
        { label: 'Europe/Oslo', searchIndex: 'europe/oslo|cest|utc+02:00|norway|no', value: 'Europe/Oslo' },
        { label: 'Europe/Paris', searchIndex: 'europe/paris|cest|utc+02:00|france|fr|monaco|mc', value: 'Europe/Paris' },
        {
          label: 'Europe/Podgorica',
          searchIndex: 'europe/podgorica|cest|utc+02:00|montenegro|me',
          value: 'Europe/Podgorica',
        },
        {
          label: 'Europe/Prague',
          searchIndex: 'europe/prague|cest|utc+02:00|czech republic|cz|slovakia|sk',
          value: 'Europe/Prague',
        },
        { label: 'Europe/Riga', searchIndex: 'europe/riga|eest|utc+03:00|latvia|lv', value: 'Europe/Riga' },
        {
          label: 'Europe/Rome',
          searchIndex: 'europe/rome|cest|utc+02:00|italy|it|san marino|sm|holy see (vatican city state)|va',
          value: 'Europe/Rome',
        },
        { label: 'Europe/Samara', searchIndex: 'europe/samara||utc+04:00|russian federation|ru', value: 'Europe/Samara' },
        {
          label: 'Europe/San_Marino',
          searchIndex: 'europe/san_marino|cest|utc+02:00|san marino|sm',
          value: 'Europe/San_Marino',
        },
        {
          label: 'Europe/Sarajevo',
          searchIndex: 'europe/sarajevo|cest|utc+02:00|bosnia and herzegovina|ba',
          value: 'Europe/Sarajevo',
        },
        {
          label: 'Europe/Saratov',
          searchIndex: 'europe/saratov||utc+04:00|russian federation|ru',
          value: 'Europe/Saratov',
        },
        {
          label: 'Europe/Simferopol',
          searchIndex: 'europe/simferopol|msk|utc+03:00|russian federation|ru|ukraine|ua',
          value: 'Europe/Simferopol',
        },
        { label: 'Europe/Skopje', searchIndex: 'europe/skopje|cest|utc+02:00|macedonia|mk', value: 'Europe/Skopje' },
        { label: 'Europe/Sofia', searchIndex: 'europe/sofia|eest|utc+03:00|bulgaria|bg', value: 'Europe/Sofia' },
        {
          label: 'Europe/Stockholm',
          searchIndex: 'europe/stockholm|cest|utc+02:00|sweden|se',
          value: 'Europe/Stockholm',
        },
        { label: 'Europe/Tallinn', searchIndex: 'europe/tallinn|eest|utc+03:00|estonia|ee', value: 'Europe/Tallinn' },
        { label: 'Europe/Tirane', searchIndex: 'europe/tirane|cest|utc+02:00|albania|al', value: 'Europe/Tirane' },
        {
          label: 'Europe/Ulyanovsk',
          searchIndex: 'europe/ulyanovsk||utc+04:00|russian federation|ru',
          value: 'Europe/Ulyanovsk',
        },
        { label: 'Europe/Vaduz', searchIndex: 'europe/vaduz|cest|utc+02:00|liechtenstein|li', value: 'Europe/Vaduz' },
        {
          label: 'Europe/Vatican',
          searchIndex: 'europe/vatican|cest|utc+02:00|holy see (vatican city state)|va',
          value: 'Europe/Vatican',
        },
        { label: 'Europe/Vienna', searchIndex: 'europe/vienna|cest|utc+02:00|austria|at', value: 'Europe/Vienna' },
        { label: 'Europe/Vilnius', searchIndex: 'europe/vilnius|eest|utc+03:00|lithuania|lt', value: 'Europe/Vilnius' },
        {
          label: 'Europe/Volgograd',
          searchIndex: 'europe/volgograd|msk|utc+03:00|russian federation|ru',
          value: 'Europe/Volgograd',
        },
        { label: 'Europe/Warsaw', searchIndex: 'europe/warsaw|cest|utc+02:00|poland|pl', value: 'Europe/Warsaw' },
        { label: 'Europe/Zagreb', searchIndex: 'europe/zagreb|cest|utc+02:00|croatia|hr', value: 'Europe/Zagreb' },
        {
          label: 'Europe/Zurich',
          searchIndex: 'europe/zurich|cest|utc+02:00|switzerland|ch|germany|de|liechtenstein|li',
          value: 'Europe/Zurich',
        },
      ],
    },
    {
      label: 'Indian',
      options: [
        {
          label: 'Indian/Antananarivo',
          searchIndex: 'indian/antananarivo|eat|utc+03:00|madagascar|mg',
          value: 'Indian/Antananarivo',
        },
        {
          label: 'Indian/Chagos',
          searchIndex: 'indian/chagos||utc+06:00|british indian ocean territory|io',
          value: 'Indian/Chagos',
        },
        {
          label: 'Indian/Christmas',
          searchIndex: 'indian/christmas||utc+07:00|christmas island|cx',
          value: 'Indian/Christmas',
        },
        {
          label: 'Indian/Cocos',
          searchIndex: 'indian/cocos||utc+06:30|cocos (keeling) islands|cc',
          value: 'Indian/Cocos',
        },
        { label: 'Indian/Comoro', searchIndex: 'indian/comoro|eat|utc+03:00|comoros|km', value: 'Indian/Comoro' },
        {
          label: 'Indian/Kerguelen',
          searchIndex: 'indian/kerguelen||utc+05:00|french southern territories|tf',
          value: 'Indian/Kerguelen',
        },
        { label: 'Indian/Mahe', searchIndex: 'indian/mahe||utc+04:00|seychelles|sc', value: 'Indian/Mahe' },
        {
          label: 'Indian/Maldives',
          searchIndex: 'indian/maldives||utc+05:00|maldives|mv|french southern territories|tf',
          value: 'Indian/Maldives',
        },
        { label: 'Indian/Mauritius', searchIndex: 'indian/mauritius||utc+04:00|mauritius|mu', value: 'Indian/Mauritius' },
        { label: 'Indian/Mayotte', searchIndex: 'indian/mayotte|eat|utc+03:00|mayotte|yt', value: 'Indian/Mayotte' },
        { label: 'Indian/Reunion', searchIndex: 'indian/reunion||utc+04:00|reunion|re', value: 'Indian/Reunion' },
      ],
    },
    {
      label: 'Pacific',
      options: [
        { label: 'Pacific/Apia', searchIndex: 'pacific/apia||utc+13:00|samoa|ws', value: 'Pacific/Apia' },
        {
          label: 'Pacific/Auckland',
          searchIndex: 'pacific/auckland|nzdt|utc+13:00|antarctica|aq|new zealand|nz',
          value: 'Pacific/Auckland',
        },
        {
          label: 'Pacific/Bougainville',
          searchIndex: 'pacific/bougainville||utc+11:00|papua new guinea|pg',
          value: 'Pacific/Bougainville',
        },
        { label: 'Pacific/Chatham', searchIndex: 'pacific/chatham||utc+13:45|new zealand|nz', value: 'Pacific/Chatham' },
        {
          label: 'Pacific/Chuuk',
          searchIndex: 'pacific/chuuk||utc+10:00|micronesia (federated states of)|fm',
          value: 'Pacific/Chuuk',
        },
        { label: 'Pacific/Easter', searchIndex: 'pacific/easter||utc-05:00|chile|cl', value: 'Pacific/Easter' },
        { label: 'Pacific/Efate', searchIndex: 'pacific/efate||utc+11:00|vanuatu|vu', value: 'Pacific/Efate' },
        { label: 'Pacific/Fakaofo', searchIndex: 'pacific/fakaofo||utc+13:00|tokelau|tk', value: 'Pacific/Fakaofo' },
        { label: 'Pacific/Fiji', searchIndex: 'pacific/fiji||utc+12:00|fiji|fj', value: 'Pacific/Fiji' },
        { label: 'Pacific/Funafuti', searchIndex: 'pacific/funafuti||utc+12:00|tuvalu|tv', value: 'Pacific/Funafuti' },
        {
          label: 'Pacific/Galapagos',
          searchIndex: 'pacific/galapagos||utc-06:00|ecuador|ec',
          value: 'Pacific/Galapagos',
        },
        {
          label: 'Pacific/Gambier',
          searchIndex: 'pacific/gambier||utc-09:00|french polynesia|pf',
          value: 'Pacific/Gambier',
        },
        {
          label: 'Pacific/Guadalcanal',
          searchIndex: 'pacific/guadalcanal||utc+11:00|micronesia (federated states of)|fm|solomon islands|sb',
          value: 'Pacific/Guadalcanal',
        },
        {
          label: 'Pacific/Guam',
          searchIndex: 'pacific/guam|chst|utc+10:00|guam|gu|northern mariana islands|mp',
          value: 'Pacific/Guam',
        },
        {
          label: 'Pacific/Honolulu',
          searchIndex: 'pacific/honolulu|hst|utc-10:00|united states|us',
          value: 'Pacific/Honolulu',
        },
        { label: 'Pacific/Kanton', searchIndex: 'pacific/kanton||utc+13:00|kiribati|ki', value: 'Pacific/Kanton' },
        {
          label: 'Pacific/Kiritimati',
          searchIndex: 'pacific/kiritimati||utc+14:00|kiribati|ki',
          value: 'Pacific/Kiritimati',
        },
        {
          label: 'Pacific/Kosrae',
          searchIndex: 'pacific/kosrae||utc+11:00|micronesia (federated states of)|fm',
          value: 'Pacific/Kosrae',
        },
        {
          label: 'Pacific/Kwajalein',
          searchIndex: 'pacific/kwajalein||utc+12:00|marshall islands|mh',
          value: 'Pacific/Kwajalein',
        },
        {
          label: 'Pacific/Majuro',
          searchIndex: 'pacific/majuro||utc+12:00|marshall islands|mh',
          value: 'Pacific/Majuro',
        },
        {
          label: 'Pacific/Marquesas',
          searchIndex: 'pacific/marquesas||utc-09:30|french polynesia|pf',
          value: 'Pacific/Marquesas',
        },
        {
          label: 'Pacific/Midway',
          searchIndex: 'pacific/midway|sst|utc-11:00|united states outlying islands|um',
          value: 'Pacific/Midway',
        },
        { label: 'Pacific/Nauru', searchIndex: 'pacific/nauru||utc+12:00|nauru|nr', value: 'Pacific/Nauru' },
        { label: 'Pacific/Niue', searchIndex: 'pacific/niue||utc-11:00|niue|nu', value: 'Pacific/Niue' },
        {
          label: 'Pacific/Norfolk',
          searchIndex: 'pacific/norfolk||utc+12:00|norfolk island|nf',
          value: 'Pacific/Norfolk',
        },
        { label: 'Pacific/Noumea', searchIndex: 'pacific/noumea||utc+11:00|new caledonia|nc', value: 'Pacific/Noumea' },
        {
          label: 'Pacific/Pago_Pago',
          searchIndex: 'pacific/pago_pago|sst|utc-11:00|american samoa|as|united states outlying islands|um',
          value: 'Pacific/Pago_Pago',
        },
        { label: 'Pacific/Palau', searchIndex: 'pacific/palau||utc+09:00|palau|pw', value: 'Pacific/Palau' },
        { label: 'Pacific/Pitcairn', searchIndex: 'pacific/pitcairn||utc-08:00|pitcairn|pn', value: 'Pacific/Pitcairn' },
        {
          label: 'Pacific/Pohnpei',
          searchIndex: 'pacific/pohnpei||utc+11:00|micronesia (federated states of)|fm',
          value: 'Pacific/Pohnpei',
        },
        {
          label: 'Pacific/Port_Moresby',
          searchIndex:
            'pacific/port_moresby||utc+10:00|antarctica|aq|micronesia (federated states of)|fm|papua new guinea|pg',
          value: 'Pacific/Port_Moresby',
        },
        {
          label: 'Pacific/Rarotonga',
          searchIndex: 'pacific/rarotonga||utc-10:00|cook islands|ck',
          value: 'Pacific/Rarotonga',
        },
        {
          label: 'Pacific/Saipan',
          searchIndex: 'pacific/saipan|chst|utc+10:00|northern mariana islands|mp',
          value: 'Pacific/Saipan',
        },
        {
          label: 'Pacific/Tahiti',
          searchIndex: 'pacific/tahiti||utc-10:00|french polynesia|pf',
          value: 'Pacific/Tahiti',
        },
        {
          label: 'Pacific/Tarawa',
          searchIndex:
            'pacific/tarawa||utc+12:00|kiribati|ki|marshall islands|mh|tuvalu|tv|united states outlying islands|um|wallis and futuna|wf',
          value: 'Pacific/Tarawa',
        },
        { label: 'Pacific/Tongatapu', searchIndex: 'pacific/tongatapu||utc+13:00|tonga|to', value: 'Pacific/Tongatapu' },
        {
          label: 'Pacific/Wake',
          searchIndex: 'pacific/wake||utc+12:00|united states outlying islands|um',
          value: 'Pacific/Wake',
        },
        {
          label: 'Pacific/Wallis',
          searchIndex: 'pacific/wallis||utc+12:00|wallis and futuna|wf',
          value: 'Pacific/Wallis',
        },
      ],
    },
  ];

  const getTimezoneInfo = (searchIndex: string) => {
    const list = searchIndex.split('|');
    return {
      abbreviation: list[1].toLocaleUpperCase(),
      country: (list[3] || '').replace(/(\b\w)/g, v => v.toLocaleUpperCase()),
      countryCode: list[4] || '',
      utc: list[2].toLocaleUpperCase(),
    };
  };

  const getTimezoneInfoByValue = (value: string) => timezoneDetails.reduce((pre: any, group: TimeZoneGroup) => {
    if (pre?.label === value) return pre;
    return group.options.find(option => option.label === value);
  }, {}) as TimezoneItem;

  const getTimezoneDetails = () => {
    const browserTimeZone = dayjs.tz.guess();
    const defaultTimezoneList: TimezoneItem[] = [];
    const list: TimeZoneGroup[] = timezoneList.map(group => ({
      label: group.label,
      options: group.options.map((option) => {
        const info = {
          ...option,
          ...getTimezoneInfo(option.searchIndex),
        };
        if (option.value === browserTimeZone) {
          defaultTimezoneList.push({
            ...option,
            ...info,
            label: info.label,
          });
        }
        return info;
      }),
    }));
    list.unshift({
      label: '',
      options: defaultTimezoneList,
    });
    return list;
  };

  const { t } = useI18n();
  const timeZoneStore = useTimeZone();

  const timezoneDetails = getTimezoneDetails();

  const localValue = ref(timezoneDetails[0].options[0].label);
  const selected = ref<TimezoneItem>(timezoneDetails[0].options[0]);
  const isActive = ref(false);

  const timezoneData = shallowRef(timezoneDetails);

  const isBrowserTimezone = computed(() => selected.value?.label === timezoneData.value[0].options[0].label);

  watch(localValue, (val) => {
    const info = getTimezoneInfoByValue(val);
    selected.value = info;
    timeZoneStore.update(info);
    emits('change', val, info);
  }, {
    immediate: true,
  });

  const handleClickTriggerBox = () => {
    isActive.value = !isActive.value;
  };

  const handleChange = (val: string) => {
    localValue.value = val;
  };

  const handleSearch = (keyword: string, timezone: TimezoneItem) => {
    const searchKey = new RegExp(encodeRegexp(keyword.toLowerCase()), 'i');
    return searchKey.test(timezone.label?.toLowerCase())
      || searchKey.test(timezone.country?.toLowerCase())
      || searchKey.test(timezone.abbreviation?.toLowerCase())
      || searchKey.test(timezone.utc?.toLowerCase());
  };

  const checkClickTrigger = (e: any) => {
    const targetDom = document.getElementById('timezone-picker-trigger');
    if (!targetDom?.contains(e.target)) {
      isActive.value = false;
    }
  };

  onMounted(() => {
    window.addEventListener('click', checkClickTrigger);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('click', checkClickTrigger);
  });

</script>
<style lang="less" scoped>
.timezone-picker-trigger-box {
  display: flex;
  width: 100%;
  height: 32px;
  padding: 0 9px;
  cursor: pointer;
  border: 1px solid #C4C6CC;
  border-radius: 2px;
  align-items: center;

  &:hover {
    border-color: #A3C5FD;
  }

  .diaplay-content {
    display: flex;
    align-items: center;
    flex: 1;
    overflow: hidden;

    .option-name {
      font-weight: 400;
      color: #313238;
    }

    .option-country {
      margin-left: 8px;
      overflow: hidden;
      color: #979BA5;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .option-utc {
      height: 20px;
      padding: 0 8px;
      margin-left: 8px;
      line-height: 20px;
      color: #63656E;
      border: 1px solid #DCDEE5;
      border-radius: 2px;
    }

  }

  .down-icon {
    font-size: 14px;
  }
}

.timezone-picker-trigger-box-active {
  border-color: #3A84FF !important;


  .down-icon {
    transform: rotate(-180deg);
    transition: all 0.5s;
  }
}

.timezone-picker-option {
  display: flex;
  align-items: center;
  width: 100%;
  color: #63656e;

  .option-name {
    flex: 1;
  }

  .option-country {
    width: 100%;
    margin-left: 6px;
    overflow: hidden;
    color: #999;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .option-utc {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 20px;
    padding: 0 8px;
    background: #f0f1f5;
    border-radius: 2px;
  }
}

.timezone-picker-option-selected {
  color: #3a84ff;

  .option-country {
    color: #699df4;
  }

  .option-utc {
    color: white;
    background-color: #699df4;
  }
}


</style>
