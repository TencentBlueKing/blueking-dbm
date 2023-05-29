<template>
  <div class="system-serach-filter-options">
    <div class="filter-item">
      <div class="filter-title">
        {{ t('业务') }}
      </div>
      <BkSelect
        v-model="modelValue.bk_biz_ids"
        behavior="simplicity"
        filterable
        multiple
        :placeholder="t('全部')"
        :popover-min-width="300"
        :popover-options="{
          boundary: 'parent',
          disableTeleport: true,
        }"
        show-select-all
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
      <template v-if="dbOptionsExpand">
        <BkCheckbox
          class="mb-16"
          :model-value="isAllDbTypes"
          @change="handleDbTypeAll">
          {{ t('全部') }}
        </BkCheckbox>
        <BkCheckboxGroup v-model="modelValue.db_types">
          <BkCheckbox
            v-for="dbItem in dbList"
            :key="dbItem.id"
            :label="dbItem.id">
            {{ dbItem.name }}
          </BkCheckbox>
        </BkCheckboxGroup>
      </template>
      <BkSelect
        v-else
        v-model="modelValue.db_types"
        behavior="simplicity"
        filterable
        multiple
        :placeholder="t('全部')"
        :popover-options="{
          boundary: 'parent',
          disableTeleport: true,
        }"
        show-select-all
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
      <div class="pb-8">
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
    bizList: ServiceReturnType<typeof getBizs>;
    dbOptionsExpand?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    dbOptionsExpand: false,
  });

  const modelValue = defineModel<{
    bk_biz_ids: number[];
    db_types: string[];
    resource_types: string[];
    filter_type: string;
  }>({
    required: true,
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

  // name 需按字母序排序
  const dbList = [
    {
      id: 'es',
      name: 'ElasticSearch',
    },
    {
      id: 'hdfs',
      name: 'HDFS',
    },
    {
      id: 'influxDB',
      name: 'influxDB',
    },
    {
      id: 'kafka',
      name: 'Kafka',
    },
    {
      id: 'mysql',
      name: 'MySQL',
    },
    {
      id: 'pulsar',
      name: 'Pulsar',
    },
    {
      id: 'redis',
      name: 'Redis',
    },
    {
      id: 'riak',
      name: 'Riak',
    },
    {
      id: 'tendbcluster',
      name: 'Tendb Cluster',
    },
  ];

  const isAllDbTypes = computed(() => modelValue.value.db_types.length === 0);
  const isAllResourceType = computed(() => modelValue.value.resource_types.length === 0);

  const handleDbTypeAll = () => {
    modelValue.value.db_types = [];
  };

  const handleResourceTypeAll = () => {
    modelValue.value.resource_types = [];
  };
</script>
<style lang="less">
  .system-serach-filter-options {
    .filter-item {
      .filter-title {
        margin-bottom: 10px;
        line-height: 16px;
        color: #979ba5;
      }

      & ~ .filter-item {
        margin-top: 24px;
      }
    }

    .bk-checkbox-group {
      display: block;
    }

    .bk-checkbox {
      display: flex;
      margin-left: 0 !important;

      & ~ .bk-checkbox {
        margin-top: 16px;
      }
    }

    .bk-radio-group {
      display: block;

      .bk-radio {
        display: block;
        margin-left: 0 !important;

        & ~ .bk-radio {
          margin-top: 16px;
        }
      }
    }
  }
</style>
