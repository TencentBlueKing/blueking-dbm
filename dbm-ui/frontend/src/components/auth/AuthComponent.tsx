/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
*/

import {
  checkAuthAllowed,
  getApplyDataLink,
} from '@services/source/iam';

import {
  permissionDialog,
} from '@utils';

import './style.less';

export default defineComponent({
  name: 'AuthComponent',
  props: {
    permission: {
      type: Boolean,
      default: false,
    },
    actionId: {
      type: String,
      required: true,
    },
    resourceType: {
      type: String,
      default: '',
    },
    resourceId: {
      type: [String, Number],
      default: '',
    },
    immediateCheck: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    const hasAuth = ref(false);

    const isRenderDefaultSlot = computed(() => {
      if (props.permission || hasAuth.value) {
        return true;
      }
      return false;
    });

    const fetchPermissionParams = computed(() => {
      const resources = [];

      if (props.resourceId && props.resourceType) {
        resources.push({
          id: props.resourceId,
          type: props.resourceType,
        });
      }

      return {
        action_ids: [props.actionId],
        resources,
      };
    });

    const checkPermission = () => {
      checkAuthAllowed(fetchPermissionParams.value)
        .then((res) => {
          hasAuth.value = res[0]?.is_allowed ?? false;
        });
    };

    const handleShowPermissionApply = (event: MouseEvent) => {
      event.stopPropagation();
      event.preventDefault();
      if (props.permission || hasAuth.value) return;

      getApplyDataLink(fetchPermissionParams.value)
        .then((res) => {
          permissionDialog(res);
        });
    };

    onBeforeMount(() => {
      if (props.immediateCheck) {
        checkPermission();
      }
    });

    return {
      isRenderDefaultSlot,
      handleShowPermissionApply,
    };
  },
  render() {
    if (this.isRenderDefaultSlot) {
      return this.$slots.default ? this.$slots.default() : null;
    }

    if (this.$slots.forbid) {
      return (
        <div
          class="permission-disabled"
          v-cursor
          onClick={this.handleShowPermissionApply}>
          {this.$slots.forbid ? this.$slots.forbid() : null}
        </div>
      );
    }

    return <div></div>;
  },
});
