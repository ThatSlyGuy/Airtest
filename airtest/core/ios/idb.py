from ntpath import basename
from os import path
from pathlib import Path
from subprocess import Popen, STDOUT, PIPE

class IDB(object):
    
    def __init__(self, udid=None):
        self.deviceId = udid
        self.disconnect()
        self.connect()
        self.filePath = Path(__file__).parent.absolute()
        self.recordingPath = None
    
    def connect(self):
        """
        Perform `idb connect` command

        Returns:
            process

        """
        self._cmd('list-targets', targetDevice=False)
        return self._cmd('idb', 'connect', self.deviceId, targetDevice=False)

    def disconnect(self):
        """
        Perform `idb disconnect` command

        Returns:
            process

        """
        return self._cmd('idb', 'disconnect', self.deviceId, targetDevice=False)

    def list_apps(self):
        """
        Perform `idb list-apps` command

        Returns:
            process

        """
        return self._cmd('idb', 'list-apps', targetDevice=False)

    def ios_deploy(self, app, *args):
        """
        Perform `ios-deploy` app command

        Args:
            app: the path to the app to deploy
            args: optional additional arguments

        Returns:
            process

        """
        return self._cmd('ios-deploy', *args, '--bundle', app, '--no-wifi', idSyntax='id', waitForProcess=False)

    def kill(self):
        """
        Perform `idb kill` command

        Returns:
            process

        """
        return self._cmd('idb', 'kill')
    
    def install_app(self, filePath):
        """
        Perform `idb install` command

        Args:
            filepath: full path to file to be installed on the device

        Returns:
            process

        """
        return self._cmd('idb', 'install', filePath)

    def uninstall_app(self, package):
        """
        Perform `idb uninstall` command
        Args:
            package: package name to be uninstalled from the device

        Returns:
            process

        """
        return self._cmd('idb', 'uninstall', package)

    def start_app(self, package):
        """
        Perform `idb launch` command to start the application

        Returns:
            process

        """
        return self._cmd('idb', 'launch', package, '-f/--foreground-if-running')

    def stop_app(self, package):
        """
        Perform `idb terminate` command to force stop the application

        Args:
            package: package name

        Returns:
            process

        """
        return self._cmd('idb', 'terminate', package)

    def push(self, package, targetFile, destination):
        """
        Perform `ios-deploy upload` command

        Args:
            package: package the file will be under
            targetFile: desired name of the file on the device
            destination: destination on the device where the file will be copied

        Returns:
            process

        """
        return self._cmd('ios-deploy', '--bundle_id', package, '--upload', targetFile, '--to', destination, '--no-wifi', idSyntax='id')

    def start_debug_session(self, package):
        """
        Perform `idb debugserver start` command

        Args:
            package: name of the running package to debug

        Returns:
            process

        """
        return self._cmd('idb', 'debugserver', 'start', package, waitForProcess=False)

    def start_recording(self, filePath):
        """
        Perform `idb record video` command

        Args:
            filePath: destination of the recorded video

        Returns:
            process

        """
        directory = filePath[0:max(filePath.rfind('/') + 1, filePath.rfind('\\') + 1)] if '/' in filePath or '\\' in filePath else ''
        fileName = basename(filePath)
        fileExtension = fileName[fileName.rfind('.') + 1:]
        fileName = fileName[0:fileName.rfind('.')]
        
        i = 0
        while path.isfile(f'{directory}{fileName}_{i}.{fileExtension}'):
            i += 1

        self.recordingPath = f'{directory}{fileName}_{i}.{fileExtension}'
        return self._cmd('idb', 'record', 'video', filePath, waitForProcess=False)

    def _cmd(self, *cmds, **kwargs):
        commands = list(cmds)
        if 'targetDevice' not in kwargs or kwargs['targetDevice'] == True:
            commands.append('--udid' if 'idSyntax' not in kwargs else '--{0}'.format(kwargs['idSyntax']))
            commands.append(self.deviceId)
        
        command = ' '.join(commands)
        print(command, flush=True)

        process = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True)

        if 'waitForProcess' not in kwargs or kwargs['waitForProcess'] == True:
            process.wait()
        
        return process