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
  <FormItemWithHint
    class="apply-items-cluster-name"
    :label="t('集群标识')"
    property="details.cluster_name"
    required
    :rules="rules">
    <div class="item-input-wrapper">
      <DbInput
        v-model="modelValue"
        class="item-input"
        clearable
        :maxlength="63"
        :placeholder="t('请输入集群标识')"
        show-word-limit />
      <div class="cluster-name-preview ml-12">
        <span>{{ t('域名预览：') }}</span>
        <span>{{ clusterNamePreview.masterDomain.prefix }}</span>
        <span
          v-if="modelValue"
          class="cluster-name-value">
          {{ modelValue }}
        </span>
        <span v-else>{{ '{' + t('集群标识') + '}' }}</span>
        <span>{{ clusterNamePreview.masterDomain.suffix }}</span>
      </div>
    </div>
    <template #hint>
      {{ t('仅支持小写字母、数字、连字符，同时会参与集群域名生成，') }}
      <span class="hint-warning">{{ t('创建后不可改') }}</span>
    </template>
  </FormItemWithHint>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkDomainRepeat } from '@services/source/ticket';

  import { ClusterTypes } from '@common/const';
  import { clusterNameFormatRegx, clusterNameSymbolRegx } from '@common/regex';

  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  import { dbModuleClusterTypes } from '@views/db-manage/const/dbModuleClusterTypes';
  import { getDomainStrategy } from '@views/db-manage/utils/getDomainPreview';

  interface Props {
    bizId: number | '';
    clusterType: ClusterTypes;
    dbAppAbbr: string;
    dbModuleId?: number | null;
    dbModuleName?: string;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('不能以连字符开头或结尾'),
      trigger: 'blur',
      validator: (value: string) => clusterNameFormatRegx.test(value),
    },
    {
      message: t('格式不正确，请勿使用中文、大写、空格、下划线或特殊符号'),
      trigger: 'blur',
      validator: (value: string) => clusterNameSymbolRegx.test(value),
    },
    {
      message: t('该域名已被占用，请修改集群标识'),
      trigger: 'blur',
      validator: (val: string) => {
        const isModuleRelatedClusterTypes = dbModuleClusterTypes.includes(props.clusterType);

        if (isModuleRelatedClusterTypes) {
          if (!props.bizId || !props.dbModuleId) {
            return true;
          }
        } else {
          if (!props.bizId) {
            return true;
          }
        }

        return checkDomainRepeat({
          cluster_type: props.clusterType,
          db_app_abbr: dbModuleClusterTypes.includes(props.clusterType)
            ? props.dbAppAbbr || `biz-${props.bizId}`
            : props.dbAppAbbr,
          db_module_id: dbModuleClusterTypes.includes(props.clusterType) ? props.dbModuleId : undefined,
          domains: [val],
        }).then((result) => {
          return !result[0].validate;
        });
      },
    },
  ];

  const clusterNamePreview = computed(() => {
    const strategy = getDomainStrategy(props.clusterType);
    const isModuleRelatedClusterTypes = dbModuleClusterTypes.includes(props.clusterType);

    return strategy(
      {
        clusterName: modelValue.value,
        dbAppAbbr: props.dbAppAbbr,
        moduleName: props.dbModuleName,
      },
      isModuleRelatedClusterTypes
        ? {
            bizId: props.bizId,
          }
        : undefined,
    );
  });
</script>

<style lang="less">
  .apply-items-cluster-name {
    .item-input-wrapper {
      display: flex;
    }

    .cluster-name-preview {
      display: flex;
      align-items: center;
      font-size: 12px;
      color: #63656e;

      .cluster-name-value {
        color: #3a84ff;
      }
    }

    .hint-warning {
      color: rgb(255 156 1);
    }
  }
</style>
