# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQLServer 账号密码加密工具模块。

模块职责：
  - 为 DBM 工单侧下发到 SQLServer（如 linkserver 场景）的账号密码提供加密能力，
    使得密文可以被 Go 端（sqlserver-crond / dbactuator 等）用相同算法解密。

设计要点 / 数据源 / 通道：
  - 算法：AES-256-GCM（AEAD），密文中天然包含 16 字节认证 tag
  - 依赖：pycryptodome（项目 pyproject.toml 已直接声明，避免额外引入 cryptography）
  - 密钥派生：key = SHA256(key_seed + b"|" + SALT)，共 32 字节
  - SALT：dbm-sqlserver-login-secret-v1，**必须与 Go 端 SecretSalt 严格一致**，
    任何一端修改都必须同步，否则解密失败
  - 输出格式：base64( nonce(12B) || ciphertext(N B) || tag(16B) )，ASCII 字符串，
    与 cryptography.AESGCM / Go crypto/cipher GCM 输出二进制布局一致

威胁模型（重要，请勿产生"密码已被强加密"的错觉）：
  - 本模块解决的是「**防止 sa_pwd / drs_pwd 等敏感字段以明文出现在 Job 平台 script_param、
    目标机进程参数 (`ps -ef`)、Job 日志与审计流水中**」这一具体威胁点，属于纵深防御中
    "应用层加密"的一层；与 Job 平台 `is_param_sensitive=1` 传输加密是**正交**关系。
  - **不在本模块防护范围内**（已知安全局限，需依赖上层访问控制 / 主机层加固）：
      1. 拥有 DBM 后端服务器权限（能读源码 + 能读运行时 IP）的内部攻击者：
         由于 SALT 硬编码在开源仓库、key_seed 使用可预测的目标 IP，
         此类攻击者可离线重算 key 解密任意密文。此前提下，攻击者亦可直接读 DBM
         授权中心明文密码 / 直接调 API 授权自己，绕过本层无实际收益，威胁不闭合。
      2. 同时拿到 Go 端 dbactuator 编译产物与 Job 密文的攻击者：由于 SALT 编译期常量，
         同样可离线解密。缓解措施同上（应通过部署侧访问控制解决）。
  - **在本模块防护范围内**（相对旧的"明文直接下发"有实际收益）：
      1. 仅能看到 Job 平台 UI / 目标机进程参数 / 抓包中间态者，密文不可直接使用；
      2. 目标机中间态临时文件、调试日志、误上报到监控/告警的 payload。
  - 后续演进方向（专项立项，不在本 PR 范围）：
      * 引入信封加密：单据级一次性 session key，用 App 公钥加密后随 payload 下发；
      * 或将 SALT 迁移至 KMS / 环境注入，实现"代码/密钥分离"。
      具体见 :data:`_SECRET_SALT` 常量上方的 TODO。

与上下游模块的边界：
  - 上游：SQLServer 单据 / Flow 编排（如 exec_sqlserver_login、linkserver 相关活动节点）
  - 下游：Go 端解密逻辑（linkserver 密码使用方）
  - 本模块只负责加密，不落盘、不打日志明文密码
