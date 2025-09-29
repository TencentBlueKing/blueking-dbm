#!/usr/bin/env python3
# mongo 命令行工具，用于执行mongo命令
import argparse
import os
import signal
import subprocess
import re
from datetime import datetime
import sys
from typing import List

import yaml

# python 3.6.8
MONGO_CMD_PATH = ""
MONGOSTAT_CMD_PATH = ""
MONOTOP_CMD_PATH = ""

def signal_handler(signal, frame):
    print ("done")
    sys.exit(0)

def __init_script__():
    global MONGO_CMD_PATH
    MONGO_CMD_PATH = "/usr/local/mongodb/bin/mongo"
    if os.path.exists("/home/mysql/dbtools/mongo"):
        MONGO_CMD_PATH = "/home/mysql/dbtools/mongo"

    global MONGOSTAT_CMD_PATH
    MONGOSTAT_CMD_PATH = "/usr/local/mongodb/bin/mongostat"
    if os.path.exists("/home/mysql/dbtools/mongostat"):
        MONGOSTAT_CMD_PATH = "/home/mysql/dbtools/mongostat"

    global MONOTOP_CMD_PATH
    MONOTOP_CMD_PATH = "/usr/local/mongodb/bin/mongotop"
    if os.path.exists("/home/mysql/dbtools/mongotop"):
        MONOTOP_CMD_PATH = "/home/mysql/dbtools/mongotop"

    global MONGOSH_CMD_PATH
    MONGOSH_CMD_PATH = "/usr/local/mongodb/bin/mongosh"
    if os.path.exists("/home/mysql/dbtools/mongosh"):
        MONGOSH_CMD_PATH = "/home/mysql/dbtools/mongosh"

    signal.signal(signal.SIGINT, signal_handler)


