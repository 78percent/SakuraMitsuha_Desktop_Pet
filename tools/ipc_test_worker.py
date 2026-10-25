"""Isolated IPC integration worker; never imports app config or network clients."""
import argparse,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'CetaPet'))
from PySide6.QtCore import QCoreApplication,QTimer
from single_instance import SingleInstance,InstanceError
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('runtime');p.add_argument('--duration',type=int,default=20000);p.add_argument('--delay',type=int,default=0);p.add_argument('--timeout',type=int,default=5000);p.add_argument('--lock-only',action='store_true');p.add_argument('--stop-file');p.add_argument('--bind-file');a=p.parse_args()
app=QCoreApplication([]);c=SingleInstance(a.root,app,runtime_dir=a.runtime)
if a.lock_only:
    assert c.lock.tryLock(0);c.owner=True
    print(json.dumps({'state':'lock','pid':os.getpid()}),flush=True)
else:
    try:owner=c.acquire_or_activate(timeout_ms=a.timeout)
    except InstanceError:
        print(json.dumps({'state':'timeout','pid':os.getpid()}),flush=True);raise SystemExit(2)
    print(json.dumps({'state':'owner' if owner else 'secondary','pid':os.getpid()}),flush=True)
    if not owner:raise SystemExit(0)
    if not a.bind_file:
        QTimer.singleShot(a.delay,lambda:c.set_handler(lambda full:print(json.dumps({'activated':full}),flush=True)))
poll=QTimer();poll.setInterval(40)
def control():
    if a.bind_file and Path(a.bind_file).exists() and c.handler is None:
        c.set_handler(lambda full:print(json.dumps({'activated':full}),flush=True))
    if a.stop_file and Path(a.stop_file).exists():app.quit()
poll.timeout.connect(control);poll.start()
app.aboutToQuit.connect(c.close);QTimer.singleShot(a.duration,app.quit);app.exec()
