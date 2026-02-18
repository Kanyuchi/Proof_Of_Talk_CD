# Gunicorn production config
# Usage: gunicorn -c gunicorn.conf.py app.main:app

import multiprocessing

# Bind
bind = "127.0.0.1:8000"

# Workers: (2 × CPU cores) + 1
workers = (multiprocessing.cpu_count() * 2) + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = 120
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "/var/log/pot-matchmaker/access.log"
errorlog  = "/var/log/pot-matchmaker/error.log"
loglevel  = "warning"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# Security
limit_request_line    = 4094
limit_request_fields  = 100
limit_request_field_size = 8190
