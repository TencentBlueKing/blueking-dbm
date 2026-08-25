<template>
  <DbFormItem
    :label="t('目标容量')"
    property="capacity"
    required
    :rules="capacityRules">
    <div class="input-box">
      <BkInput
        class="mb10"
        :min="0"
        :model-value="capacity"
        style="width: 314px"
        type="number"
        @change="handleCapacityChange" />
      <div class="uint-text ml-12">
        <span>{{ t('当前') }}</span>
        <span class="spec-text">{{ cluster.cluster_capacity }}</span>
        <span>G</span>
      </div>
    </div>
  </DbFormItem>
  <DbFormItem
    :label="t('资源标签')"
    property="labels"
    required
    :rules="resourceTagRules">
    <ResourceTagSelector
      ref="resourceTagSelector"
      v-model="labels"
      style="width: 314px"
      @change="handleTesourceTagChange" />
  </DbFormItem>
  <BkLoading :loading="loading">
    <PrimaryTable
      class="deploy-table"
      :columns="columns"
      :data="tableData"
      row-key="spec_id"
      @row-click="handleRowClick"
      @sort-change="handleColumnSort">
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
    </PrimaryTable>
  </BkLoading>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import type { PrimaryTableCol, TableRowData, TableSort } from 'tdesign-vue-next';
  import type { UnwrapRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type RedisModel from '@services/model/redis/redis';
  import type ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getFilterClusterSpec } from '@services/source/dbresourceSpec';

  import { ClusterTypes } from '@common/const';

  import ResourceTagSelector from '@views/db-manage/common/apply-items/ResourceTagSelector.vue';

  import { messageError } from '@utils';

  interface Props {
    cluster: RedisModel;
  }

  interface Emits {
    (e: 'spec-change', value: ClusterSpecModel): void;
    (e: 'label-change', value: UnwrapRef<typeof labels>): void;
  }

  interface Exposes {
    choose(id: number): void;
    disable(id: number): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const resourceTagSelector = useTemplateRef('resourceTagSelector');

  const capacity = ref('');
  const labels = ref<ComponentProps<typeof ResourceTagSelector>['modelValue']>([]);
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

  const capacityRules = [
    {
      message: t('容量不能为空'),
      trigger: 'change',
      validator: () => !!capacity.value,
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

  const isDisabled = (row: ClusterSpecModel) => {
    // 非Tendisplus集群，选择的方案，必须能被当前集群分片数整除
    return !isTendisplus.value && props.cluster.cluster_shard_num % row.machine_pair !== 0;
  };

  const columns = computed(() => {
    const cols: PrimaryTableCol[] = [
      {
        cell: (_, { row, rowIndex }) => (
          <div style='display:flex;align-items:center;'>
            <bk-radio
              v-model={radioValue.value}
              disabled={specDisabledMap.value[row.spec_id] || isDisabled(row as ClusterSpecModel)}
              label={rowIndex}>
              <span style='font-size: 12px'>{row.spec_name}</span>
            </bk-radio>
          </div>
        ),
        colKey: 'spec',
        ellipsis: true,
        title: t('资源规格'),
        width: 260,
      },
      {
        colKey: 'machine_pair',
        sorter: true,
        title: t('需机器组数'),
      },
      {
        colKey: 'cluster_capacity',
        sorter: true,
        title: t('集群容量(G)'),
      },
    ];

    if (isTendisplus.value) {
      cols.splice(2, 0, {
        colKey: 'cluster_shard_num',
        sorter: true,
        title: t('集群分片'),
      });
    }

    return cols;
  });

  const handleCapacityChange = (value: string) => {
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

  const handleRowClick = ({ index, row }: { index: number; row: TableRowData }) => {
    if (isDisabled(row as ClusterSpecModel)) {
      messageError(t('当前集群分片数不能被该规格的机器组数整除，请选择其他规格'));
      return;
    }
    if (index === radioValue.value || specDisabledMap.value[row.spec_id]) {
      return;
    }
    radioValue.value = index;
  };

  const handleColumnSort = (payload: TableSort) => {
    if (Array.isArray(payload)) {
      return;
    }
    if (payload) {
      const field = payload.sortBy as keyof ClusterSpecModel;
      const sortOrder = payload.descending ? -1 : 1;
      tableData.value.sort((a, b) => ((a[field] as number) - (b[field] as number)) * sortOrder);
    } else {
      tableData.value = [...rawTableData];
    }

    const selectedIndex = tableData.value.findIndex((item) => item.spec_id === radioChoosedId.value);
    radioValue.value = selectedIndex;
  };

  watch(radioValue, () => {
    if (radioValue.value !== -1) {
      emits(
        'spec-change',
        Object.assign(_.cloneDeep(tableData.value[radioValue.value]), {
          cluster_shard_num: isTendisplus.value
            ? tableData.value[radioValue.value].cluster_shard_num
            : props.cluster.cluster_shard_num,
        }),
      );
    }
  });

  const handleTesourceTagChange = (value: UnwrapRef<typeof labels>) => {
    emits('label-change', value);
  };

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
