<template>
  <div class="operate-item">
    <div class="operate-item-inner">
      <Select
        v-model="localValue"
        :filter-option="handleSearch"
        :input-search="false"
        :search-placeholder="t('请输入搜索（国家，城市，简称）')"
        :popover-min-width="400"
        filterable
        @change="handleChange">
        <template #trigger>
          <div
            class="timezone-picker-trigger"
            @click="() => (isActive = !isActive)">
            <DbIcon
              class="operate-icon timezone-picker-prefix"
              type="bk-dbm-icon db-icon-time" />
            <div
              v-bk-tooltips="{
                content: `${isBrowserTimezone ? t('浏览器时区') : ''} ${selected.label}`,
              }">
              {{ selected.utc }}
            </div>
            <DbIcon
              class="operate-icon timezone-picker-append"
              :class="{
                'db-icon-up': isActive,
              }"
              type="bk-dbm-icon db-icon-down-big" />
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
                  class="option-country">
                  {{ item.country }}, {{ item.abbreviation }}
                </span>
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
                    class="option-country">
                    {{ item.country }}, {{ item.abbreviation }}
                  </span>
                  <span class="option-utc">{{ item.utc }}</span>
                </div>
              </Option>
            </Group>
          </template>
        </template>
      </Select>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { Select } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import dayjs from 'dayjs';
  import timezoneList from './list';
  import { encodeRegexp } from '@utils';

  interface TimezoneItem {
    abbreviation: string;
    country: string;
    countryCode: string;
    label: string;
    utc: string;
  }

  interface TimeZoneGroup {
    label: string;
    options: TimezoneItem[];
  }

  const modelValue = defineModel<string>({
    required: true,
  });

  const { Group, Option } = Select;

  const { t } = useI18n();

  const getTimezoneInfo = (searchIndex: string) => {
    const list = searchIndex.split('|');
    return {
      abbreviation: list[1].toLocaleUpperCase(),
      country: (list[3] || '').replace(/(\b\w)/g, (v) => v.toLocaleUpperCase()),
      countryCode: list[4] || '',
      utc: list[2].toLocaleUpperCase(),
    };
  };

  const getTimezoneDetails = () => {
    const browserTimeZone = dayjs.tz.guess();
    const defaultTimezoneList: TimezoneItem[] = [];
    const list: TimeZoneGroup[] = timezoneList.map((group) => ({
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

  const timezoneDetails = getTimezoneDetails();

  const localValue = ref(timezoneDetails[0].options[0].label);
  const selected = ref<TimezoneItem>(timezoneDetails[0].options[0]);

  const timezoneData = shallowRef(timezoneDetails);

  const isActive = ref(false);

  const isBrowserTimezone = computed(() => selected.value?.label === timezoneData.value[0].options[0].label);

  const getTimezoneInfoByValue = (value: string) =>
    timezoneDetails.reduce((pre: any, group: TimeZoneGroup) => {
      if (pre?.label === value) {
        return pre;
      }
      return group.options.find((option) => option.label === value);
    }, {}) as TimezoneItem;

  const handleSearch = (keyword: string, timezone: TimezoneItem) => {
    const searchKey = new RegExp(encodeRegexp(keyword.toLowerCase()), 'i');
    return (
      searchKey.test(timezone.label?.toLowerCase()) ||
      searchKey.test(timezone.country?.toLowerCase()) ||
      searchKey.test(timezone.abbreviation?.toLowerCase()) ||
      searchKey.test(timezone.utc?.toLowerCase())
    );
  };

  const handleChange = (val: string) => {
    localValue.value = val;
    const info = getTimezoneInfoByValue(val);
    selected.value = info;
    modelValue.value = info.utc.substring(3) || '+00:00';
  };
</script>
<style lang="less" scoped>
  .timezone-picker-trigger {
    position: relative;
    display: flex;
    width: 114px;
    height: 28px;
    align-items: center;
    justify-content: center;

    .timezone-picker-prefix,
    .timezone-picker-append {
      position: absolute;
    }

    .timezone-picker-prefix {
      left: 0;
    }

    .timezone-picker-append {
      right: 0;
    }

    .db-icon-up {
      transform: rotate(180deg);
      transition: all 0.2s;
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
