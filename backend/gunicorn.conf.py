import os

bind = "0.0.0.0:8000"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = "gthread"
timeout = 30
graceful_timeout = 20
keepalive = 5
max_requests = 2000
max_requests_jitter = 200
# tmpfs privado do container (só heartbeat do gunicorn); funciona com sistema de arquivos read-only.
worker_tmp_dir = "/dev/shm"  # noqa: S108  # nosec B108
accesslog = None  # o app registra o acesso pelo molde da rota (sem tokens no caminho)
errorlog = "-"
forwarded_allow_ips = "*"
control_socket_disable = True  # sem socket de controle (container read-only, sem HOME)
