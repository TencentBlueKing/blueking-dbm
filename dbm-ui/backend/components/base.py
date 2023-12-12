# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import hashlib
import json
import logging
import os.path
import time
from typing import Any, Callable, Dict, List
from urllib import parse

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import translation
from django.utils.translation import ugettext as _
from urllib3.exceptions import ConnectTimeoutError

from backend import env
from backend.configuration.models.system import SystemSettings
from backend.exceptions import ApiError, ApiRequestError, ApiResultError, AppBaseException
from backend.utils.local import local

# TODO 整体复杂度较高，待优化降低复杂度和提高可读性
from .constants import CLIENT_CRT_PATH, SSL_KEY, SSLEnum
from .exception import DataAPIException
from .utils.params import add_esb_info_before_request, remove_auth_args

logger = logging.getLogger("root")


class DataResponse(object):
    """response for data api request"""

    def __init__(self, request_response, request_id):
        """
        初始化一个请求结果
        @param request_response: 期待是返回的结果字典
        """
        self.response = request_response
        self.request_id = request_id

    def is_success(self):
        # 防止接口返回没有result，再补上code做判断
        if "result" in self.response:
            return self.response["result"]

        try:
            return int(self.code) == 0
        except Exception as e:
            logger.error("third-open-api-debug[%s]: code: %s, except=%s", self.code, e)
            return False

    @property
    def message(self):
        return self.response.get("message", None)

    @property
    def code(self):
        return self.response.get("code", None)

    @property
    def data(self):
        return self.response.get("data", None)

    @property
    def permission(self):
        return self.response.get("permission", None)

    @property
    def errors(self):
        return self.response.get("errors", None)


