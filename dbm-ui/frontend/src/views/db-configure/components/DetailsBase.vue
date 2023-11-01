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
      style="height: 100%;"
      :z-index="12">
      <DbCard
        class="base-card"
        mode="collapse"
        :title="$t('基础信息')">
        <EditInfo
          :columns="baseInfoColumns"
          :data="data"
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
          :sticky-top="stickyTop" />
      </DbCard>
      <DbCard
        v-for="(card) of extraParametersCards"
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

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import {
    updateBusinessConfig,
    updatePlatformConfig,
  } from '@services/source/configs';
  import type {
    BizConfDetailsUpdateParams,
    ConfigBaseDetails,
    GetLevelConfigParams,
    PlatConfDetailsParams,
    PlatConfDetailsUpdateParams,
  } from '@services/types/configs';

  import {
    ConfLevels,
    type ConfLevelValues,
  } from '@common/const';

  import EditInfo, { type EditEmitData } from '@components/editable-info/index.vue';

  import type { ExtraConfListItem } from '../common/types';

  import ReadonlyTable from './ReadonlyTable.vue';

  interface Props {
    data?: ConfigBaseDetails,
    loading?: boolean,
    fetchParams?: PlatConfDetailsParams | GetLevelConfigParams,
    stickyTop?: number,
    level?: ConfLevelValues,
    title?: string,
    extraParametersCards?: ExtraConfListItem[],
    routeParams?: Record<string, any>,
  }

  interface Emits {
    (e:'update-info', value: { key: string, value: string }): void
  }

  type updateFuncParam = PlatConfDetailsUpdateParams & BizConfDetailsUpdateParams;

  const props = withDefaults(defineProps<Props>(), {
    data: () => ({} as ConfigBaseDetails),
    loading: false,
    fetchParams: () => ({} as PlatConfDetailsParams),
    stickyTop: 0,
    level: ConfLevels.PLAT,
    title: '',
    extraParametersCards: () => ([]),
    routeParams: () => ({}),
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const cardTitle = computed(() => props.title || t('参数配置'));
  // 是否为平台级别配置
  const isPlat = computed(() => ConfLevels.PLAT === props.level);
  const configItems = computed(() => props.data?.conf_items || []);
  const baseInfoColumns = computed(() => [
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
  ]);
  // 更新基础信息 api
  const updateConfig = computed(() => (isPlat.value ? updatePlatformConfig : updateBusinessConfig));

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
    updateConfig.value(params)
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
      params: { ...route.params, ...props.routeParams, ...extra },
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
