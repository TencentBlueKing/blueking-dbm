<template>
  <div class="system-serach-filter-options">
    <div class="filter-item">
      <div class="filter-title">
        {{ t('业务') }}
      </div>
      <BkSelect
        v-model="modelValue.bk_biz_ids"
        behavior="simplicity"
        collapse-tags
        filterable
        multiple
        :placeholder="t('全部')"
        :popover-min-width="300"
        :popover-options="{
          boundary: 'parent',
          disableTeleport: true
        }"
        size="small">
        <BkOption
          v-for="bizItem in bizList"
          :id="bizItem.bk_biz_id"
          :key="bizItem.bk_biz_id"
          :name="bizItem.display_name" />
      </BkSelect>
    </div>
    <div class="filter-item">
      <div class="filter-title">
        {{ t('数据库组件') }}
      </div>
      <BkSelect
        v-model="modelValue.db_types"
        behavior="simplicity"
        collapse-tags
        filterable
        multiple
        :placeholder="t('全部')"
        :popover-options="{
          boundary: 'parent',
          disableTeleport: true,
        }"
        size="small">
        <BkOption
          v-for="dbItem in dbList"
          :id="dbItem.id"
          :key="dbItem.id"
          :name="dbItem.name" />
      </BkSelect>
    </div>
    <div class="filter-item">
      <div class="filter-title">
        {{ t('检索内容') }}
      </div>
      <div>
        <BkCheckbox
          class="mb-16"
          :model-value="isAllResourceType"
          @change="handleResourceTypeAll">
          {{ t('全部') }}
        </BkCheckbox>
        <BkCheckboxGroup v-model="modelValue.resource_types">
          <BkCheckbox
            v-for="resourceTypeItem in resourceList"
            :key="resourceTypeItem.id"
            :label="resourceTypeItem.id">
            {{ resourceTypeItem.name }}
          </BkCheckbox>
        </BkCheckboxGroup>
      </div>
    </div>
    <div class="filter-item">
      <div class="filter-title">
        {{ t('检索类型') }}
      </div>
      <BkRadioGroup v-model="modelValue.filter_type">
        <BkRadio label="CONTAINS">
          {{ t('模糊') }}
        </BkRadio>
        <BkRadio label="EXACT">
          {{ t('精确') }}
        </BkRadio>
      </BkRadioGroup>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getBizs } from '@services/source/cmdb';

  interface Props {
    bizList: ServiceReturnType<typeof getBizs>
  }

  defineProps<Props>();

  const modelValue = defineModel<{
    bk_biz_ids: number[],
    db_types: string[],
    resource_types: string[],
    filter_type: string,
  }>({
    required: true,
    local: true,
  });

  const { t } = useI18n();

  const resourceList = [
    {
      id: 'cluster_domain',
      name: t('域名'),
    },
    {
      id: 'cluster_name',
      name: t('集群名称'),
    },
    {
      id: 'instance',
      name: t('实例'),
    },
    {
      id: 'task',
      name: t('任务ID'),
    },
    {
      id: 'ticket',
      name: t('单据'),
    },
    {
      id: 'machine',
      name: t('主机'),
    },
  ];

  const dbList = [
    {
      id: 'mysql',
      name: 'MySQL',
    },
    {
      id: 'tendbcluster',
      name: 'Tendb Cluster',
    },
    // {
    //   id: 'mongodb',
    //   name: 'MongoDB',
    // },
    {
      id: 'influxDB',
      name: 'influxDB',
    },
    {
      id: 'pulsar',
      name: 'Pulsar',
    },
    {
      id: 'kafka',
      name: 'Kafka',
    },
    {
      id: 'es',
      name: 'ElasticSearch',
    },
    {
      id: 'hdfs',
      name: 'HDFS',
    },
    {
      id: 'redis',
      name: 'Redis',
    },
  ];

  const isAllResourceType = ref(true);

  watch(modelValue, () => {
    isAllResourceType.value = modelValue.value.resource_types.length === 0;
  }, {
    deep: true,
  });

  const handleResourceTypeAll = () => {
    modelValue.value.resource_types = [];
  };
</script>
<style lang="less">
  .system-serach-filter-options {
    .filter-item{
      .filter-title{
        margin-bottom: 10px;
        line-height: 16px;
        color: #979BA5;
      }

      & ~ .filter-item{
        margin-top: 16px;
      }
    }

    .bk-checkbox-group{
      display: block;
    }

    .bk-checkbox{
      display: flex;
      margin-left: 0 !important;

      & ~ .bk-checkbox{
        margin-top: 16px;
      }
    }

    .bk-radio-group{
      display: block;

      .bk-radio{
        display: block;
        margin-left: 0 !important;

        & ~ .bk-radio{
          margin-top: 16px;
        }
      }
    }
  }
</style>
