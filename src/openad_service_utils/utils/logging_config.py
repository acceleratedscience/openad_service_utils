# logging_config.py
import logging
import logging.config
import colorlog


LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'colored': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'log_colors': {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
        },
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
            'level': 'DEBUG',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'app.log',
            'formatter': 'standard',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True
        },
        'openad_service_utils': {  # your application logger
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False
        },
    },
}

def setup_logging():
    # make sure logger is initialized once. TODO: may need to make singleton to make sure.
    if not logging.getLogger().hasHandlers():
        # print("Setting up logging config")  # Debug statement
        logging.config.dictConfig(LOGGING_CONFIG)
