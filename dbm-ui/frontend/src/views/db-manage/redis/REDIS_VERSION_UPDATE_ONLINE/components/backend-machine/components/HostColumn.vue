<template>
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="host.ip"
    fixed="left"
    :label="t('目标主机')"
    :loading="isLoading"
    :min-width="240"
    required>
    <template #headAppend>
      <BkButton
        text
        theme="primary"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </BkButton>
    </template>
    <div style="flex: 1">
      <EditableInput v-model="modelValue.ip"> </EditableInput>
      <BkLoading
        v-if="modelValue.pair_machine?.ip"
        class="pair_machine"
        :loading="pairLoading">
        <div>{{ t('关联 Slave') }}</div>
        <div>-- {{ modelValue.pair_machine.ip }}</div>
      </BkLoading>
    </div>
    <HostSelector
      v-model:is-show="isShowSelector"
      :cluster-types="[ClusterTypes.REDIS]"
      :data-source-map="dataSourceMap"
      :model-value="selectedList"
      @change="handleInstanceSelectChange" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getGlobalMachine } from '@services/source/dbbase';
  import { getRedisMachineList } from '@services/source/redis';
  import { queryMachineInstancePair } from '@services/source/redisToolbox';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import HostSelector, { type HostModel, type HostSelectorValues } from '@components/host-selector/Index.vue';

  interface Props {
    selected: {
      ip: string;
    }[];
  }

  type Emits = (e: 'batch-edit', value: HostModel<ClusterTypes.REDIS>[]) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id: number;
    cluster_type: string;
    instance_role: string;
    ip: string;
    pair_machine: {
      bk_host_id: number;
      ip: string;
      related_clusters: {
        id: number;
      }[];
    };
    related_clusters: {
      id: number;
      immute_domain: string;
    }[];
  }>({
    required: true,
  });

  const { t } = useI18n();

  // 存储层主机：主从角色均可见（与旧实现 firsrColumn.role 的接口过滤语义一致）
  const dataSourceMap = {
    [ClusterTypes.REDIS]: (params: ServiceParameters<typeof getRedisMachineList>) =>
      getRedisMachineList({
        ...params,
        instance_role: 'redis_master,redis_slave',
      }),
  };

  const rules = [
    {
      message: t('目标主机输入格式有误'),
      trigger: 'change',
      validator: (value: string) => ipv4.test(value),
    },
    {
      message: t('目标主机重复'),
      trigger: 'blur',
      validator: (value: string) => props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.bk_host_id),
    },
  ];

  const isShowSelector = ref(false);
  const isLoading = ref(false);

  const selectedList = computed<HostSelectorValues<ClusterTypes.REDIS>>(
    () =>
      ({
        [ClusterTypes.REDIS]: props.selected,
      }) as unknown as HostSelectorValues<ClusterTypes.REDIS>,
  );

  const { loading: pairLoading, run: runQueryMachineInstancePair } = useRequest(queryMachineInstancePair, {
    manual: true,
    onSuccess: (data) => {
      const machines = data.machines!;
      const slaveInfo = machines[`${modelValue.value.bk_cloud_id}:${modelValue.value.ip}`];
      modelValue.value.pair_machine = {
        bk_host_id: slaveInfo.bk_host_id,
        ip: slaveInfo.ip,
        related_clusters: slaveInfo.related_clusters,
      };
    },
  });

  watch(
    () => modelValue.value.ip,
    () => {
      if (!modelValue.value.bk_host_id && modelValue.value.ip) {
        isLoading.value = true;
        modelValue.value.bk_host_id = 0;
        getGlobalMachine({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          db_type: DBTypes.REDIS,
          ip: modelValue.value.ip,
        })
          .then((data) => {
            if (data.results.length > 0) {
              modelValue.value = {
                ...data.results[0],
                pair_machine: {
                  bk_host_id: 0,
                  ip: '',
                  related_clusters: [] as UnwrapRef<typeof modelValue>['pair_machine']['related_clusters'],
                },
              };
              if (data.results[0].instance_role === 'redis_master') {
                runQueryMachineInstancePair({
                  machines: [`${data.results[0].bk_cloud_id}:${data.results[0].ip}`],
                });
              }
            }
          })
          .finally(() => {
            isLoading.value = false;
          });
      }
      if (!modelValue.value.ip) {
        modelValue.value.bk_host_id = 0;
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleInstanceSelectChange = (data: HostSelectorValues<ClusterTypes.REDIS>) => {
    const hostList = Object.values(data).flatMap((selectedList) => selectedList);
    emits('batch-edit', hostList);
  };
</script>

<style lang="less" scoped>
  .host-selector-btn {
    width: 24px;
    font-size: 16px;
    border: none;
    border-radius: 2px;

    &:hover {
      color: #3a84ff;
      background: #f0f1f5;
    }
  }

  .pair_machine {
    padding: 4px 8px;
    font-size: 12px;
    line-height: 16px;
    color: #979ba5;
    background: #fafbfd;
  }
</style>