class DataAPI(object):
    """Single API for DATA"""

    HTTP_STATUS_OK = 200

    def __init__(
        self,
        method: str,
        base: str,
        url: str,
        module: str,
        ssl: bool = False,
        description: str = "",
        freeze_params: bool = False,
        default_return_value: Any = None,
        before_request: Callable = None,
        after_request: Callable = None,
        max_response_record: int = 5000,
        max_query_params_record: int = 5000,
        method_override: str = None,
        url_keys: List[str] = None,
        cache_time: int = 0,
        default_timeout: int = 30,
        max_retry_times: int = 3,
    ):
        """
        初始化一个请求句柄
        @param {string} method 请求方法, GET or POST，大小写皆可
        @param {string} url 请求地址
        @param {string} module 对应的模块，用于后续查询标记
        @param {bool} ssl 是否采用https链接
        @param {string} description 中文描述
        @param {bool} freeze_params 是否冻结参数(参数不允许修改)
        @param {object} default_return_value 默认返回值，在请求失败情形下将返回该值
        @param {function} before_request 请求前的回调
        @param {function} after_request 请求后的回调
        @param {int} max_response_record 最大记录返回长度，如果为None将记录所有内容
        @param {int} max_query_params_record 最大请求参数记录长度，如果为None将记录所有的内容
        @param {string} method_override 重载请求方法，注入到 header（X-HTTP-METHOD-OVERRIDE）
        @param {array.<string>} url_keys 请求地址中存在未赋值的 KEYS
        @param {int} cache_time 缓存时间
        @param {int} default_timeout 默认超时时间
        @param {int} max_retry_times 最大自动重试次数
        """
        self.base = base
        self.url = f'{base.rstrip("/")}/{url.lstrip("/")}'
        self.module = module
        self.method = method
        self.ssl = ssl
        self.default_return_value = default_return_value
        self.freeze_params = freeze_params

        self.before_request = before_request
        self.after_request = after_request

        self.description = description
        self.max_response_record = max_response_record
        self.max_query_params_record = max_query_params_record

        self.method_override = method_override
        self.url_keys = url_keys

        self.cache_time = cache_time
        self.default_timeout = default_timeout
        self.max_retry_times = max_retry_times

    def __call__(
        self,
        params=None,
        data=None,
        raw=False,
        timeout=None,
        raise_exception=True,
        use_admin=False,
        headers=None,
        current_retry_times=0,
    ):
        """
        调用传参

        @param {Boolean} raw 是否返回原始内容
        """
        if current_retry_times >= self.max_retry_times:
            raise ApiError(_("请求已达到最大重试次数{max_retry_times}").format(max_retry_times=self.max_retry_times))
        if params is None:
            params = {}
        if headers is None:
            headers = {}
        self.timeout = timeout or self.default_timeout
        self.request_id = None
        self.data = data

        try:
            response = self._send_request(params, headers, use_admin=use_admin)
            if raw:
                return response.response

            # 统一处理返回内容，根据平台既定规则，断定成功与否
            if raise_exception and not response.is_success():
                raise ApiResultError(
                    self.get_error_message(response.message, response.request_id),
                    code=response.code,
                    errors=response.errors,
                    data=response.data,
                    permission=response.permission,
                )

            return response.data
        except (requests.exceptions.Timeout, ConnectTimeoutError):
            # 网络超时导致，尝试重试并增加超时时间
            current_retry_times += 1
            return self.__call__(
                params=params,
                data=data,
                raw=raw,
                timeout=self.timeout + 30,
                raise_exception=raise_exception,
                use_admin=use_admin,
                headers=headers,
                current_retry_times=current_retry_times,
            )
        except (ApiResultError, ApiRequestError, Exception) as error:  # pylint: disable=broad-except
            # 捕获ApiResultError, ApiRequestError和其他未知异常
            error_message = getattr(error, "error_message", None) or getattr(
                error, "message", _("{}-接口调用异常: {}").format(self.module, str(error))
            )
            logger.exception(f"{error_message}, url => {self.url}, params => {params}, headers => {headers}")

            if isinstance(error, ApiResultError):
                raise ApiResultError(error)
            elif isinstance(error, (DataAPIException, requests.exceptions.RequestException)):
                raise ApiRequestError(error)
            elif isinstance(error, Exception):
                raise DataAPIException(error_message=error_message)

    def get_error_message(self, error_message, request_id=None):
        url_path = ""
        try:
            url_path = parse.urlparse(parse.unquote(self.url)).path
        except TypeError:
            pass

        message = _("[{module}]API请求异常：({error_message})").format(module=self.module, error_message=error_message)
        if url_path:
            message += f" path => {url_path}"
        if request_id:
            message += f" request_id => {request_id}"
        return message

    def _send_request(self, params, headers, use_admin=False):
        # 请求前的参数清洗处理 如果参数冻结了，则无需修改
        if not self.freeze_params:
            if self.before_request is not None:
                params = self.before_request(params)

            params = add_esb_info_before_request(params)
            # 使用管理员账户请求时，设置用户名为管理员用户名，移除bk_token等认证信息
            if use_admin:
                params["bk_username"] = env.DEFAULT_USERNAME
                params = remove_auth_args(params)

        # 是否有默认返回，调试阶段可用
        if self.default_return_value is not None:
            return DataResponse(self.default_return_value, self.request_id)

        # 缓存
        try:
            cache_key = self._build_cache_key(params)
            if self.cache_time:
                result = self._get_cache(cache_key)
                if result is not None:
                    # 有缓存时返回
                    return DataResponse(result, self.request_id)
        except (TypeError, AttributeError):
            pass

        response = None
        error_message = ""

        # 发送请求
        # 开始时记录请求时间
        start_time = time.time()
        try:
            raw_response = self._send(params, headers, use_admin=use_admin)

            # http层面的处理结果
            if raw_response.status_code != self.HTTP_STATUS_OK:
                request_response = {
                    "result": False,
                    "message": f"[{raw_response.status_code}]" + (raw_response.text or raw_response.reason),
                    "code": raw_response.status_code,
                }
                response = DataResponse(request_response, self.request_id)
                raise DataAPIException(self.get_error_message(request_response["message"]), response=raw_response)

            # 结果层面的处理结果
            try:
                response_result = raw_response.json()
                logger.debug("third-open-api-debug[%s]: response_result = %s", self.url, response_result)
            except AttributeError:
                error_message = "data api response not json format url->[{}] content->[{}]".format(
                    self.url,
                    raw_response.text,
                )
                logger.exception(error_message)

                raise DataAPIException(_("返回数据格式不正确，结果格式非json."), response=raw_response)
            else:
                # 防止第三方接口不规范，补充返回数据
                response_result = self.safe_response(response_result)
                self.request_id = response_result["request_id"]

                # 只有正常返回才会调用 after_request 进行处理
                if response_result["result"]:

                    # 请求完成后的清洗处理
                    if self.after_request is not None:
                        response_result = self.after_request(response_result)

                if self.cache_time and "cache_key" in locals():
                    self._set_cache(locals()["cache_key"], response_result)

                response = DataResponse(response_result, self.request_id)
                return response
        finally:
            # 最后记录时间
            end_time = time.time()
            # 如果param是一个非dict，则手动变成dict来记录流水日志
            if not isinstance(params, dict):
                params = {"params_data": params}
            # 判断是否需要记录,及其最大返回值
            bk_username = params.get("bk_username", "")

            if response is not None:
                response_result = response.is_success()
                response_data = json.dumps(response.data)[: self.max_response_record]

                for _param in settings.SENSITIVE_PARAMS:
                    params.pop(_param, None)

                try:
                    params = json.dumps(params)[: self.max_query_params_record]
                except TypeError:
                    params = ""

                # 防止部分平台不规范接口搞出大新闻
                if response.code is None:
                    response.response["code"] = "00"
                # message不符合规范，不为string的处理
                if type(response.message) not in [str]:
                    response.response["message"] = str(response.message)
                response_code = response.code
            else:
                response_data = ""
                response_code = -1
                response_result = False
            response_message = response.message if response is not None else error_message
            response_errors = response.errors if response is not None else ""

            # 增加流水的记录
            _info = {
                "request_datetime": start_time,
                "url": self.url,
                "module": self.module,
                "method": self.method,
                "method_override": self.method_override,
                "query_params": params,
                "response_result": response_result,
                "response_code": response_code,
                "response_data": response_data,
                "response_message": response_message[:1023],
                "response_errors": response_errors,
                "cost_time": (end_time - start_time),
                "request_id": self.request_id,
                "request_user": bk_username,
            }

            _log = _("[BKAPI] {info}").format(
                info=" && ".join([" {}=>{} ".format(_k, _v) for _k, _v in list(_info.items())])
            )
            if response_result:
                logger.debug(_log)
            else:
                logger.exception(_log)

    def _build_cache_key(self, params):
        """
        缓存key的组装方式，保证URL和参数相同的情况下返回是一致的
        :param params:
        :return:
        """
        # 缓存
        cache_str = "url_{url}__params_{params}".format(url=self.build_actual_url(params), params=json.dumps(params))
        hash_md5 = hashlib.new("md5")
        hash_md5.update(cache_str.encode("utf-8"))
        cache_key = hash_md5.hexdigest()
        return cache_key

    def _set_cache(self, cache_key, data):
        """
        获取缓存
        :param cache_key:
        :return:
        """
        cache.set(cache_key, data, self.cache_time)

    def _send(self, params: Any, headers: Dict, use_admin: bool = False):
        """
        发送和接受返回请求的包装
        @param params: 请求的参数,预期是一个字典
        @return: requests response
        """

        # 增加request id
        session = requests.session()
        session.headers.update(headers)
        session.headers.update(
            {
                "X-Bkapi-Request-Id": self.request_id,
                "blueking-language": translation.get_language(),
            }
        )
        # 增加鉴权信息
        if isinstance(params, dict):
            session.headers.update(
                {
                    "X-Bkapi-Authorization": json.dumps(
                        {
                            "bk_app_code": params.pop("bk_app_code", ""),
                            "bk_app_secret": params.pop("bk_app_secret", ""),
                            "bk_username": params.pop("bk_username", env.DEFAULT_USERNAME),
                        }
                    ),
                }
            )

        # 设置cookies
        try:
            local_request = local.request
        except AppBaseException:
            local_request = None

        if local_request and local_request.COOKIES and not use_admin:
            session.cookies.update(local_request.COOKIES)

        # headers 申明重载请求方法
        if self.method_override is not None:
            session.headers.update({"X-METHOD-OVERRIDE": self.method_override})

        url = self.build_actual_url(params)
        # 发出请求并返回结果
        non_file_data, file_data = self._split_file_data(params)
        request_method = self.method.upper()

        # 如果是https链接，则需要带上client证书
        if self.ssl:
            client_crt, client_key = self._fetch_client_crt()
            session.cert = (client_crt, client_key)

        if request_method == "GET":
            result = session.request(method=self.method, url=url, params=params, verify=False, timeout=self.timeout)
        elif request_method == "DELETE":
            session.headers.update({"Content-Type": "application/json; charset=utf-8"})
            result = session.request(
                method=self.method, url=url, data=json.dumps(non_file_data), verify=False, timeout=self.timeout
            )
        elif request_method in ["PUT", "PATCH", "POST"]:
            if not file_data:
                session.headers.update({"Content-Type": "application/json; charset=utf-8"})
                params = json.dumps(non_file_data)
            else:
                params = non_file_data

            # PUT 方法上传文件时，data需作为
            if request_method == "PUT" and file_data:
                data = list(file_data.values())[0]
                result = session.request(method=self.method, url=url, data=data, verify=False, timeout=self.timeout)
            else:
                result = session.request(
                    method=self.method, url=url, data=params, files=file_data, verify=False, timeout=self.timeout
                )
        else:
            raise ApiRequestError(_("异常请求方式，{method}").format(method=self.method))

        return result

    def _fetch_client_crt(self):
        client_crt, client_key = f"{CLIENT_CRT_PATH}/{SSLEnum.CLIENT_CRT}", f"{CLIENT_CRT_PATH}/{SSLEnum.CLIENT_KEY}"
        # 如何证书已存在，则直接返回即可
        ssl = SystemSettings.get_setting_value(key=SSL_KEY, default={})
        # 这里需要判断是否本地化以及文件夹是否存在，有可能pod重启导致秘钥文件丢失
        if ssl and ssl.get("local") and os.path.exists(CLIENT_CRT_PATH):
            return client_crt, client_key

        # 本地写入crt和key文件，防止每次都需要write IO
        os.makedirs(CLIENT_CRT_PATH)
        with open(client_crt, "w+") as f:
            f.write(ssl[SSLEnum.CLIENT_CRT.value])

        with open(client_key, "w+") as f:
            f.write(ssl[SSLEnum.CLIENT_KEY.value])

        # 记录秘钥已经本地化
        ssl["local"] = True
        SystemSettings.insert_setting_value(key=SSL_KEY, value=ssl, value_type="dict")

        return client_crt, client_key

    def build_actual_url(self, params):
        # url中包含变量的场景，用参数渲染
        if isinstance(params, dict):
            return self.url.format(**params)
        return self.url

    def safe_response(self, response_result):
        if "result" not in response_result:
            response_result["result"] = response_result.get("code") == 0 or False
        if "message" not in response_result:
            response_result["message"] = ""
        if "data" not in response_result:
            response_result["data"] = None
        if "request_id" not in response_result:
            response_result["request_id"] = self.request_id
        return response_result

    @staticmethod
    def _split_file_data(data):
        file_data = {}
        non_file_data = {}

        if not isinstance(data, dict):
            return file_data, non_file_data

        for key, value in list(data.items()):
            if hasattr(value, "read"):
                # 一般认为含有read属性的为文件类型
                file_data[key] = value
            else:
                non_file_data[key] = value
        return non_file_data, file_data

    @staticmethod
    def _get_cache(cache_key):
        """
        获取缓存
        :param cache_key:
        :return:
        """
        if cache.get(cache_key):
            return cache.get(cache_key)
