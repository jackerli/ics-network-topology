import commands
class tryServerclass:
    def func1(self):
        cm = "mkdir apd"
        ret = commands.getstatusoutput(cm)
        print ret[0]
        return 1
    def func2(self):
        cm = "echo '2'"
        ret = commands.getoutputstatus(cm)
        print ret[0]
        return 2

    
