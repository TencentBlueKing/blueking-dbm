<template>
  <BkSearchSelect
    v-model="modelValue"
    class="search-selector"
    :data="searchSelectData"
    unique-select
    value-split-code="+"
    @search="handleSearch" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchDeviceClass, getOsTypeList } from '@services/source/dbresourceResource';
  import { fetchDbTypeList } from '@services/source/infras';
  import { getCloudList } from '@services/source/ipchooser';

  import { useGlobalBizs } from '@stores';

  interface Emits {
    (e: 'search'): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { bizs } = useGlobalBizs();

  const modelValue = defineModel({
    default: () => [],
  });

  const searchSelectData = computed(() => [
    {
      name: 'IP',
      id: 'hosts',
    },
    {
      name: t('所属业务'),
      id: 'for_biz',
      children: bizs.map((biz) => ({
        name: biz.name,
        id: String(biz.bk_biz_id),
      })),
    },
    {
      name: t('所属DB类型'),
      id: 'resource_type',
      children: resourceTypeList.value,
    },
    {
      name: t('管控区域'),
      id: 'bk_cloud_ids',
      children: cloudList.value?.map((item) => ({
        id: item.bk_cloud_id,
        name: item.bk_cloud_name,
      })),
    },
    {
      name: t('Agent 状态'),
      id: 'agent_status',
      children: [
        {
          name: t('正常'),
          id: '1',
        },
        {
          name: t('异常'),
          id: '0',
        },
      ],
    },
    {
      name: t('操作系统'),
      id: 'os_type',
      children: osTypeList.value?.map((item) => ({
        id: item,
        name: item,
      })),
    },
    {
      name: t('机型'),
      id: 'device_class',
      children: deviceClassList.value?.map((item) => ({
        id: item,
        name: item,
      })),
    },
  ]);

  // 管控区域
  const { data: cloudList } = useRequest(getCloudList);

  // DB类型
  const { data: resourceTypeList } = useRequest(fetchDbTypeList, {
    onSuccess(data) {
      resourceTypeList.value = [
        {
          id: 'PUBLIC',
          name: t('通用'),
        },
        ...data,
      ];
    },
  });

  // 操作系统
  const { data: osTypeList } = useRequest(getOsTypeList, {
    defaultParams: [
      {
        offset: 0,
        limit: -1,
      },
    ],
  });

  // 机型
  const { data: deviceClassList } = useRequest(fetchDeviceClass);

  const handleSearch = () => {
    emits('search');
  };
</script>

<style scoped lang="less">
  .resource-search-selector {
    width: 560px;
    height: 32px;
    margin-left: auto;
  }
</style>
