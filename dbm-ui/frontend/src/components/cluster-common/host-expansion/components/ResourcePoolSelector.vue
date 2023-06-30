<template>
  <div class="expansion-resource-pool-selector">
    <BkLoading :loading="recommendSpecLoading">
      <div class="form-block">
        <div class="form-block-item">
          <div class="form-block-title">
            {{ t('xx节点规格', { name: data.label.toLocaleLowerCase() }) }}
            <span class="required-flag">*</span>
          </div>
          <span
            v-bk-tooltips="{
              content: t('请先设置期望容量'),
              disabled:data.targetDisk > 0
            }">
            <BkSelect
              :disabled="data.targetDisk < 1"
              :loading="isResourceSpecLoading"
              :model-value="specId || undefined"
              @change="handleSpecChange">
              <BkOption
                v-for="item in resourceSpecList?.results"
                :key="item.spec_id"
                :label="item.spec_name"
                :value="item.spec_id" />
            </BkSelect>
          </span>
        </div>
        <div class="form-block-item">
          <div class="form-block-title">
            <I18nT keypath="扩容至（当前n台）">
              {{ originalHostNums }}
            </I18nT>
            <span class="required-flag">*</span>
          </div>
          <span
            v-bk-tooltips="{
              content: t('请先设置期望容量'),
              disabled:data.targetDisk > 0
            }">
            <BkInput
              :disabled="data.targetDisk < 1"
              :min="originalHostNums"
              :model-value="machinePairCnt || undefined"
              type="number"
              @change="handleMachinePairCntChange" />
          </span>
        </div>
      </div>
    </BkLoading>
    <div
      v-if="estimateCapacity > 0"
      class="disk-tips mt-16">
      <span style="padding-right: 4px">
        {{ t('预估容量（以最小配置计算）') }}:
      </span>
      <span class="number">{{ estimateCapacity }}</span>
      <span>G</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    computed,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchRecommendSpec } from '@services/dbResource';
  import { getResourceSpecList } from '@services/resourceSpec';

  import type { TExpansionNode } from '../Index.vue';

  interface Props {
    data: TExpansionNode,
  }

  interface Emits {
    (e: 'change', value: TExpansionNode['resourceSpec'], expansionDisk: TExpansionNode['expansionDisk']): void,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const specId = ref(props.data.resourceSpec.spec_id);
  const machinePairCnt = ref(props.data.resourceSpec.count + props.data.originalHostList.length);

  const originalHostNums = computed(() => props.data.originalHostList.length);

  // 资源池预估容量
  const estimateCapacity = computed(() => {
    if (machinePairCnt.value < 1) {
      return 0;
    }
    const currentSpec = _.find(resourceSpecList.value?.results, item => item.spec_id === specId.value);
    if (!currentSpec) {
      return 0;
    }
    const storage = currentSpec.storage_spec.reduce((result, item) => result + item.size, 0);
    return storage * machinePairCnt.value;
  });

  const {
    loading: isResourceSpecLoading,
    data: resourceSpecList,
  } = useRequest(getResourceSpecList, {
    defaultParams: [
      {
        spec_cluster_type: props.data.specClusterType,
        spec_machine_type: props.data.specMachineType,
      },
    ],
  });

  // 推荐规格
  const {
    loading: recommendSpecLoading,
  } = useRequest(fetchRecommendSpec, {
    defaultParams: [
      {
        cluster_id: props.data.clusterId,
        role: props.data.role,
      },
    ],
    onSuccess(recommendSpecList) {
      if (recommendSpecList.length > 0) {
        specId.value = recommendSpecList[0].spec_id;
      }
    },
  });

  const handleSpecChange = (value: number) => {
    specId.value = value;
  };

  const handleMachinePairCntChange = (value: string) => {
    machinePairCnt.value = Number(value);
    emits('change', {
      spec_id: specId.value,
      count: Math.max(machinePairCnt.value - originalHostNums.value, 0),
    }, estimateCapacity.value);
  };
</script>
<style lang="less">
  .expansion-resource-pool-selector {
    font-size: 12px;

    .form-block{
      display: flex;

      .form-block-title{
        margin-bottom: 6px;
        line-height: 20px;

        .required-flag{
          color: #EA3636;
        }
      }

      .form-block-item{
        flex: 1;

        & ~ .form-block-item{
          margin-left: 32px;
        }
      }
    }

    .disk-tips{
      color: #63656E;
    }
  }
</style>
