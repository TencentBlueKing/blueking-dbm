import logging

from backend import env

logger = logging.getLogger("root")
# if REPO_VERSION_FOR_DEV is set, it means the env is in dev environment
dev_env = str(env.REPO_VERSION_FOR_DEV)

UNIFY_QUERY_PARAMS = {
    "bk_biz_id": 0,  # 替换为实际的biz_id
    "query_configs": [
        {
            "data_source_label": "prometheus",
            "data_type_label": "time_series",
            "promql": "",
            "interval": 60,
            "alias": "a",
        }
    ],
    "expression": "a",
    "alias": "a",
    # 单位：s
    "start_time": 1697100405,
    "end_time": 1697101305,
    "slimit": 500,
    "down_sample_range": "1s",
    # 取最新的几个周期，可以加速查询（如果指标数据不连续，则查不出数据）
    "type": "instant",
}


def logger_debug(msg: str):
    """
    A simple logging function to log debug messages.
    """
    if is_dev():
        logger.debug("env:{} msg:{}".format(dev_env, msg))


def is_dev() -> bool:
    """
    check if the env is in dev environment
    """
    return True if dev_env != "" else False
