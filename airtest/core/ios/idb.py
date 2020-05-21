from ntpath import basename
from os import path
from pathlib import Path
from subprocess import Popen, STDOUT, PIPE

class IDB(object):
    
    def __init__(self, udid=None):
        self.udid = udid
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
        self._cmd('list-targets', targetUdid=False)
        return self._cmd('connect', self.udid, targetUdid=False)

    def disconnect(self):
        """
        Perform `idb disconnect` command

        Returns:
            process

        """
        return self._cmd('disconnect', self.udid, targetUdid=False)

    def kill(self):
        """
        Perform `idb kill` command

        Returns:
            process

        """
        return self._cmd('kill')

    def install_app(self, filePath):
        """
        Perform `idb install` command

        Args:
            filepath: full path to file to be installed on the device

        Returns:
            process

        """
        return self._cmd('install', filePath)

    def uninstall_app(self, package):
        """
        Perform `idb uninstall` command
        Args:
            package: package name to be uninstalled from the device

        Returns:
            process

        """
        return self._cmd('uninstall', package)

    def start_app(self, package):
        """
        Perform `idb launch` command to start the application

        Returns:
            process

        """
        return self._cmd('launch', package, '-f/--foreground-if-running')

    def stop_app(self, package):
        """
        Perform `idb terminate` command to force stop the application

        Args:
            package: package name

        Returns:
            process

        """
        return self._cmd('terminate', package)

    def push(self, source, targetName, destination, package):
        """
        Perform `idb push` command

        Args:
            source: source file to be copied to the device
            targetName: desired name of the file on the device
            destination: destination on the device where the file will be copied
            package: package the file will be under

        Returns:
            process

        """
        self._cmd('file', 'mkdir', 'files', '--bundle-id', package)
        return self._cmd('file', 'push', source, targetName, destination, '--bundle-id', package)

    def start_debug_session(self, package):
        """
        Perform `debugserver start` command

        Args:
            package: name of the running package to debug

        Returns:
            process

        """
        return self._cmd('debugserver', 'start', package, separateProcess=True)

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
        return self._cmd('record', 'video', filePath, separateProcess=True)

    def _cmd(self, *cmds, **kwargs):
        command = ['idb']
        command.extend(cmds)
        if 'targetUdid' not in kwargs or kwargs['targetUdid'] == True:
            command.extend(['--udid', self.udid])
        command = ' '.join(command)
        print(command)
        activateProcess = ''

        if 'separateProcess' in kwargs and kwargs['separateProcess'] == True:
            idx = 0
            writtenProcess = False

            while not writtenProcess:
                idx += 1
                try:
                    with open(f'{self.filePath}/tempProcess{idx}.py', 'w') as f:
                        f.write('from subprocess import Popen, STDOUT, PIPE \n')
                        f.write(f'Popen(\"{command}\", stdout=PIPE, stderr=STDOUT, shell=True)')
                    writtenProcess = True
                except:
                    pass

            process = Popen('python {0}/tempProcess{1}.py'.format(self.filePath, idx), shell=True)
        else:
            process = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True)
            process.wait()
        
        return process