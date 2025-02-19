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
  type DetailData = { charset?: string } & ServiceReturnType<typeof getLevelConfig>;

  interface Props {
    data?: Partial<DetailData>;
    deployInfo?: Partial<DetailData>;
    extraParametersCards?: ExtraConfListItem[];
    fetchParams?: PlatConfDetailsParams | ServiceParameters<typeof getLevelConfig>;
    level?: ConfLevelValues;
    loading?: boolean;
    routeParams?: Record<string, any>;
    stickyTop?: number;
    title?: string;
  }

  type Emits = (e: 'update-info', value: { key: string; value: string }) => void;

  type updateFuncParam = ServiceParameters<typeof updateBusinessConfig> &
    ServiceParameters<typeof updatePlatformConfig>;

  const props = withDefaults(defineProps<Props>(), {
    data: () => ({}) as NonNullable<Props['data']>,
    deployInfo: () => ({
      conf_items: [] as DetailData['conf_items'],
    }),
    extraParametersCards: () => [],
    fetchParams: () => ({}) as PlatConfDetailsParams,
    level: ConfLevels.PLAT,
    loading: false,
    routeParams: () => ({}),
    stickyTop: 0,
    title: '',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const { state } = useBaseDetails(true, 'spider_version');

  const clusterType = ref(props.data.version);

  const isSqlServer = computed(() =>
    [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE].includes(props.routeParams.clusterType),
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
          isEdit: isPlat.value,
          key: 'name',
          label: t('配置名称'),
        },
        {
          isEdit: true,
          key: 'description',
          label: t('描述'),
        },
        {
          key: 'version',
          label: t('数据库版本'),
        },
      ],
      [
        {
          key: 'updated_at',
          label: t('更新时间'),
        },
        {
          key: 'updated_by',
          label: t('更新人'),
        },
      ],
    ];
    if (isShowCharset.value) {
      baseColumns[1].push({
        key: 'charset',
        label: t('字符集'),
      });
    }
    if (isSqlServer.value) {
      baseColumns[0].push(
        ...[
          {
            key: 'buffer_percent',
            label: t('实际内存分配比率'),
          },
          {
            key: 'sync_type',
            label: t('主从方式'),
            render: () => (
              <span> {detailData.value.sync_type === 'mirroring' ? t('镜像') : detailData.value.sync_type} </span>
            ),
          },
        ],
      );
      baseColumns[1].push(
        ...[
          {
            key: 'max_remain_mem_gb',
            label: t('最大系统保留内存'),
          },
          {
            key: 'system_version',
            label: t('操作系统版本'),
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
          return Object.assign(acc, {
            [item.conf_name]: item.conf_value,
          });
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
  const handleSaveEditInfo = ({ editResolve, key, value }: EditEmitData) => {
    // 默认需要把所有信息带上，否则接口会报错。
    const params = {
      ...props.fetchParams,
      conf_items: [],
      confirm: 0,
      description: props.data.description,
      [key]: value,
      name: props.data.name,
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
