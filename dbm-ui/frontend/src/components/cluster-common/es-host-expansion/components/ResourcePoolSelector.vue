<template>
  <div class="es-cluster-expansion-resource-pool-selector">
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
                :value="item.spec_id">
                <BkPopover
                  placement="right"
                  theme="light"
                  width="580">
                  <div style="display: flex; width: 100%; align-items: center;">
                    <div>{{ item.spec_name }}</div>
                    <BkTag style="margin-left: auto;">{{ specCountMap[item.spec_id] }}</BkTag>
                  </div>
                  <template #content>
                    <SpecDetail :data="item" />
                  </template>
                </BkPopover>
              </BkOption>
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
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import {
    fetchRecommendSpec,
    getResourceSpecList,
  } from '@services/source/dbresourceSpec';

  import SpecDetail from '@components/cluster-common/SpecDetailForPopover.vue';

  import type { TExpansionNode } from '../Index.vue';

  interface Props {
    data: TExpansionNode,
    cloudInfo: {
      id: number,
      name: string
    },
  }

  interface Emits {
    (e: 'change', value: TExpansionNode['resourceSpec'], expansionDisk: TExpansionNode['expansionDisk']): void,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const specId = ref(props.data.resourceSpec.spec_id);
  const machinePairCnt = ref(props.data.resourceSpec.count + props.data.originalHostList.length);
  const specCountMap = shallowRef<Record<number, number>>({});

  const originalHostNums = computed(() => props.data.originalHostList.length);

  // 选中的规格
  const currentSelectSpec = computed(() => _.find(
    resourceSpecList.value?.results,
    item => item.spec_id === specId.value,
  ));

  // 资源池预估容量
  const estimateCapacity = computed(() => {
    if (machinePairCnt.value < 1 || !currentSelectSpec.value) {
      return 0;
    }

    const storage = currentSelectSpec.value.storage_spec.reduce((result, item) => result + item.size, 0);
    return storage * machinePairCnt.value;
  });

  const triggerChange = () => {
    emits('change', {
      spec_id: specId.value,
      count: Math.max(machinePairCnt.value - originalHostNums.value, 0),
      instance_num: currentSelectSpec.value ? currentSelectSpec.value.instance_num as number : 0,
    }, estimateCapacity.value);
  };

  const {
    run: fetchSpecResourceCount,
  } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specCountMap.value = data;
    },
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
    onSuccess(data) {
      fetchSpecResourceCount({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: props.cloudInfo.id,
        spec_ids: data.results.map(item => item.spec_id),
      });
    },
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
  });

  const handleSpecChange = (value: number) => {
    specId.value = value;
    triggerChange();
  };

  const handleMachinePairCntChange = (value: number) => {
    machinePairCnt.value = value;
    triggerChange();
  };
</script>
<style lang="less">
  .es-cluster-expansion-resource-pool-selector {
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
