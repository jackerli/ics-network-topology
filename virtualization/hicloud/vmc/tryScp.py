import commands
cmd = 'echo 123456 | sudo -S scp trys.py hicloud@172.20.0.234:/tmp'
ret = commands.getstatusoutput(cmd)
print ret[0]
print ret[1]
