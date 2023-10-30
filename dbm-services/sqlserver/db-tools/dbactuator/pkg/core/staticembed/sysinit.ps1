#-------------------------------------- special work -----------------------------------
#configuration windows service
SET-SERVICE AppMgmt      -STARTUPTYPE DISABLED
SET-SERVICE Spooler      -STARTUPTYPE DISABLED
SET-SERVICE RasMan       -STARTUPTYPE DISABLED
SET-SERVICE RpcLocator   -STARTUPTYPE DISABLED
SET-SERVICE RemoteAccess -STARTUPTYPE DISABLED
SET-SERVICE SCardSvr     -STARTUPTYPE DISABLED
SET-SERVICE AudioSrv     -STARTUPTYPE DISABLED
SET-SERVICE SharedAccess -STARTUPTYPE DISABLED
SET-SERVICE WinRM        -STARTUPTYPE DISABLED


# if there are some previous operations make OS require a restart, turn it off
Remove-Item -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager" -Name "PendingFileRenameOperations" -Force
Remove-Item -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired" -Force

# wait 3s
Start-Sleep -Seconds 3


# 代码的作用是为除了系统盘（C:）以外的所有逻辑磁盘添加权限，以便 SQL Server 和 MSSQL 账号可以访问这些磁盘
$DISKLIST =  GET-WMIOBJECT -CLASS WIN32_LOGICALDISK |WHERE-OBJECT {$_.DRIVETYPE -EQ 3}|SELECT-OBJECT -PROPERTY DEVICEID
FOREACH($DISK IN $DISKLIST)
{
        #add privileges
        IF($DISK.DEVICEID -NE "C:")
        {
        $CMD = "ICACLS "+$DISK.DEVICEID+"\ /T /C /Q /GRANT mssql:(OI)(CI)F & ICACLS "+$DISK.DEVICEID+"\ /T /C /Q /GRANT sqlserver:(OI)(CI)F"
        CMD /C $CMD
        }
}

#--------------------------------------- install action -------------------------------------------
# 导入 ServerManager 模块
IMPORT-MODULE SERVERMANAGER

