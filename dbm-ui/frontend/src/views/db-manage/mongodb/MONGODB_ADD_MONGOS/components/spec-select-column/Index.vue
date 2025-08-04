<template>
  <EditableColumn
    class="spec-select-column"
    field="spec_id"
    :label="t('扩容规格')"
    required
    :width="300">
    <EditableSelect v-model="modelValue">
      <BkOption
        v-for="(item, index) in specList"
        :key="index"
        :label="item.spec_name"
        :value="item.spec_id">
        <SpecDetailPopover
          :data="item"
          placement="right">
          <div class="spec-select-column-spec-item">
            <span class="text-overflow">
              {{ item.spec_name }}
              <BkTag
                v-if="currentSpecIds?.includes(item.spec_id)"
                size="small"
                theme="info">
                {{ t('当前规格') }}
              </BkTag>
            </span>
            <span class="count">
              {{ item.availableCount }}
            </span>
          </div>
        </SpecDetailPopover>
      </BkOption>
    </EditableSelect>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { ClusterTypes, MachineTypes } from '@common/const';

  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  interface Props {
    bkCloudId: number;
    currentSpecIds?: number[];
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const specList = ref<({ availableCount: number } & ResourceSpecModel)[]>([]);

  const { run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specList.value.forEach((item) => {
        Object.assign(item, {
          availableCount: data[item.spec_id],
        });
      });
    },
  });

  useRequest(getResourceSpecList, {
    defaultParams: [
      {
        limit: -1,
        offset: 0,
        spec_cluster_type: ClusterTypes.MONGODB,
        spec_machine_type: MachineTypes.MONGOS,
      },
    ],
    onSuccess(data) {
      specList.value = data.results.map((item) => Object.assign(item, { availableCount: 0 }));
    },
  });

  watch(
    () => props.bkCloudId,
    () => {
      fetchSpecResourceCount({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: props.bkCloudId,
        spec_ids: specList.value.map((item) => item.spec_id),
      });
    },
  );

  watch(
    () => props.currentSpecIds,
    () => {
      if (props.currentSpecIds?.length === 1 && !modelValue.value) {
        [modelValue.value] = props.currentSpecIds;
      }
    },
  );
</script>

<style lang="less" scoped>
  .spec-select-column-label-tip {
    border-bottom: 1px dashed #979ba5;
  }

  .spec-select-column-spec-item {
    display: flex;
    width: 100%;
    flex: 1;
    align-items: center;
    justify-content: space-between;

    .count {
      height: 16px;
      min-width: 20px;
      font-size: 12px;
      line-height: 16px;
      color: @gray-color;
      text-align: center;
      background-color: #f0f1f5;
      border-radius: 2px;
    }
  }
</style>
