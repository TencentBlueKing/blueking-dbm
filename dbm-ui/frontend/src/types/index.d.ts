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

import type { TablePropTypes } from 'bkui-vue/lib/table/props';
import type { Router } from 'vue-router';

import type { Permission } from '@services/types';

declare global {
  interface Window {
    changeConfirm: boolean | 'popover';
    login: {
      showLogin: ({ src, width, height }) => void;
      hideLogin: () => void;
      isShow: boolean;
    };
    permission: {
      show: (permission: Permission) => void;
      isShow: boolean;
    };
  }
  interface Element {
    _bk_overflow_tips_: any;
    _tippy: any;
  }

  interface FocusEvent {
    sourceCapabilities: any;
  }

  interface DragEvent {
    target: {
      innerText: string;
    };
    relatedTarget: {
      innerText: string;
    } | null;
  }

  type ClusterTableProps = {
    -readonly [K in keyof TablePropTypes]: TablePropTypes[K];
  };

  type BKTagTheme = 'success' | 'info' | 'warning' | 'danger' | undefined;
}

declare module 'pinia' {
  interface PiniaCustomProperties {
    router: Router;
  }
}

// export {} 将其标记为外部模块，模块是至少包含1个导入或导出语句的文件，我们必须这样做才能扩展全局范围
export {};
