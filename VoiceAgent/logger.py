import logging
import logging.config
import os
import yaml

_CONFIG_LOADED = False


def setup_logging(config_path=r"configs\logging_config.yaml"):
    """
    设置日志配置
    """
    global _CONFIG_LOADED
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=logging.DEBUG)
    _CONFIG_LOADED = True
    logging.getLogger("setup").info("初始化日志配置完成")


def get_logger(name):
    """
    获取日志记录器
    """
    if not _CONFIG_LOADED:
        setup_logging()
    return logging.getLogger(name)


if __name__ == "__main__":
    setup_logging()
    logger = get_logger("VoiceAgent")
    logger.debug("这是一个调试日志")
    logger.info("这是一个信息日志")
    logger.warning("这是一个警告日志")
    logger.error("这是一个错误日志")
    logger.critical("这是一个严重错误日志")
