LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'level': 'INFO',
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s [%(filename)s:%(lineno)s - %(funcName)s()] %(message)10s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        # 'file': {
        #     'level': 'DEBUG',
        #     'class': 'logging.FileHandler',
        #     'formatter': 'verbose',
        #     'filename': "/home/stabiledev/git/logging_test/testlog.txt",
        #     'mode': "w",
        # },
        'null': {
            'level':'DEBUG',
            'class':'logging.StreamHandler',
        },
        'console':{
            # 'level':'WARNING',
            'class':'logging.StreamHandler',
            'formatter': 'verbose'
        }

    },
    'loggers': {
        '': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO'
        }
    }
}
