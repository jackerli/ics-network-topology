# -*- coding: utf-8 -*-

import os
import time

import commands

import Config

DATE = 'Register_date'
NAME = 'User name'
MAIL = 'Mail'
HWID = 'HardwareID'
USERKEY = 'UserKey'
EXPIREDATE = 'ExpireingDate'
DATEKEY = 'DateKey'
LICENSEPATH = "/etc/hicloud/license"
config = Config.load(str('/tmp/adtp-master/hicloud/general.yaml'))
# 当前值为：/usr/local/hicloud/script
script_dir = config['script_dir']
HWCHECKPATH = "%s/vmc/hw_check.dat" % script_dir
ENCODEPATH = "%s/vmc/encode.dat" % script_dir
ZERODATE = "00000000"


# 执行linux命令，返回执行结果
def execute_cmd(cmd):
    try:
        ret = commands.getstatusoutput(cmd)
        if ret[0] != 0:
            return -1
        return ret[1].strip()
    except Exception as e:
        logger.info('execute_cmd error: %s' % e)
        return -1


class CheckLicense():

    def get_item(self, item, license_path):
        cmd = "grep %s %s | awk '{ print $2}'" % (item, license_path)
        return execute_cmd(cmd)

    # 转换16进制字符转换为10进制
    def hex2dec(self, hwid):
        return int(hwid, 16)

    # 把硬件id转换为10进制表示，返回长度为8的列表
    def hex2dec_all(self, hwid):
        dec = []
        # 顺序每次取出两个字符进行10进制转换
        for i in range(8):
            dec.append(self.hex2dec(hwid[i * 2:i * 2 + 2]))
        return dec

    # 对日期根据HardwareID进行编码
    def encode(self, date, hwid):
        try:
            hwid = self.hex2dec_all(hwid)

            if (len(date) < 8):
                logger.info("Date format is wrong")
                return -1

            base = 48
            key0 = 13
            key1 = 27
            key2 = 11
            key3 = 15

            key_items = []
            # 顺序取出日期的每个字符
            for i in range(8):
                date_item = date[i]
                datekey0 = int(date_item)
                s0 = (((((base + datekey0 + (hwid[0] + hwid[1] + i)) * key0) + (hwid[2] + hwid[3] + i)) * key1 + (
                        hwid[4] + hwid[5] + i)) * key2 + (hwid[6] + hwid[7] + i)) * key3
                key_items.append(str(s0).zfill(8).strip())

            return ''.join(key_items)
        except Exception as e:
            logger.info('encode error: %s' % e.message)
            return None

    # 使用dat文件进行编码
    def encode2(self, date, hwid):
        if not os.path.exists(ENCODEPATH):
            logger.info('encode.dat file is not exists')

        encode_cmd = "%s %s %s | grep 'Encode_date:' | awk '{print $1}' | awk -F ':' '{print $2}'" % (
            ENCODEPATH, hwid, date)
        date_key = execute_cmd(encode_cmd)
        if date_key == -1:
            return None
        else:
            return date_key

    # 获取配置文件中相应的配置信息
    def parse_license(self, file_path):
        try:
            license = {}
            # 获取注册账户的邮件信息
            license[MAIL] = self.get_item(MAIL, file_path)
            # 获取vmc主机cpu信息
            license[HWID] = self.get_item(HWID, file_path)
            # 获取根据mail生成的md5值
            license[USERKEY] = self.get_item(USERKEY, file_path)
            # 获取有效日期
            license[EXPIREDATE] = self.get_item(EXPIREDATE, file_path)
            # 获取有效日期的验证码
            license[DATEKEY] = self.get_item(DATEKEY, file_path)
        except Exception as e:
            logger.info('parse_license error: %s' % e.message)
            return -1

        if -1 in license.values():
            return -1

        return license

    # 验证硬件ID是否一致
    def check_hw(self, hw_id):
        try:
            cmd = "%s | head -n 1 | awk '{ print $3 }'" % HWCHECKPATH
            dst_hw = execute_cmd(cmd)
            ret = cmp(dst_hw, hw_id)
            return ret
        except Exception as e:
            logger.info('check_hw error: %s' % e.message)
            return -1

    # 验证邮件名和编码后的user_key知否一致
    def check_mail(self, mail, user_key):
        try:
            mail = '%sTeamsunhicloud2011' % mail
            cmd = 'echo -n %s | md5sum' % mail
            ret = execute_cmd(cmd)
            ret = ret.split()[0]
            return int(ret != user_key)
        except Exception as e:
            logger.info('check_mail error: %s' % e.message)
            return -1

    # 验证是否过期
    def check_date(self, expire_date, date_key, hwid):
        en_date = self.encode(expire_date, hwid)
        if en_date is None:
            return 13

        # 到期时间编码错误
        if en_date != date_key:
            return 13

        # 试用状态
        if expire_date == ZERODATE:  # for beta version
            return 1

        cur_date = time.strftime('%Y%m%d', time.localtime(time.time()))
        # 过期状态
        if cur_date > expire_date:  # date expire
            return 14

        # 正常启动
        return 0

    def run(self):
        state = -1

        # license配置文件不存在
        if not os.path.exists(LICENSEPATH) or not os.path.exists(HWCHECKPATH):
            state = -1

        license = self.parse_license(LICENSEPATH)
        if license == -1:
            state = -1

        # 验证license邮件信息
        if (self.check_mail(license[MAIL], license[USERKEY]) != 0):
            state = 11

        # 验证vmc所在主机cpu信息
        if (self.check_hw(license[HWID]) != 0):
            # 硬件id不匹配
            state = 12

        # 验证licencse到期时间
        state = self.check_date(license[EXPIREDATE], license[DATEKEY], license[HWID])
        return state


# 验证license状态，将状态值插入数据库
def license_main():
    return


if __name__ == "__main__":
    license_main()
