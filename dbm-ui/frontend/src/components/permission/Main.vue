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
  <div class="permission-main">
    <BkException
      class="permission-main__exception"
      scene="part"
      type="403">
      <span>{{ $t('该操作需要以下权限') }}</span>
    </BkException>
    <DbOriginalTable
      :columns="columns"
      :data="tableData"
      :min-height="0" />
  </div>
</template>
<script lang="ts">
  import type { PropType } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { Permission, PermissionAction } from '@services/types/common';

  export default {
    name: 'PermissionTable',
  };
</script>

<script setup lang="ts">
  const props = defineProps({
    permission: {
      required: true,
      type: Object as PropType<Permission>,
    },
  });

  const { t } = useI18n();

  const tableData = computed(() => {
    const actions = props.permission?.permission?.actions || [];

    if (actions.length === 0) return [];

    return actions.map((action: PermissionAction) => {
      const resources: string[] = [];
      const relatedResourceTypes = action.related_resource_types || [];
      for (const related of relatedResourceTypes) {
        const instances = related.instances || [];
        for (const instance of instances) {
          const names = instance.map(item => `【${item.type_name}】${item.name}`);
          resources.push(names.join(' / '));
        }
      }
      return {
        permission: action.name,
        resource: resources.join(' / '),
      };
    });
  });

  const columns = [{
    label: t('需申请的权限'),
    field: 'permission',
  }, {
    label: t('关联的资源实例'),
    field: 'resource',
    render: ({ cell }: { cell: string }) => cell || t('无关联资源实例'),
  }];
</script>

<style lang="less" scoped>
  .permission-main {
    padding-bottom: 24px;

    &__exception {
      padding-bottom: 24px;

      :deep(.bk-exception-img) {
        height: 130px;
      }

      span {
        font-size: 20px;
      }
    }
  }
</style>
