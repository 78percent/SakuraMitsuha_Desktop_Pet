"""Per-user/project single-instance ownership and bounded activation IPC.

A QLockFile owns the lifetime; a local pipe alone is not exclusive on Windows.
Only the fixed activation command is accepted. No keys/chat data cross IPC.
"""
import hashlib,getpass,json,os,time
from pathlib import Path
from PySide6.QtCore import QObject,Signal,QLockFile,QTimer
from PySide6.QtNetwork import QLocalServer,QLocalSocket

class InstanceError(RuntimeError):pass

def instance_key(root,role='sakura'):
    identity=os.path.normcase(str(Path(root).resolve()))+'|'+getpass.getuser()+'|'+role
    return 'sakura-'+hashlib.sha256(identity.encode('utf-8')).hexdigest()[:28]

class SingleInstance(QObject):
    activated=Signal(bool)
    def __init__(self,root,parent=None,role='sakura',runtime_dir=None):
        super().__init__(parent)
        self.key=instance_key(root,role)
        folder=Path(runtime_dir) if runtime_dir else Path(root)/'.bootstrap/runtime'
        folder.mkdir(parents=True,exist_ok=True)
        self.lock=QLockFile(str(folder/(self.key+'.lock')))
        self.lock.setStaleLockTime(0)
        self.server=QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self._accept)
        self.owner=False;self.pending=False;self.pending_full=False;self.handler=None
        self.clients=set()
    def acquire_or_activate(self,full=True,timeout_ms=5000):
        if self.lock.tryLock(0):
            self.owner=True
            if not self.server.listen(self.key):
                self.close()
                raise InstanceError('三叶启动协调失败：'+self.server.errorString())
            return True
        deadline=time.monotonic()+timeout_ms/1000
        while time.monotonic()<deadline:
            socket=QLocalSocket()
            socket.connectToServer(self.key)
            if socket.waitForConnected(min(150,max(1,int((deadline-time.monotonic())*1000)))):
                socket.write((json.dumps({'command':'activate','full':bool(full)})+'\n').encode())
                socket.flush();socket.waitForBytesWritten(300)
                data=bytearray()
                while time.monotonic()<deadline:
                    if socket.bytesAvailable() or socket.waitForReadyRead(150):
                        data.extend(bytes(socket.readAll()))
                        if b'\n' in data:
                            if json.loads(bytes(data).split(b'\n')[0]).get('accepted') is True:
                                socket.disconnectFromServer();return False
                            break
                socket.abort()
            # A new process may own the lock but still be preparing its local server.
            time.sleep(.04)
        raise InstanceError('三叶已在启动或响应较慢。请稍后再试；未创建重复角色。')
    def set_handler(self,handler):
        self.handler=handler
        if self.pending:
            full=self.pending_full;self.pending=self.pending_full=False
            QTimer.singleShot(0,lambda:self._dispatch(full))
    def _dispatch(self,full):
        self.activated.emit(full)
        if self.handler:self.handler(full)
        else:
            self.pending=True;self.pending_full=self.pending_full or full
            # Focus an already open startup/setup dialog without another modal.
            from PySide6.QtWidgets import QApplication
            dialog=QApplication.activeModalWidget() if isinstance(QApplication.instance(),QApplication) else None
            if dialog is not None:
                dialog.show();dialog.raise_();dialog.activateWindow()
    def _accept(self):
        while self.server.hasPendingConnections():
            socket=self.server.nextPendingConnection();self.clients.add(socket)
            socket.setProperty('buffer',b'')
            socket.readyRead.connect(lambda s=socket:self._read(s))
            socket.disconnected.connect(lambda s=socket:self._dispose(s))
            QTimer.singleShot(1500,lambda s=socket:self._expire(s))
            self._read(socket)
    def _read(self,socket):
        data=bytes(socket.property('buffer') or b'')+bytes(socket.readAll())
        if len(data)>1024:socket.abort();return
        socket.setProperty('buffer',data)
        if b'\n' not in data:return
        try:
            request=json.loads(data.split(b'\n')[0])
            if request.get('command')!='activate':raise ValueError('command')
            full=request.get('full') is True
        except (ValueError,AttributeError):socket.abort();return
        socket.write(b'{"accepted":true}\n');socket.flush()
        # Acknowledge before scheduling any UI/modality changes.
        QTimer.singleShot(0,lambda:self._dispatch(full))
        socket.disconnectFromServer()
    def _expire(self,socket):
        if socket in self.clients:socket.abort()
    def _dispose(self,socket):
        self.clients.discard(socket);socket.deleteLater()
    def close(self):
        for socket in list(self.clients):socket.abort()
        self.server.close()
        if self.owner:
            self.lock.unlock();self.owner=False
