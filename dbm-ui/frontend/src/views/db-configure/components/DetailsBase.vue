<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="details-base">
    <BkLoading
      :loading="loading"
      style="height: 100%"
      :z-index="12">
      <DbCard
        class="base-card"
        mode="collapse"
        :title="$t('基础信息')">
        <EditInfo
          :columns="baseInfoColumns"
          :data="detailData"
          @save="handleSaveEditInfo" />
      </DbCard>
      <DbCard
        class="params-card"
        mode="collapse"
        :title="cardTitle">
        <template #desc>
          <i
            class="db-icon-edit edit-parameter"
            @click.stop="handleToEdit" />
        </template>
        <ReadonlyTable
          class="details-base__table"
          :data="configItems"
          :level="level"
          :sticky-top="stickyTop">
          <template
            v-if="tabs.length > 1"
            #prefix>
            <BkRadioGroup
              v-model="clusterType"
              type="capsule">
              <BkRadioButton
                v-for="tab of tabs"
                :key="tab"
                :label="tab"
                style="width: 200px">
                {{ tab }} {{ t('参数配置') }}
              </BkRadioButton>
            </BkRadioGroup>
          </template>
        </ReadonlyTable>
      </DbCard>
      <DbCard
        v-for="card of extraParametersCards"
        :key="card.conf_type"
        class="params-card"
        mode="collapse"
        :title="card.title">
        <template #desc>
          <i
            class="db-icon-edit edit-parameter"
            @click.stop="handleToEdit({ confType: card.conf_type, version: card.version })" />
        </template>
        <ReadonlyTable
          class="details-base__table"
          :data="card.data?.conf_items || []"
          :level="level"
          :sticky-top="props.stickyTop" />
      </DbCard>
    </BkLoading>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import {
    getConfigBaseDetails,
    getLevelConfig,
    updateBusinessConfig,
    updatePlatformConfig,
  } from '@services/source/configs';

  import { ClusterTypes, ConfLevels, type ConfLevelValues } from '@common/const';

  import EditInfo, { type EditEmitData } from '@components/editable-info/index.vue';

  import { useBaseDetails } from '../business/list/components/hooks/useBaseDetails';
  import type { ExtraConfListItem } from '../common/types';

  import ReadonlyTable from './ReadonlyTable.vue';

  type PlatConfDetailsParams = ServiceParameters<typeof getConfigBaseDetails>;
  type DetailData = ServiceReturnType<typeof getLevelConfig> & { charset?: string };

  interface Props {
    data?: Partial<DetailData>;
    loading?: boolean;
    fetchParams?: PlatConfDetailsParams | ServiceParameters<typeof getLevelConfig>;
    stickyTop?: number;
    level?: ConfLevelValues;
    title?: string;
    extraParametersCards?: ExtraConfListItem[];
    routeParams?: Record<string, any>;
    deployInfo?: Partial<DetailData>;
  }

  interface Emits {
    (e: 'update-info', value: { key: string; value: string }): void;
  }

  // eslint-disable-next-line max-len
  type updateFuncParam = ServiceParameters<typeof updatePlatformConfig> &
    ServiceParameters<typeof updateBusinessConfig>;

  const props = withDefaults(defineProps<Props>(), {
    data: () => ({}) as NonNullable<Props['data']>,
    loading: false,
    fetchParams: () => ({}) as PlatConfDetailsParams,
    stickyTop: 0,
    level: ConfLevels.PLAT,
    title: '',
    extraParametersCards: () => [],
    routeParams: () => ({}),
    deployInfo: () =>
    ({
      conf_items: [] as DetailData['conf_items'],
    }),
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const { state } = useBaseDetails(true, 'spider_version');

  const clusterType = ref(props.data.version);

  const isSqlServer = computed(() =>
    [ClusterTypes.SQLSERVER_SINGLE, ClusterTypes.SQLSERVER_HA].includes(props.routeParams.clusterType),
  );
  const tabs = computed(() => {
    if (!state.version) {
      return [props.data.version];
    }
    return [props.data.version, state.data.version];
  });
  const cardTitle = computed(() => props.title || t('参数配置'));
  // 是否为平台级别配置
  const isPlat = computed(() => ConfLevels.PLAT === props.level);
  const configItems = computed(() => {
    if (clusterType.value === props.data.version) {
      return props.data.conf_items;
    }
    return state.data.conf_items;
  });
  const isShowCharset = computed(() => !!props.data.charset);
  const baseInfoColumns = computed(() => {
    const baseColumns = [
      [
        {
          label: t('配置名称'),
          key: 'name',
          isEdit: isPlat.value,
        },
        {
          label: t('描述'),
          key: 'description',
          isEdit: true,
        },
        {
          label: t('数据库版本'),
          key: 'version',
        },
      ],
      [
        {
          label: t('更新时间'),
          key: 'updated_at',
        },
        {
          label: t('更新人'),
          key: 'updated_by',
        },
      ],
    ];
    if (isShowCharset.value) {
      baseColumns[1].push({
        label: t('字符集'),
        key: 'charset',
      });
    }
    if (isSqlServer.value) {
      baseColumns[0].push(
        ...[
          {
            label: t('实际内存分配比率'),
            key: 'buffer_percent',
          },
          {
            label: t('主从方式'),
            key: 'sync_type',
            render: () => <span> {
              detailData.value.sync_type === 'mirroring'
                ? t('镜像')
                : detailData.value.sync_type
            } </span>
          },
        ],
      );
      baseColumns[1].push(
        ...[
          {
            label: t('最大系统保留内存'),
            key: 'max_remain_mem_gb',
          },
          {
            label: t('操作系统版本'),
            key: 'system_version',
          },
        ],
      );
    }
    if (state.version) {
      baseColumns[0].push({
        label: t('Spider版本'),
        render: () => state.data.version,
      });
    }
    return baseColumns;
  });
  const detailData = computed(() => {
    if (isSqlServer.value) {
      return {
        ...props.data,
        ...props.deployInfo.conf_items!.reduce<Record<string, string>>((acc, item) => {
          acc[item.conf_name] = item.conf_value!;
          return acc;
        }, {}),
      };
    }
    return props.data;
  });

  watch(
    () => props.data.version,
    () => {
      clusterType.value = props.data.version;
    },
    { immediate: true },
  );

  /**
   * 基础信息编辑
   */
  const handleSaveEditInfo = ({ value, key, editResolve }: EditEmitData) => {
    // 默认需要把所有信息带上，否则接口会报错。
    const params = {
      ...props.fetchParams,
      name: props.data.name,
      conf_items: [],
      description: props.data.description,
      confirm: 0,
      [key]: value,
    } as updateFuncParam;

    const handleRequest = isPlat.value ? updatePlatformConfig : updateBusinessConfig;
    handleRequest(params)
      .then(() => {
        editResolve(true);
        emits('update-info', { key, value });
      })
      .catch(() => {
        editResolve(false);
      });
  };

  /**
   * 编辑配置
   */
  const handleToEdit = (extra = {}) => {
    const name = isPlat.value ? 'PlatformDbConfigureEdit' : 'DbConfigureEdit';
    router.push({
      name,
      params: {
        ...route.params,
        ...props.routeParams,
        ...extra,
        version: clusterType.value,
      },
    });
  };
</script>

<style lang="less" scoped>
  .details-base {
    height: calc(100% - 32px);

    &__tips {
      color: @default-color;

      .db-icon-attention {
        margin-right: 4px;
        font-size: @font-size-normal;
      }
    }

    .edit-parameter {
      font-size: @font-size-large;
      color: @primary-color;
    }

    .params-card {
      margin-top: 16px;
    }
  }
</style>