"""
import base64
import hashlib
import os

from Cryptodome.Cipher import AES  # pycryptodome（项目内加密模块统一使用 Cryptodome 命名空间）

# ---------------------------------------------------------------------------
# 模块级常量
# ---------------------------------------------------------------------------

# 加密盐值：与 Go 端 SecretSalt 保持一致，用于派生 AES 密钥。
# ⚠️ 修改此值将导致 Go 端无法解密历史/新密文，必须两端同步升级并处理灰度。
# TODO(security P2)：当前 SALT 硬编码于开源仓库，key_seed 使用可预测的目标 IP，
#   针对"能读源码+能读运行时 IP"的内部攻击者不构成机密性防护（威胁模型详见模块 docstring）。
#   后续加固方向（择一，需双端联动改造，不在本次改动范围）：
#     1) 信封加密：单据级一次性 session key，用 App 公钥加密后随 payload 下发；
#     2) SALT 迁移到 KMS / env 注入，dbactuator 侧通过启动配置获取，代码/密钥分离。
#   立项时需一并处理：密钥轮换流程、历史密文兼容窗口、灰度回退开关。
_SECRET_SALT: bytes = b"dbm-sqlserver-login-secret-v1"

# AES-GCM 推荐 nonce 长度；单位：字节。RFC 5116 推荐 96bit(12B) 以获得最佳安全/性能平衡。
_AES_GCM_NONCE_BYTES: int = 12


class LoginPasswordEncryptor:
    """SQLServer 账号密码加密器。

    职责：
      - 使用 AES-256-GCM 对明文密码进行加密
      - 密钥由 key_seed 与固定 SALT 派生（SHA-256），确保不同作用域下密文互不通用
      - 产出可直接放入 JSON / 数据库 / 命令行参数的 base64 字符串

    使用方式：
        encryptor = LoginPasswordEncryptor(key_seed="1.2.3.4:48322")
        cipher_b64 = encryptor.encrypt(plain_pwd="my-password")

    线程安全：是（无可变实例状态，AESGCM 每次调用内部构造）

    边界说明：
      - key_seed 为空字符串仍可派生 key，但语义上不允许，调用方应校验后传入
      - plain_pwd 为空字符串会加密得到非空密文（GCM 允许空明文），调用方按业务决定是否放行
      - 未捕获底层 cryptography 异常，属于不可预期故障，交由上层处理
    """

    #: 底层使用的盐值，暴露为类属性以便测试断言 / 双端比对
    SECRET_SALT: bytes = _SECRET_SALT

    #: AES-GCM nonce 字节数
    NONCE_BYTES: int = _AES_GCM_NONCE_BYTES

    def __init__(self, key_seed: str) -> None:
        """初始化加密器。

        :param key_seed: 密钥派生种子，用于隔离密文作用域（如实例地址、集群域名等业务维度标识），
                         必填、非空；与 Go 端保持同一取值语义即可解密
        :return: None
        边界 / 异常：
          - 不在 __init__ 做 IO / RPC，仅做属性赋值与轻量派生
          - key_seed 非 str 时，encode 阶段会抛 AttributeError，由调用方保证类型
        """
        self.key_seed: str = key_seed

        # 派生密钥：SHA256(key_seed_bytes + b"|" + SALT)，长度 32B，用于 AES-256-GCM
        self._key: bytes = hashlib.sha256(key_seed.encode("utf-8") + b"|" + self.SECRET_SALT).digest()

    def encrypt(self, plain_pwd: str) -> str:
        """加密明文密码。

        设计要点 / 怎么做：
          - 每次调用生成 12B 随机 nonce，保证同一 key + 同一明文的多次加密结果不同
          - 使用 pycryptodome AES.MODE_GCM；encrypt_and_digest 返回 (ciphertext, 16B tag)
          - 输出结构：base64( nonce(12B) || ciphertext(N B) || tag(16B) )，
            与 Go 端 crypto/cipher GCM.Seal 的默认 dst=nonce+ct+tag 布局一致
          - 与 Go 端约定：解密时先 base64 decode，
            切分为 nonce(前 12B) / tag(后 16B) / ciphertext(中间部分)

        :param plain_pwd: 明文密码，UTF-8 语义；不允许 None，允许长字符串
        :return: base64 编码的 ASCII 字符串，可直接用于 JSON / 存储 / 传参
        边界 / 异常：
          - plain_pwd 为空字符串：正常加密，返回非空密文（仅 nonce + 16B tag）
          - plain_pwd 为 None：抛 AttributeError（由调用方避免）
          - 底层加密异常：不吞异常，向上抛出，属于不可预期故障
        """
        nonce: bytes = os.urandom(self.NONCE_BYTES)
        # AES-256-GCM：key 32B，nonce 12B；encrypt_and_digest 一次性返回密文与认证 tag
        cipher = AES.new(self._key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plain_pwd.encode("utf-8"))
        return base64.b64encode(nonce + ciphertext + tag).decode("ascii")


def encrypt_login_password(key_seed: str, plain_pwd: str) -> str:
    """加密 SQLServer login 账号密码（模块级便捷函数）。

    功能说明：
      - 对 :class:`LoginPasswordEncryptor` 的薄封装，供仅需一次性调用的场景使用
      - 内部创建临时加密器实例，等价于 LoginPasswordEncryptor(key_seed).encrypt(plain_pwd)

    :param key_seed: 密钥派生种子，非空
    :param plain_pwd: 明文密码，UTF-8 语义
    :return: base64 编码的密文字符串，结构：b64(nonce(12B) || ct_with_tag)
    边界 / 异常：
      - 参数约束与异常语义与 :meth:`LoginPasswordEncryptor.encrypt` 完全一致
      - 高频调用场景建议复用 :class:`LoginPasswordEncryptor` 实例以避免重复派生 key
    """
    return LoginPasswordEncryptor(key_seed=key_seed).encrypt(plain_pwd=plain_pwd)
