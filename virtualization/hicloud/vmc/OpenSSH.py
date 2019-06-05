# -*- coding: utf-8 -*-

import getpass
import os
import sys
import threading

import pexpect

import Logging

logger = Logging.get_logger(__name__)

KEY = '/root/.ssh/id_rsa'
PUB_KEY = '%s.pub' % KEY
TIMEOUT = 60


class OpenSsh(threading.Thread):
    def __init__(self, ip, username, password, logger):
        threading.Thread.__init__(self)
        self.ip = ip
        self.username = username
        self.password = password
        self.logger = logger

    # 删除密钥文件
    def delete_key(self):
        self.logger.info('***** delete_key() is running *****')
        if os.path.exists(KEY):
            os.remove(KEY)

        if os.path.exists(PUB_KEY):
            os.remove(PUB_KEY)

    # 匹配机器指令
    def expect_cmd(self, conn, info):
        self.logger.info('***** expect_cmd is running *****')
        try:
            if type(info) is str:
                sub_cmd = [info, pexpect.EOF, pexpect.TIMEOUT]
            elif type(info) is list:
                info.extend([pexpect.EOF, pexpect.TIMEOUT])
                sub_cmd = info
            else:
                self.logger.error('expect is error !')
                return None

            result = conn.expect(sub_cmd, timeout=TIMEOUT)
            if result != 0:
                self.logger.info(
                    'info: %s, result: %s \ncmd before: %s, cmd after: %s' % (info, result, conn.before, conn.after))
            else:
                self.logger.info('execute cmd: %s is successful' % repr(info))
            return result
        except Exception as e:
            self.logger.error('expect_cmd is error: %s' % repr(e))
            return None

    # 向远程主机发送本机证书
    def send_key(self):
        self.logger.info('***** send_key() is running *****')
        try:
            # 清除本地证书
            os.system('> /root/.ssh/known_hosts')
            spawn_cmd = 'ssh %s@%s' % (self.username, self.ip)
            self.logger.info(spawn_cmd)
            ssh_conn = pexpect.spawn(spawn_cmd)
            self.expect_cmd(ssh_conn, 'Are you sure you want to continue connecting (yes/no)?')
            ssh_conn.sendline('yes')
            self.expect_cmd(ssh_conn, 'password:')
            ssh_conn.sendline(self.password)
            ssh_conn.sendline('exit')
            ssh_conn.eof()
            ssh_conn.close()
        except Exception as e:
            self.logger.error('send_key is error: %s' % repr(e))

    # 创建本机密钥信息
    def create_key(self):
        self.logger.info('***** create_key() is running *****')
        try:
            # 删除旧的认证文件
            if os.path.exists(KEY):
                os.remove(KEY)

            spawn_cmd = 'ssh-keygen -t rsa -f %s' % KEY
            self.logger.info(spawn_cmd)
            keygen_conn = pexpect.spawn(spawn_cmd)
            # 提示是否覆盖当前key文件，如果文件不存在，将不会返回该交互信息
            self.expect_cmd(keygen_conn,
                            ['Generating public/private rsa key pair.', '/root/.ssh/id_rsa already exists.',
                             'Overwrite (y/n)?'])
            keygen_conn.sendline('y')
            # 确认是否重新生成key文件
            self.expect_cmd(keygen_conn, ['Enter passphrase', '(empty for no passphrase):'])
            keygen_conn.sendline('')
            # 再次进行确认
            self.expect_cmd(keygen_conn, 'Enter same passphrase again:')
            keygen_conn.sendline('')
            keygen_conn.sendline('exit')
            keygen_conn.eof()
            keygen_conn.close()
        except Exception as e:
            self.logger.error('create_key is error: %s' % repr(e))

    # 将公共密钥信息加入远程主机
    def scp_key(self):
        self.logger.info('***** scp_key() is running *****')
        try:
            # 在目标机上创建.ssh目录
            mkdir_cmd = 'mkdir -p /%s/.ssh' % self.username
            self.logger.info('mkdir_cmd: %s' % mkdir_cmd)
            self.execute_cmd(mkdir_cmd)
            spawn_cmd = 'scp -r %s %s:/%s/.ssh/authorized_keys' % (PUB_KEY, self.ip, self.username)
            self.logger.info(spawn_cmd)
            scp_conn = pexpect.spawn(spawn_cmd)
            self.expect_cmd(scp_conn, "%s@%s's password:" % (self.username, self.ip))
            scp_conn.sendline('%s' % self.password)
            scp_conn.sendline('')
            scp_conn.sendline('exit')
            scp_conn.eof()
            scp_conn.close()
        except Exception as e:
            self.logger.error('scp_key is error: %s' % repr(e))

    # 远程执行命令
    def execute_cmd(self, cmd):
        self.logger.info('***** execute_cmd is running *****')
        try:
            conn = pexpect.spawn('ssh %s@%s' % (self.username, self.ip))
            self.expect_cmd(conn, "%s@%s's password:" % (self.username, self.ip))
            conn.sendline('%s' % self.password)
            conn.sendline('')
            conn.sendline(cmd)
            conn.sendline('')
            conn.sendline('exit')
            conn.eof()
            conn.close()
        except Exception as e:
            self.logger.error('execute_cmd is error: %s' % repr(e))

    #        ssh = pxssh.pxssh()
    #        ssh.login(self.ip, self.username, self.password)
    #        ssh.prompt()
    #        ssh.sendline(ssh)
    #        ssh.prompt()
    #        result = ssh.defore
    #        ssh.logout()
    #        return result

    def run(self):
        self.logger.info('run() is running ...')
        try:
            self.delete_key()
            self.send_key()
            self.create_key()
            self.scp_key()
            self.logger.info('---- open ssh is finished ----')
        except Exception as e:
            self.logger.error('---- open ssh is error ----')

    def stop(self):
        pass


# 接受用户输入的主机，用户名，密码信息
def get_ssh_info():
    ip = raw_input('please input host ip: ')
    username = raw_input('please input username: ')
    password = getpass.getpass('please input password: ')

    return (ip.strip(), username.strip(), password.strip())


if __name__ == '__main__':
    args = sys.argv
    if len(args) == 4:
        ip = args[1].strip()
        username = args[2].strip()
        password = args[3].strip()
    else:
        (ip, username, password) = get_ssh_info()
    logger.info('ip: %s, username: %s, password: %s' % (ip, username, password))
    ssh = OpenSsh(ip, username, password)
    ssh.start()
