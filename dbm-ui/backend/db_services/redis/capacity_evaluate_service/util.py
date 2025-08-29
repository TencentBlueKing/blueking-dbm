import logging

from backend import env

logger = logging.getLogger("root")
# if REPO_VERSION_FOR_DEV is set, it means the env is in dev environment
dev_env = str(env.REPO_VERSION_FOR_DEV)


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