def get_local_ip(eth_name = "eth1"):
    """Get local IP address by checking network interfaces"""
    try:
        # Try to get IP from eth interface (old format)
        result = subprocess.run(['ip', 'addr', 'show', eth_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            # Look for eth interface with inet addr format
            lines = result.stdout.decode('utf-8').split('\n')
            # inet 1.2.3.4/23
            for i, line in enumerate(lines):
                if eth_name in line and 'inet' in line:
                    match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', line)
                    if match:
                        return match.group(1)
            
    except Exception as e:
        raise e
    
    return None


def ping_mongo(host, port, password):
    """Ping Redis instance and return response"""
    try:
        cmd = [MONGO_CMD_PATH, '-a', password, '-h', host, '-p', str(port), 'ping']
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        if result.returncode == 0:
            return result.stdout.decode('utf-8').strip()
        else:
            return result.stderr.decode('utf-8').strip()
    except subprocess.TimeoutExpired:
        raise subprocess.TimeoutExpired(cmd, timeout=5)
    except Exception as e:
        raise e


def load_config(config_file):
    if not os.path.exists(config_file):
        print(f"Config file not found: {config_file}")
        return
    
    yaml_content = open(config_file, 'r').read()
    # remove the line contain app_name, app_name 存在中文的情况下，会报错
    yaml_content = re.sub(r'^.*app_name:.*\n', '', yaml_content, flags=re.MULTILINE)
    print(yaml_content)
    yaml_data = yaml.safe_load(yaml_content)
    return yaml_data

def list_instance_from_config(yaml_data: dict):
    port_list = []
    for item in yaml_data['servers']:
        port_list.append(item['port'])
    return port_list


class mongo_instance:
    def __init__(self, port):
        self.port = port
        self.server_config = None
        

    def init_in_dbm_env(self, yaml_data: dict):
        self.local_ip = get_local_ip()
        self.now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ports = []
        servers = yaml_data.get("servers", [])
        for server in servers:
            ports.append(server.get("port"))
            if server.get("port") == self.port:
                self.server_config = server

        if self.server_config is None:
            print(f"Error: server config not found: {self.port}. valid ports: {ports}")
            return False
        return True

    # python 3.6.8 用List[str] 不使用list[str]
    def exec_cmd(self, cmd: List[str]):
        auth_args = self.get_auth_args()
        if len(auth_args) > 0:
            cmdline = [MONGO_CMD_PATH, "--quiet", *auth_args, "--port", str(self.port), "--eval", " ".join(cmd)]
        else:
            cmdline = [MONGO_CMD_PATH, "--quiet", "--port", str(self.port), "--eval", " ".join(cmd)]
        print(" ".join(cmdline))
        time_start = datetime.now()
        result = subprocess.run(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        print ("result: ", result.returncode)

        if result.returncode == 0:
            result_str = result.stdout.decode('utf-8').strip()
            result_str = re.sub(r'^', str(self.port) + " ", result_str, flags=re.MULTILINE)
            print(result_str, end="\n")
        else:
            result_str = result.stdout.decode('utf-8').strip()
            result_str = re.sub(r'^', str(self.port) + " ", result_str, flags=re.MULTILINE)
            print(result_str, end="\n")
    
            result_str = result.stderr.decode('utf-8').strip()
            result_str = re.sub(r'^', str(self.port) + " ", result_str, flags=re.MULTILINE)
            print(result_str, end="\n")

        time_end = datetime.now()
        print(self.port, "time cost: ", (time_end - time_start).total_seconds(), "s")

    def get_auth_args(self):
        username = self.server_config.get("username", "")
        password = self.server_config.get("password", "")   
        if username != "" and password != "":
            return ["--username", username, "--password", password, "--authenticationDatabase", "admin"]
        else:
            return []

    # python 3.6.8 用List[str] 不使用list[str]
    def exec_mongostat(self):
        cmdline = [MONGOSTAT_CMD_PATH, "--port", str(self.port), *self.get_auth_args()]
        print(" ".join(cmdline))
        time_start = datetime.now()
        try:
            subprocess.call(cmdline)
        except Exception as e:
            print ("done")  
        time_end = datetime.now()
        print(self.port, "time cost: ", (time_end - time_start).total_seconds(), "s")


    def exec_mongotop(self):
        cmdline = [MONOTOP_CMD_PATH, "--port", str(self.port), *self.get_auth_args()]
        print(" ".join(cmdline))
        time_start = datetime.now()
        try:
            subprocess.call(cmdline)
        except Exception as e:
            print ("done")  
        time_end = datetime.now()
        print(self.port, "time cost: ", (time_end - time_start).total_seconds(), "s")

    def exec_shell(self, shell: str):
        if shell == "mongo":
            cmdline = [MONGO_CMD_PATH, "--port", str(self.port), *self.get_auth_args()]
        elif shell == "mongosh":
            cmdline = [MONGOSH_CMD_PATH, "--port", str(self.port), *self.get_auth_args()]
        else:
            print("Error: invalid shell: ", shell)
            return
        
        print(" ".join(cmdline))
        time_start = datetime.now()
        try:
            subprocess.call(cmdline)
        except Exception as e:
            print ("done")  
        time_end = datetime.now()
        print(self.port, "time cost: ", (time_end - time_start).total_seconds(), "s")

def main():
    parser = argparse.ArgumentParser(description='mongodb cmd helper' + usage(), 
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--config', default="/home/mysql/bk-dbmon/dbmon-config.yaml", help='Config file')
    parser.add_argument('--skip-bad-port', action='store_true', default=False, help='Skip bad port')
    parser.add_argument('--usage', action='store_true', default=False, help='Show usage')
    args, unknown = parser.parse_known_args()

    if args.usage:
        usage()
        return

    if len(unknown) < 2:
        usage()
        return  
    
    yaml_data = load_config(args.config)
    port_list = list_instance_from_config(yaml_data)

    first_arg = unknown[0]
    cmd_list = unknown[1:]

    # if port is 0, for all port
    if first_arg != "0" and first_arg != "all":
        if first_arg.count(",") > 0:
            port_list = [int(port) for port in first_arg.split(",")]
            # if port_list 有重复的，则删除重复的，报错
            if len(port_list) != len(set(port_list)):
                print("Error: port list has duplicate, please check the first_arg: ", first_arg)
                return
        elif first_arg.count("-") == 1:
            port_list = [int(port) for port in range(int(first_arg.split("-")[0]), int(first_arg.split("-")[1]) + 1)]
        elif first_arg.isdigit():
            port_list = [int(first_arg)]
        else:
            print("Error: port list has duplicate, please check the first_arg: ", first_arg)
            return
    
    if len(port_list) > 100:     
        print("Error: port list is too long, please check the first_arg: ", first_arg, "max port is 100")
        return
    
    instance_list = []
    for port in port_list:
        instance = mongo_instance(port)
        if not instance.init_in_dbm_env(yaml_data):
            if args.skip_bad_port:
                print("Error: init_in_dbm_env failed, please check the port: ", port, "skip it")
                continue
            else:
                return 1
        instance_list.append(instance)

    for instance in instance_list:
        if cmd_list[0] == "mongostat":
            instance.exec_mongostat()
        elif cmd_list[0] == "mongotop":
            instance.exec_mongotop()
        elif cmd_list[0] == "shell":
            instance.exec_shell()
        elif cmd_list[0] == "mongo":
            instance.exec_shell("mongo")
        elif cmd_list[0] == "mongosh":
            instance.exec_shell("mongosh")
        else:
            instance.exec_cmd(cmd_list)


def usage():
    return """
    Usage: mongo-cmd.py  <port> "cmd..."\t# run cmd on port
    Usage: mongo-cmd.py  <port> shell|mongo|mongosh
    Usage: mongo-cmd.py  <port> mongostat
    Usage: mongo-cmd.py  <port> mongotop
    Usage: mongo-cmd.py  0|all "cmd..."\t# run cmd on all port
    """
if __name__ == "__main__":
    __init_script__()
    main()





