# TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
# Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://opensource.org/licenses/MIT
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
 

#POWERSHELL D:\sql_install\dba_tools\install\common.ps1 0.0.0.0 SQL2008x64_SorceMedia S48322,S48332 0 0 >D:\sql_install\dba_tools\install\install.log 2>&1
#POWERSHELL D:\sql_install\dba_tools\install\common.ps1 0.0.0.0 SQL2019x64_SorceMedia S48322,S48332 1 1 >D:\sql_install\dba_tools\install\install.log 2>&1
#"C:\Program Files\7-Zip\7z" x -oD: D:\SQL2008R2x64_SorceMedia.tar
PARAM
(
[STRING]$LOCAL_IP = $(THROW "Parameter LOCAL_IP missing."),
[STRING]$MEDIA_PATH_VERSION = $(THROW "Parameter sqlserver version missing.such as SQL2008R2x64,SQL2012x64,SQL2014x64,SQL2016x64,SQL2017x64,SQL2019x64,SQL2022x64 etc."),
[STRING]$INSNAME_LIST = $(THROW "Parameter INSNAME_LIST list missing."),
[STRING]$HADR_Enabled = $(THROW "Parameter HADR_Enabled missing."),
[STRING]$SSMS_Enabled = $(THROW "Parameter SSMS_Enabled missing.")
)

#----------------------------------- version controler -----------------------
$TARGET_INSTANCES = $INSNAME_LIST.TOUPPER().SPLIT(" ")
$MANAGER_PATH			= "D:\" 
$MEDIA_PATH 			= "D:\"+$MEDIA_PATH_VERSION+"\" 

# $CONFIGURATION_FILE_HEAD_VERSION = "[OPTIONS]"
# IF ($MEDIA_PATH_VERSION -like "*2008*")
# {
#     $CONFIGURATION_FILE_HEAD_VERSION = "[SQLSERVER2008]"
# }

#--------------------------------------- mkdir path -----------------------------------
# $DISKLIST =  GET-WMIOBJECT -CLASS WIN32_LOGICALDISK |WHERE-OBJECT {$_.DRIVETYPE -EQ 3}|SELECT-OBJECT -PROPERTY DEVICEID

# FOREACH($T IN $TARGET_INSTANCES)
# {	
#     $PORT = $T.REPLACE("S","")
# 	FOREACH($DISK IN $DISKLIST)
# 	{
# 		IF($DISK.DEVICEID -NE "C:")
# 		{
# 			$CMD = "IF NOT EXIST "+$DISK.DEVICEID+"\gamedb\"+$PORT+" md "+$DISK.DEVICEID+"\gamedb\"+$PORT+""
#             CMD /C $CMD
# 		}
# 	} 
# }

#--------------------------------------- special work -----------------------------------
# #configuration windows service
# SET-SERVICE AppMgmt      -STARTUPTYPE DISABLED
# SET-SERVICE Spooler      -STARTUPTYPE DISABLED
# SET-SERVICE RasMan       -STARTUPTYPE DISABLED
# SET-SERVICE RpcLocator   -STARTUPTYPE DISABLED
# SET-SERVICE RemoteAccess -STARTUPTYPE DISABLED
# SET-SERVICE SCardSvr     -STARTUPTYPE DISABLED
# SET-SERVICE AudioSrv     -STARTUPTYPE DISABLED
# SET-SERVICE SharedAccess -STARTUPTYPE DISABLED
# SET-SERVICE WinRM		 -STARTUPTYPE DISABLED

# #Ignore restart
# $CMD = "reg delete ""HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired"" /f"
# CMD /C $CMD
# $CMD = "reg delete ""HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager"" /v PendingFileRenameOperations /f"
# CMD /C $CMD


#--------------------------------------- install action -------------------------------------------
# IMPORT-MODULE SERVERMANAGER	 #GET-WINDOWSFEATURE
# ADD-WINDOWSFEATURE TELNET-CLIENT

# SET-LOCATION "C:\Windows\Temp"

# key of configuration file
# FOREACH($T IN $TARGET_INSTANCES)
# {	
#     $PORT = $T.REPLACE("S","")
# 	$TARGET_CONFIGURATION_FILE = $MANAGER_PATH+$MODULE_CONFIGURATION_FILE+"_"+$T
# 	IF(TEST-PATH $TARGET_CONFIGURATION_FILE){REMOVE-ITEM $TARGET_CONFIGURATION_FILE}
# 	$CONTENT = GET-CONTENT $SOURCE_CONFIGURATION_FILE
#     $CONTENT = $CONTENT.REPLACE('{data_dir_port}',$PORT)
# 	"$CONFIGURATION_FILE_HEAD_VERSION" 	| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $TARGET_CONFIGURATION_FILE
# 	$CONTENT							| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $TARGET_CONFIGURATION_FILE
# 	"INSTANCEID=""$T"""					| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $TARGET_CONFIGURATION_FILE
# 	"INSTANCENAME=""$T""" 				| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $TARGET_CONFIGURATION_FILE
# 	#install aciton
# 	$CMD = $MEDIA_PATH+"setup.exe /ConfigurationFile=$TARGET_CONFIGURATION_FILE"
# 	CMD /C $CMD
# 	REMOVE-ITEM $TARGET_CONFIGURATION_FILE
# }

# REMOVE-ITEM $SOURCE_CONFIGURATION_FILE

#--------------------------------------- bind port -----------------------------------
#define sever instance array
$LOCAL_INSTANCES = @()
$MASTER_KEY_SHORT = "HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\"
$MASTER_KEY = "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Microsoft SQL Server\"
$DETAIL_KEY = "\MSSQLServer\SuperSocketNetLib\Tcp"
$DETAIL_HADR_KEY = "\MSSQLServer"

