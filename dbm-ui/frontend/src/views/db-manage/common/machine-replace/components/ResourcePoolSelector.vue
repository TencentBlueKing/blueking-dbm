<template>
  <DbForm
    ref="dbForm"
    class="replace-resource-tag-selector"
    :label-width="72"
    :model="modelValue">
    <DbFormItem
      error-display-type="tooltips"
      :label="t('匹配规格')"
      property="spec_id"
      required
      :rules="specRules">
      <BkSelect
        :loading="isResourceSpecLoading"
        :model-value="modelValue.spec_id || undefined"
        :placeholder="t('请选择匹配规格')"
        @change="handleSpecChange">
        <BkOption
          v-for="item in resourceSpecList?.results"
          :key="item.spec_id"
          :label="item.spec_name"
          :value="item.spec_id">
          <SpecDetailPopover
            :data="item"
            placement="right">
            <div style="display: flex; width: 100%; align-items: center">
              <div>{{ item.spec_name }}</div>
              <BkTag style="margin-left: auto">
                {{ specCountMap[item.spec_id] }}
              </BkTag>
            </div>
          </SpecDetailPopover>
        </BkOption>
      </BkSelect>
    </DbFormItem>
    <DbFormItem
      error-display-type="tooltips"
      :label="t('资源标签')"
      property="labels"
      required
      :rules="resourceTagRules">
      <ResourceTagSelector
        ref="resourceTagSelector"
        v-model="modelValue.labels" />
    </DbFormItem>
  </DbForm>
</template>
<script setup lang="ts">
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { fetchRecommendSpec, getResourceSpecList } from '@services/source/dbresourceSpec';

  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  import ResourceTagSelector from '@views/db-manage/common/apply-items/ResourceTagSelector.vue';

  import type { TReplaceNode } from '../Index.vue';

  interface Props {
    cloudInfo: {
      id: number;
      name: string;
    };
    data: TReplaceNode;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<Props['data']['resourceSpec']>({
    required: true,
  });

  interface Exposes {
    validate: () => Promise<boolean>;
  }

  const { t } = useI18n();

  const specRules = [
    {
      message: t('请选择匹配规格'),
      required: true,
      trigger: 'change',
      validator: (value: number) => Boolean(value) && value > 0,
    },
  ];

  const resourceTagRules = [
    {
      message: t('请选择资源标签'),
      required: true,
      trigger: 'change',
      validator: () => resourceTagSelector.value?.validate(),
    },
  ];

  const dbFormRef = useTemplateRef('dbForm');
  const resourceTagSelector = useTemplateRef('resourceTagSelector');
  const specCountMap = shallowRef<Record<number, number>>({});

  const { run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specCountMap.value = data;
    },
  });

  const { data: resourceSpecList, loading: isResourceSpecLoading } = useRequest(getResourceSpecList, {
    defaultParams: [
      {
        biz_ids: `${window.PROJECT_CONFIG.BIZ_ID}`,
        limit: -1,
        spec_cluster_type: props.data.specClusterType,
        spec_machine_type: props.data.specMachineType,
      },
    ],
    onSuccess(data) {
      fetchSpecResourceCount({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: props.cloudInfo.id,
        spec_ids: data.results.map((item) => item.spec_id),
      });
    },
  });

  const getDefaultParams = ():
    | {
        instance_id: number;
        role: string;
      }
    | {
        cluster_id: number;
        role: string;
      } => {
    // influxdb 没有 cluster_id 需要通过 instance_id 查询
    if (props.data.role === 'influxdb') {
      const [firstNode] = props.data.oldHostList;
      return {
        instance_id: firstNode.related_instances[0]?.bk_instance_id,
        role: 'influxdb',
      };
    }
    // 大数据集群同步 cluster_id 查询
    return {
      cluster_id: props.data.clusterId,
      role: props.data.role,
    };
  };

  useRequest(fetchRecommendSpec, {
    defaultParams: [getDefaultParams()],
    onSuccess(recommendSpecList) {
      if (recommendSpecList.length > 0) {
        modelValue.value = Object.assign(modelValue.value, {
          count: props.data.oldHostList.length,
          spec_id: recommendSpecList[0].spec_id,
        });
      }
    },
  });

  const handleSpecChange = (value: number) => {
    modelValue.value = Object.assign(modelValue.value, {
      count: props.data.oldHostList.length,
      spec_id: value,
    });
  };

  defineExpose<Exposes>({
    validate() {
      return dbFormRef.value!.validate();
    },
  });
</script>
<style lang="less">
  .replace-resource-tag-selector {
    padding: 16px 60px;

    .bk-form-item {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }

      .bk-form-label {
        font-size: 12px;
      }
    }
  }
</style>
