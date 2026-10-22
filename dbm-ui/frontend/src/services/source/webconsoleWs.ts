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

import { t } from '@locales/index';

export type WebconsoleState = 'connecting' | 'initializing' | 'ready' | 'executing' | 'disconnected' | 'closed';

export interface WebconsoleResponse {
  code?: number | string;
  error: string;
  result?: unknown;
  rows_affected?: number;
}

export interface WebconsoleOptions {
  charset: string;
  role: 'backend_master' | 'backend_slave' | 'orphan';
}

export class WebconsoleError extends Error {
  constructor(
    message: string,
    public readonly code?: number | string,
    public readonly cancelled = false,
  ) {
    super(message);
    this.name = 'WebconsoleError';
  }
}

interface Pending {
  reject: (error: WebconsoleError) => void;
  resolve: (response: WebconsoleResponse) => void;
  timer: ReturnType<typeof setTimeout>;
  type: 'CONNECT' | 'COMMAND';
}

// 浏览器等待守卫不覆盖服务端超时；COMMAND 为默认 600 秒执行上限留出回包时间。
const CONNECT_WAIT_MS = 30_000;
const COMMAND_WAIT_MS = 610_000;

export function createWebconsoleConnection(
  params: { baseUrl: string; clusterId: number; options: WebconsoleOptions },
  onState: (state: WebconsoleState, error?: WebconsoleError) => void,
) {
  let socket: WebSocket | undefined;
  let state: WebconsoleState = 'connecting';
  let pending: Pending | undefined;
  let finished = false;

  const setState = (next: WebconsoleState, error?: WebconsoleError) => {
    state = next;
    onState(next, error);
  };

  const settle = (response?: WebconsoleResponse, error?: WebconsoleError) => {
    const current = pending;
    pending = undefined;
    if (!current) {
      return;
    }
    clearTimeout(current.timer);
    if (error) {
      current.reject(error);
    } else if (response) {
      current.resolve(response);
    }
  };

  // 解绑旧 socket 回调并结算 Promise，迟到结果不能进入新会话。
  const finish = (error: WebconsoleError, next: WebconsoleState = 'disconnected') => {
    if (finished) {
      return;
    }
    finished = true;
    if (socket) {
      socket.onopen = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
    }
    settle(undefined, error);
    setState(next, error);
  };

  const createPending = (type: Pending['type']) =>
    new Promise<WebconsoleResponse>((resolve, reject) => {
      pending = {
        reject,
        resolve,
        timer: setTimeout(
          () => {
            finish(
              new WebconsoleError(
                type === 'COMMAND' ? t('WebConsole_等待超时_结果未知') : t('WebConsole_连接等待超时'),
                'CLIENT_TIMEOUT',
              ),
            );
          },
          type === 'CONNECT' ? CONNECT_WAIT_MS : COMMAND_WAIT_MS,
        ),
        type,
      };
    });

  const send = (payload: Record<string, unknown>) => {
    try {
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        throw new Error();
      }
      socket.send(JSON.stringify(payload));
    } catch {
      finish(new WebconsoleError(t('WebConsole_消息发送失败')));
    }
  };

  const ready = createPending('CONNECT').then(() => undefined);
  try {
    const url = new URL('/ws/dbbase/webconsole/', params.baseUrl);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    socket = new WebSocket(url);
    socket.onopen = () => {
      setState('initializing');
      send({
        body: {},
        cluster_id: params.clusterId,
        options: { ...params.options },
        'request-type': 'CONNECT',
      });
    };
    socket.onmessage = (event: MessageEvent<unknown>) => {
      let response: WebconsoleResponse;
      try {
        if (typeof event.data !== 'string') {
          throw new Error();
        }
        const data: unknown = JSON.parse(event.data);
        if (typeof data !== 'object' || data === null || Array.isArray(data)) {
          throw new Error();
        }
        const record = data as Record<string, unknown>;
        if (
          typeof record.error !== 'string' ||
          (record.code !== undefined && typeof record.code !== 'number' && typeof record.code !== 'string') ||
          (record.rows_affected !== undefined && typeof record.rows_affected !== 'number') ||
          (pending?.type === 'COMMAND' &&
            record.error === '' &&
            !Object.prototype.hasOwnProperty.call(record, 'result'))
        ) {
          throw new Error();
        }
        response = record as unknown as WebconsoleResponse;
      } catch {
        finish(
          new WebconsoleError(
            pending?.type === 'COMMAND' ? t('WebConsole_非法响应_结果未知') : t('WebConsole_非法响应'),
            'INVALID_RESPONSE',
          ),
        );
        return;
      }
      if (!pending) {
        finish(new WebconsoleError(response.error || t('WebConsole_非法响应'), response.code));
        return;
      }
      if (response.error !== '') {
        const code = Number(response.code);
        if (pending.type === 'CONNECT' || [401, 403, 408, 4401, 4403].includes(code)) {
          finish(new WebconsoleError(response.error, response.code));
        } else {
          // 校验失败、限流等业务错误不销毁仍有效的会话。
          settle(response);
          setState('ready');
        }
        return;
      }
      settle(response);
      setState('ready');
    };
    socket.onclose = (event) => {
      const messages: Record<number, string> = {
        4400: t('WebConsole_连接协议错误'),
        4401: t('WebConsole_登录失效'),
        4403: t('WebConsole_无访问权限'),
      };
      const message = messages[event.code] || t('WebConsole_连接已断开');
      finish(
        new WebconsoleError(
          pending?.type === 'COMMAND' ? `${message}${t('WebConsole_执行结果未知后缀')}` : message,
          event.code,
        ),
      );
    };
    // error 通常紧接 close，保留关闭码；等待守卫兜底无 close 的情况。
    socket.onerror = () => undefined;
  } catch {
    finish(new WebconsoleError(t('WebConsole_连接失败')));
  }

  return {
    close() {
      finish(new WebconsoleError(t('WebConsole_会话已关闭'), undefined, true), 'closed');
    },
    execute(command: string) {
      if (finished || state !== 'ready' || pending) {
        return Promise.reject(new WebconsoleError(t('WebConsole_请先连接')));
      }
      const result = createPending('COMMAND');
      setState('executing');
      send({ body: { command }, 'request-type': 'COMMAND' });
      return result;
    },
    ready,
  };
}
