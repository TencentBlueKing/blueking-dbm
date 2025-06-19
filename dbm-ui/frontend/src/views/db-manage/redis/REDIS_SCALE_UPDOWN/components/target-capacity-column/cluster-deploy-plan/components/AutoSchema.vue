<template>
  <DbFormItem
    :label="t('目标容量')"
    property="capacity"
    required
    :rules="rules">
    <div class="input-box">
      <BkInput
        ref="capacityInputRef"
        class="mb10"
        :min="0"
        :model-value="capacity"
        style="width: 314px"
        type="number"
        @change="handleChange" />
      <div class="uint-text ml-12">
        <span>{{ t('当前') }}</span>
        <span class="spec-text">{{ cluster.cluster_capacity }}</span>
        <span>G</span>
      </div>
    </div>
  </DbFormItem>
  <BkLoading :loading="loading">
    <DbOriginalTable
      class="deploy-table"
      :columns="columns"
      :data="tableData"
      @column-sort="handleColumnSort"
      @row-click.stop="handleRowClick">
      <template #empty>
        <p
          v-if="!capacity"
          style="width: 100%; line-height: 128px; text-align: center">
          <DbIcon
            class="mr-4"
            type="attention" />
          <span>{{ t('请先设置容量') }}</span>
        </p>
        <BkException
          v-else
          :description="t('无匹配的资源规格_请先修改容量设置')"
          scene="part"
          style="font-size: 12px"
          type="empty" />
      </template>
    </DbOriginalTable>
  </BkLoading>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type RedisModel from '@services/model/redis/redis';
  import type ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getFilterClusterSpec } from '@services/source/dbresourceSpec';

  import { ClusterTypes } from '@common/const';

  import { messageError } from '@utils';

  interface Props {
    cluster: RedisModel;
  }

  type Emits = (e: 'change', data: ClusterSpecModel) => void;

  interface Exposes {
    choose(id: number): void;
    disable(id: number): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const capacityInputRef = ref();
  const capacity = ref('');
  const tableData = ref<ClusterSpecModel[]>([]);
  const radioValue = ref(-1);
  const radioChoosedId = ref(-1); // 标记，sort重新定位index用
  let rawTableData: ClusterSpecModel[] = [];
  const specDisabledMap = shallowRef<Record<number, boolean>>({});

  /**
   * 非Tendisplus集群（≠PredixyTendisplusCluster）
    - 去掉推荐方案里的集群分片
    - 选择的方案，必须能被当前集群分片数整除。
    - 提交时，目标集群分片数使用当前集群分片数

    Tendisplus集群（＝PredixyTendisplusCluster） 
    - 保留推荐方案里的集群分片
    - 提交时，目标集群分片数用方案里的集群分片数
   */
  const isTendisplus = computed(() => props.cluster.cluster_type === ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER);

  const { loading, run: fetchData } = useRequest(getFilterClusterSpec, {
    manual: true,
    onSuccess(data) {
      radioValue.value = -1;
      tableData.value = data;
      rawTableData = _.cloneDeep(data);
      specDisabledMap.value = {};
    },
  });

  const rules = [
    {
      message: t('容量不能为空'),
      trigger: 'change',
      validator: () => !!capacity.value,
    },
  ];

  const isDisabled = (row: ClusterSpecModel) => {
    // 非Tendisplus集群，选择的方案，必须能被当前集群分片数整除
    return !isTendisplus.value && props.cluster.cluster_shard_num % row.machine_pair !== 0;
  };

  const columns = [
    {
      field: 'spec',
      label: t('资源规格'),
      render: ({ index, row }: { index: number; row: ClusterSpecModel }) => (
        <div style='display:flex;align-items:center;'>
          <bk-radio
            v-model={radioValue.value}
            disabled={specDisabledMap.value[row.spec_id] || isDisabled(row)}
            label={index}>
            <span style='font-size: 12px'>{row.spec_name}</span>
          </bk-radio>
        </div>
      ),
      showOverflowTooltip: true,
      width: 260,
    },
    {
      field: 'machine_pair',
      label: t('需机器组数'),
      sort: true,
    },
    {
      field: 'cluster_shard_num',
      label: t('集群分片'),
      sort: true,
    },
    {
      field: 'cluster_capacity',
      label: t('集群容量(G)'),
      sort: true,
    },
  ];

  const handleChange = (value: string) => {
    capacity.value = value;
    const capacityNum = Number(value);
    if (capacityNum > 0) {
      const params = {
        capacity: capacityNum,
        future_capacity: capacityNum,
        spec_cluster_type: 'redis',
        spec_machine_type: props.cluster.cluster_type,
      };
      fetchData(params);
    }
  };

  const handleRowClick = (_event: PointerEvent, row: ClusterSpecModel, index: number) => {
    if (isDisabled(row)) {
      messageError(t('当前集群分片数不能被该规格的机器组数整除，请选择其他规格'));
      return;
    }
    if (index === radioValue.value || specDisabledMap.value[row.spec_id]) {
      return;
    }
    radioValue.value = index;
  };

  const handleColumnSort = (data: { column: { field: string }; index: number; type: string }) => {
    const { column, type } = data;
    const field = column.field as keyof ClusterSpecModel;

    if (type === 'asc' || type === 'desc') {
      const multiplier = type === 'asc' ? 1 : -1;
      tableData.value.sort((a, b) => {
        const aValue = a[field] as number;
        const bValue = b[field] as number;
        return (aValue - bValue) * multiplier;
      });
    } else {
      tableData.value = [...rawTableData];
    }

    const selectedIndex = tableData.value.findIndex((item) => item.spec_id === radioChoosedId.value);
    radioValue.value = selectedIndex;
  };

  watch(radioValue, () => {
    if (radioValue.value !== -1) {
      emits(
        'change',
        Object.assign(_.cloneDeep(tableData.value[radioValue.value]), {
          cluster_shard_num: isTendisplus.value
            ? tableData.value[radioValue.value].cluster_shard_num
            : props.cluster.cluster_shard_num,
        }),
      );
    }
  });

  defineExpose<Exposes>({
    choose(id) {
      radioChoosedId.value = id;
    },
    disable(id: number) {
      // init
      radioValue.value = -1;
      radioChoosedId.value = -1;
      specDisabledMap.value[id] = true;
    },
  });
</script>