#get all instance name,version,ipnum on server
FOREACH($KEY IN GET-CHILDITEM  $MASTER_KEY_SHORT | WHERE-OBJECT {$_.NAME -LIKE "*MSSQL*"} | WHERE-OBJECT {$_.NAME -NOTLIKE "*Microsoft SQL Server\MSSQLSERVER"})
{
	$STR = $KEY.NAME.REPLACE($MASTER_KEY,"")
	IF($STR.LENGTH -GT 0)
	{
		FOREACH($T IN $TARGET_INSTANCES)
		{
			IF ($STR -like "*."+$T)
			{
				$PORT = $T.REPLACE("S","")
				$KEY_COUNT = (GET-CHILDITEM ($KEY.NAME+$DETAIL_KEY).REPLACE("HKEY_LOCAL_MACHINE","HKLM:")).LENGTH - 1
				$LOCAL_INSTANCES += ,($KEY.NAME,$T,$KEY_COUNT,$PORT)
			}
		}
	}
}

$BIND_PORT_FILE = $MANAGER_PATH+"bind_port.bat"
IF(TEST-PATH $BIND_PORT_FILE)
{
	REMOVE-ITEM $BIND_PORT_FILE
}
"@ECHO OFF" | OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE

FOR($I = 0;$I -LT $LOCAL_INSTANCES.LENGTH;$I ++)
{
	$KEY_HADR = $LOCAL_INSTANCES[$I][0] + $DETAIL_HADR_KEY
	$KEY_PART = $LOCAL_INSTANCES[$I][0] + $DETAIL_KEY
	$SQLSVC_NAME = "MSSQL$"+$LOCAL_INSTANCES[$I][1]
	$AGTSVC_NAME = "SQLAGENT$"+$LOCAL_INSTANCES[$I][1]
    $IPKEY_CNT = $LOCAL_INSTANCES[$I][2]
    $PORT = $LOCAL_INSTANCES[$I][3]
	
	"REG ADD """+$KEY_PART+"\IP1"" /v Active /t REG_DWORD /d 1 /f" 						| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+"\IP1"" /v Enabled /t REG_DWORD /d 1 /f" 					| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+"\IP1"" /v IpAddress /t REG_SZ /d "+$LOCAL_IP+" /f" 		| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+"\IP1"" /v TcpDynamicPorts /t REG_SZ /d """" /f" 			| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+"\IP1"" /v TcpPort /t REG_SZ /d "+$PORT+" /f" 	| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	
	"REG ADD """+$KEY_PART+"\IP2"" /v Active /t REG_DWORD /d 1 /f" 						| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+"\IP2"" /v Enabled /t REG_DWORD /d 1 /f" 					| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+"\IP2"" /v IpAddress /t REG_SZ /d 127.0.0.1 /f" 				| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+"\IP2"" /v TcpDynamicPorts /t REG_SZ /d """" /f" 			| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+"\IP2"" /v TcpPort /t REG_SZ /d "+$PORT+" /f" 	| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	
	FOR($K = 3;$K -LE $IPKEY_CNT;$K ++)
	{
		"REG ADD """+$KEY_PART+"\IP"+$K+""" /v Active /t REG_DWORD /d 0 /f" 			| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
		"REG ADD """+$KEY_PART+"\IP"+$K+""" /v Enabled /t REG_DWORD /d 0 /f" 			| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
		"REG ADD """+$KEY_PART+"\IP"+$K+""" /v IpAddress /t REG_SZ /d ::"+$K+" /f" 		| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
		"REG ADD """+$KEY_PART+"\IP"+$K+""" /v TcpDynamicPorts /t REG_SZ /d """" /f" 	| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
		"REG ADD """+$KEY_PART+"\IP"+$K+""" /v TcpPort /t REG_SZ /d """" /f" 			| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	}
	"REG ADD """+$KEY_PART+""" /v AuditLevel /t REG_DWORD /d 2 /f" 						| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+""" /v ListenOnAllIPs /t REG_DWORD /d 0 /f" 					| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+"\IPALL"" /v TcpPort /t REG_SZ /d """" /f" 					| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"REG ADD """+$KEY_PART+"\IPALL"" /v TcpDynamicPorts /t REG_SZ /d """" /f" 			| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	
	#SQL2017+
	IF($HADR_Enabled -EQ "1"){
		"REG ADD """+$KEY_HADR+"\HADR"" /v HADR_Enabled /t REG_DWORD /d 1 /f" 			| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	}
	
	#"NET STOP "+$AGTSVC_NAME 		| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"NET STOP "+$SQLSVC_NAME+" /Y" 	| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"NET START "+$SQLSVC_NAME 		| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
	"NET START "+$AGTSVC_NAME 		| OUT-FILE -ENCODING "Default" -APPEND -FILEPATH $BIND_PORT_FILE
}
#run security file
CMD /C $BIND_PORT_FILE

REMOVE-ITEM $BIND_PORT_FILE

#SQL2016+
IF($SSMS_Enabled -EQ "1")
{
	$CMD = $MEDIA_PATH+"SSMS-Setup-ENU.exe /install /passive /norestart"
	CMD /C $CMD
}

#SQL2019
IF ($MEDIA_PATH_VERSION -like "*2019*")
{
    Copy-Item -Path 'C:\Program Files (x86)\Microsoft SQL Server Management Studio 18\Common7\IDE\PrivateAssemblies\Interop\Microsoft.VisualStudio.Shell.Interop.8.0.dll' -Destination 'C:\Program Files (x86)\Microsoft SQL Server Management Studio 18\Common7\IDE\PublicAssemblies\' -Force
}
