import json,os,signal,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'CetaPet'))
from single_instance import instance_key
WORKER=ROOT/'tools/ipc_test_worker.py'
class InstanceTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name);self.children=[]
    def tearDown(self):
        for p,info in self.children:
            Path(info['_stop']).touch()
            try:p.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                os.kill(info['pid'],signal.SIGTERM);p.communicate(timeout=5)
        self.temp.cleanup()
    def owner(self,*options,root=None):
        stop=self.folder/f'stop-{len(self.children)}'
        p=subprocess.Popen([sys.executable,str(WORKER),str(root or self.folder/'project'),str(self.folder/'runtime'),'--stop-file',str(stop),*options],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
        info=json.loads(p.stdout.readline());info['_stop']=str(stop);self.children.append((p,info));return p,info
    def secondary(self,*options,root=None):
        return subprocess.run([sys.executable,str(WORKER),str(root or self.folder/'project'),str(self.folder/'runtime'),*options],capture_output=True,text=True,encoding='utf-8',timeout=10)
    def test_secondary_receives_ack_and_only_one_owner(self):
        p,info=self.owner();self.assertEqual(info['state'],'owner')
        second=self.secondary();self.assertEqual(second.returncode,0,second.stderr)
        self.assertEqual(json.loads(second.stdout)['state'],'secondary')
        Path(info['_stop']).touch();output,errors=p.communicate(timeout=8);self.assertIn('"activated": true',output)
    def test_activation_is_queued_until_handler_ready(self):
        bind=self.folder/'bind'
        p,info=self.owner('--bind-file',str(bind))
        second=self.secondary();self.assertEqual(json.loads(second.stdout)['state'],'secondary')
        bind.touch();event=p.stdout.readline();self.assertIn('activated',event)
        Path(info['_stop']).touch();output,_=p.communicate(timeout=8);self.assertIn('"activated": true',event+output)
    def test_lock_without_ready_service_times_out_without_becoming_owner(self):
        p,info=self.owner('--lock-only')
        second=self.secondary('--timeout','250');self.assertEqual(second.returncode,2)
        self.assertEqual(json.loads(second.stdout)['state'],'timeout')
    def test_clean_exit_and_crashed_owner_allow_restart(self):
        p,info=self.owner('--duration','150');p.communicate(timeout=8)
        p2,info2=self.owner('--duration','20000');self.assertEqual(info2['state'],'owner')
        os.kill(info2['pid'],signal.SIGTERM);p2.communicate(timeout=8)
        p3,info3=self.owner('--duration','150');self.assertEqual(info3['state'],'owner');p3.communicate(timeout=8)
    def test_simultaneous_launches_have_exactly_one_owner(self):
        pending=[]
        for i in range(3):
            stop=self.folder/f'concurrent-stop-{i}'
            child=subprocess.Popen([sys.executable,str(WORKER),str(self.folder/'project'),str(self.folder/'runtime'),'--stop-file',str(stop)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
            pending.append((child,stop))
        results=[]
        for child,stop in pending:
            info=json.loads(child.stdout.readline());info['_stop']=str(stop)
            self.children.append((child,info));results.append(info['state'])
        self.assertEqual(results.count('owner'),1)
        self.assertEqual(results.count('secondary'),2)

    def test_project_and_role_scope_are_distinct(self):
        a=self.folder/'one';b=self.folder/'two'
        self.assertNotEqual(instance_key(a),instance_key(b))
        self.assertNotEqual(instance_key(a),instance_key(a,'legacy'))
        p,i=self.owner(root=a);p2,i2=self.owner(root=b)
        self.assertEqual(i['state'],'owner');self.assertEqual(i2['state'],'owner')
class StartupModalTests(unittest.TestCase):
    def test_relaunch_during_real_entry_setup_uses_only_existing_dialog(self):
        import time
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            hook="""import sys
from pathlib import Path
sys.path.insert(0,ROOT_MODULE)
import runtime_config,single_instance
from PySide6.QtWidgets import QApplication,QDialog
from PySide6.QtCore import QTimer
folder=Path(FOLDER)
runtime_config.ENV_PATH=folder/'.env'
original=single_instance.SingleInstance
class Instance(original):
    def __init__(self,root,parent=None,**kw):
        super().__init__(folder,parent,**kw)
        self.activated.connect(lambda full:print('CONFIG_ACTIVATED visible='+str(sum(isinstance(w,QDialog) and w.isVisible() for w in QApplication.topLevelWidgets())),flush=True))
single_instance.SingleInstance=Instance
original_exec=QDialog.exec
def setup(self):
    print('CONFIG_DIALOG_STARTED',flush=True)
    (folder/'ready').touch()
    timer=QTimer(self)
    timer.timeout.connect(lambda:self.reject() if (folder/'stop').exists() else None)
    timer.start(20)
    QTimer.singleShot(20000,self.reject)
    return original_exec(self)
QDialog.exec=setup
""".replace('ROOT_MODULE',repr(str(ROOT/'CetaPet'))).replace('FOLDER',repr(str(folder)))
            (folder/'sitecustomize.py').write_text(hook,encoding='utf-8')
            env=os.environ.copy();env['PYTHONPATH']=str(folder);env['QT_QPA_PLATFORM']='offscreen'
            args=[sys.executable,str(ROOT/'run_pet.py')]
            first=subprocess.Popen(args,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
            try:
                deadline=time.monotonic()+15
                while not (folder/'ready').exists() and time.monotonic()<deadline:time.sleep(.05)
                self.assertTrue((folder/'ready').exists(),'setup did not become ready')
                second=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=12)
                self.assertEqual(second.returncode,0,second.stderr)
                self.assertNotIn('CONFIG_DIALOG_STARTED',second.stdout)
                time.sleep(.2);(folder/'stop').touch()
                output,errors=first.communicate(timeout=8)
                self.assertEqual(first.returncode,0,output+errors)
                self.assertEqual(output.count('CONFIG_DIALOG_STARTED'),1)
                self.assertIn('CONFIG_ACTIVATED visible=1',output)
            finally:
                (folder/'stop').touch()
                if first.poll() is None:first.communicate(timeout=8)

if __name__=='__main__':unittest.main(verbosity=2)
