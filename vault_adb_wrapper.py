import adbutils
import json
import os
import time


class VaultPhone:
    def __init__(self, uuid, config, host_ip="127.0.0.1", host_port=5037):
        self.client = adbutils.AdbClient(host=host_ip, port=host_port)
        self.device = False
        if type(uuid) == list:
            # print("hello")
            try:
                uuid = "{}:{}".format(uuid[0], uuid[1])
                self.client.connect(uuid, timeout=1.0)
            except Exception as e:
                # print("error: {}".format(e))
                raise NameError("ip port problem - no connection")
        self.__uuid = uuid
        devices_db = self.client.devices()
        # print(devices_db)
        for db_item in devices_db:
            if db_item.serial == uuid:
                self.device = db_item
        self.data = self.read_config(config).get(uuid, {})
        # print(self.data)
        if not self.device:
            raise NameError("device not known")
        if self.data == {}:
            raise RuntimeWarning("no config for device")

    def read_config(self, filename):
        # print("open "+str(filename))
        try:
            f = open(filename, "r")
            fdata = f.read()
            f.close()
            data = json.loads(fdata)
        except IOError as err:
            # print(os.getcwd())
            # print("Oops, error: {}".format(err))
            data = {}
        return data

    def status(self):
        if self.device:
            return True
        else:
            return False

    def action(self, action="None", *args):
        todo_list = self.data.get(action, [])
        if not todo_list:
            return False
        return_value = True
        for element in todo_list:
            if element[0] == "shell":
                expr = element[1]
                for arg in args:
                    arg_str = "$ARG{}".format(args.index(arg))
                    expr = expr.replace(arg_str, str(arg))
                # print(expr)
                return_value = self.device.shell(expr)
            if element[0] == "tap":
                expr = "input tap {}".format(element[1])
                # print(expr)
                return_value = self.device.shell(expr)
            if element[0] == "action":
                return_value = self.action(element[1])
            if element[0] == "sleep":
                time.sleep(int(element[1]))
                return_value = True
            if element[0] == "push":
                if len(args) < 2:
                    return False
                return_value = self.device.push(args[0], args[1])
            if element[0] == "pull":
                if len(args) < 2:
                    return False
                return_value = self.device.pull(args[0], args[1])
            if element[0] == "forward":
                if len(args) < 2:
                    return False
                # print(args)
                return_value = self.device.forward("tcp:{}".format(args[0]), "tcp:{}".format(args[1]))
                # print(return_value)
        return return_value


if __name__ == '__main__':
    # android device uuid to use
    # device_uuid = "TA986027DH"
    # config = "phone.json"
    # ip = "127.0.0.1"
    # port = 5037
    #
    # try:
    #     phone = VaultPhone(uuid=device_uuid, config=config, host_ip=ip, host_port=port)
    # except NameError:
    #     print("Phone not known")
    # except TypeError:
    #     print("No config for device found - no action possible")
    #
    # if phone.status():
    #     print("Phone connected")
    #     number = "+49"
    #     time.sleep(1)
    #     phone.action("call_start", number)
    #     phone.action("call_end", number)
    #     phone.action("bt_pairing")
    #     phone.action("sms_send", number, "Test SMS Message")
    pass
